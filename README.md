# Urban Road Monitor — servicio de IA

Servicio en Python con FastAPI del proyecto final Urban Road Monitor (Estructura de Datos). Calcula las rutas sobre la red vial de Pasto y, más adelante, agrupará las detecciones de baches.

El servicio no se conecta a la base de datos: el backend le entrega los datos que necesita. El frontend nunca lo llama directamente; solo habla con el backend.

## Estado

Bloque 2 de la Etapa 2: ya están las estructuras base (grafo dirigido, Min-Heap indexado y Union-Find). Los algoritmos de ruta (Dijkstra y A*) llegan en el bloque 3, y el endpoint de rutas en el bloque 5.

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
  main.py          creación de la aplicación FastAPI
  routes/
    health.py      GET /health
  structures/
    graph.py       grafo dirigido con lista de adyacencia
    min_heap.py    Min-Heap indexado con decrease_key
    union_find.py  Union-Find con compresión de caminos y unión por tamaño
tests/             pruebas con pytest
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

El costo de cruzar una arista se calcula en cada consulta como `longitud × (1 + k × daño)`, porque `k` cambia con el criterio de la ruta: 0 para la más corta, 1 para la equilibrada y 3 para evitar baches. Nunca baja de la longitud, lo que mantiene válida la heurística de A*.

El Union-Find ignora el sentido de las calles: dice si dos nodos están unidos por alguna calle, no si hay un camino que respete los sentidos.

Cada estructura se prueba de dos formas: con ejemplos legibles y con cientos de operaciones al azar (semilla fija) comparadas contra una versión simple y lenta. Después de cada operación se verifican sus invariantes con `is_valid()`.

## Reglas del proyecto

- Las estructuras de datos (grafo, Min-Heap, Union-Find, Quadtree) y los algoritmos (A*, Dijkstra, DBSCAN) se escriben a mano. No se usan librerías que las implementen, como `networkx`, `heapq` o `scikit-learn`.
- Las dependencias se fijan con versión exacta y con al menos dos semanas de publicadas.
- Código, comentarios y rutas de la API en inglés; documentación en español.
- Se trabaja directo en `main`, con commits pequeños y mensajes en inglés.

## Despliegue

`render.yaml` describe el servicio web en Render: plan gratuito, región Virginia (la misma del backend), Python 3.13.3 y `GET /health` como comprobación de salud. `BACKEND_URL` e `INTERNAL_TOKEN` se escriben en el panel de Render, nunca en el repositorio. El servicio se crea en Render en el bloque 5 de la Etapa 2.
