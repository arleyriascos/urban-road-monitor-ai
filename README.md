# Urban Road Monitor — servicio de IA

Servicio en Python con FastAPI del proyecto final Urban Road Monitor (Estructura de Datos). Calcula las rutas sobre la red vial de Pasto y, más adelante, agrupará las detecciones de baches.

El servicio no se conecta a la base de datos: el backend le entrega los datos que necesita. El frontend nunca lo llama directamente; solo habla con el backend.

## Estado

Bloque 3 de la Etapa 2: ya están las estructuras base (grafo dirigido, Min-Heap indexado, Union-Find y Pila) y los algoritmos de ruta (Dijkstra y A*), junto con el ajuste del clic a la intersección más cercana. El servicio todavía no responde rutas por HTTP: eso llega en el bloque 5.

## Requisitos

- Python 3.13.3 (la versión está fijada en `.python-version`).
- Git configurado con `core.autocrlf input`.

## Instalación en Windows (PowerShell)

Desde la carpeta del repositorio:

```powershell
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
copy .env.example .env
```

Ejecuta `copy .env.example .env` una sola vez: si se repite, sobrescribe el `.env`. El archivo `.env` no se sube a GitHub.

## Ejecutar el servicio

```powershell
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

- Salud: http://localhost:8000/health
- Documentación de la API: http://localhost:8000/docs

## Comprobaciones antes de cada commit

```powershell
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m ruff format --check .
.venv\Scripts\python -m mypy .
.venv\Scripts\python -m pytest
```

Equivalen a `lint`, `prettier --check`, `typecheck` y `test` del backend.

## Variables de entorno

| Variable | Uso |
|---|---|
| `APP_ENV` | `development`, `production` o `test` |
| `BACKEND_URL` | URL del backend que entrega el grafo de la red vial |
| `INTERNAL_TOKEN` | Token compartido con el backend para sus endpoints internos; nunca se escribe en `.env.example` |

## Estructura

```
app/
  __init__.py      versión del servicio
  config.py        configuración leída del entorno
  geo.py           distancia haversine, la misma fórmula del backend
  main.py          creación de la aplicación FastAPI
  routes/
    health.py      GET /health
  routing/
    errors.py      NoRouteError, OutsideNetworkError e InvalidPointError
    locator.py     NodeLocator: del clic al nodo más cercano
    result.py      RouteResult y RouteStep
    search.py      motor de búsqueda, dijkstra y a_star
  structures/
    graph.py       grafo dirigido con lista de adyacencia
    min_heap.py    Min-Heap indexado con decrease_key
    stack.py       Pila
    union_find.py  Union-Find con compresión de caminos y unión por tamaño
tests/             pruebas con pytest
  conftest.py      redes de calle de prueba escritas a mano y cuadrículas al azar
  routing/         pruebas de la búsqueda de rutas y del ajuste del clic
  structures/      ejemplos y comparaciones al azar de cada estructura
render.yaml        despliegue en Render (plan gratuito, región Virginia)
```

## Estructuras de datos

Las tres están escritas a mano en `app/structures/`. Trabajan con índices internos de 0 a n−1: al cargar el grafo, cada nodo de `road_nodes` recibe un índice consecutivo, y los ids de la base solo aparecen al entrar y salir del grafo.

| Estructura | Para qué sirve | Operaciones y complejidad |
|---|---|---|
| Grafo dirigido (`RoadGraph`) | Red vial de Pasto. Un tramo de sentido único es una arista y uno de doble sentido son dos. Cada arista guarda el tramo, su longitud, su daño y si recorre el tramo al revés | Agregar nodo o tramo O(1); vecinos de un nodo O(grado) |
| Min-Heap indexado (`IndexedMinHeap`) | Elegir el siguiente nodo en Dijkstra y A* | `push`, `pop_min` y `decrease_key` O(log n); `contains`, `priority_of` y `peek_min` O(1) |
| Union-Find (`UnionFind`) | Encontrar la componente principal de la red y descartar pedazos de vía sueltos | `find`, `union` y `connected` O(α(n)) amortizado, casi constante |
| Pila (`Stack`) | Poner el camino en orden de viaje: la búsqueda lo recorre del destino al origen y la pila lo invierte | `push`, `pop` y `peek` O(1) |

El costo de cruzar una arista se calcula en cada consulta como `longitud × (1 + k × daño)`, porque `k` cambia con el criterio de la ruta: 0 para la más corta, 1 para la equilibrada y 3 para evitar baches. Nunca baja de la longitud, lo que mantiene válida la heurística de A*.

El Union-Find ignora el sentido de las calles: dice si dos nodos están unidos por alguna calle, no si hay un camino que respete los sentidos.

Cada estructura se prueba de dos formas: con ejemplos legibles y con cientos de operaciones al azar (semilla fija) comparadas contra una versión simple y lenta. Después de cada operación se verifican sus invariantes con `is_valid()`.

## Algoritmos de ruta

`app/routing/search.py` tiene un solo motor de búsqueda y dos algoritmos que lo usan. A* es Dijkstra con una estimación de lo que falta para llegar: con una estimación siempre igual a cero se comporta exactamente como Dijkstra.

| Función | Estimación | Se usa para |
|---|---|---|
| `dijkstra(graph, source, target, k)` | Cero | Verificar a A* en las pruebas y comparar cuántos nodos explora cada uno |
| `a_star(graph, source, target, k)` | Distancia en línea recta (haversine) hasta el destino | Responder las rutas |

- **Costo de una arista:** `longitud × (1 + k × daño)`, con `k` igual a 0 (la más corta), 1 (equilibrada) o 3 (evitar baches). La complejidad es O((V + E) log V) porque cada nodo está una sola vez en el Min-Heap indexado y `decrease_key` cuesta O(log V).
- **Por qué A* encuentra siempre la ruta óptima:** la línea recta nunca supera el costo real, y eso se cumple porque el grafo nunca deja una longitud por debajo de la distancia en línea recta entre los dos nodos del tramo. El importador del backend mide cada longitud con las coordenadas de 7 decimales de OpenStreetMap, pero guarda los nodos con 6 decimales, así que un tramo recto puede quedar hasta unos 16 cm más corto que la línea recta entre sus nodos guardados. El grafo sube esa longitud a la línea recta, y rechaza el tramo si está más de 20 cm por debajo, porque ya no es redondeo sino un dato malo.
- **Resultado (`RouteResult`):** los tramos en orden de viaje (con su `segment_id`, si se recorren al revés, longitud, daño y costo), los nodos del camino, la distancia total, el costo total, cuántos nodos exploró la búsqueda y el algoritmo usado. Usa índices internos; la traducción a ids de la base se hace en el bloque 5.
- **Origen igual a destino:** no es un error; da una ruta con cero tramos y distancia cero.
- **Errores con nombre:** `NoRouteError` (no hay camino que respete los sentidos de las calles, aunque los nodos estén unidos por alguna calle), `OutsideNetworkError` (el clic quedó a más de 200 metros de la red, con la distancia real) e `InvalidPointError` (coordenadas inválidas).
- **Ajuste del clic (`NodeLocator`):** toma solo los nodos de la componente principal que encuentra el Union-Find, y devuelve el más cercano con su distancia. La búsqueda es lineal; en la Etapa 4 el Quadtree la reemplaza sin cambiar la interfaz.

Las pruebas comparan Dijkstra con Bellman-Ford, un algoritmo simple y lento, y A* con Dijkstra, sobre cuadrículas de calles al azar con calles de sentido único. También comprueban cada ruta tramo por tramo contra el grafo.

## Reglas del proyecto

- Las estructuras de datos (grafo, Min-Heap, Union-Find, Quadtree) y los algoritmos (A*, Dijkstra, DBSCAN) se escriben a mano. No se usan librerías que las implementen, como `networkx`, `heapq` o `scikit-learn`.
- Las dependencias se fijan con versión exacta y con al menos dos semanas de publicadas.
- Código, comentarios y rutas de la API en inglés; documentación en español.
- Se trabaja directo en `main`, con commits pequeños y mensajes en inglés.

## Despliegue

`render.yaml` describe el servicio web en Render: plan gratuito, región Virginia (la misma del backend), Python 3.13.3 y `GET /health` como comprobación de salud. `BACKEND_URL` e `INTERNAL_TOKEN` se escriben en el panel de Render, nunca en el repositorio. El servicio se crea en Render en el bloque 5 de la Etapa 2.
