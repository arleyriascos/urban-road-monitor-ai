# Urban Road Monitor — servicio de IA

Servicio en Python con FastAPI del proyecto final Urban Road Monitor (Estructura de Datos). Calcula las rutas sobre la red vial de Pasto y, más adelante, agrupará las detecciones de baches.

El servicio no se conecta a la base de datos: el backend le entrega los datos que necesita. El frontend nunca lo llama directamente; solo habla con el backend.

## Estado

Bloque 5 de la Etapa 2: el servicio descarga el grafo de la red vial desde el backend, lo mantiene al día según su versión y responde rutas por HTTP en `POST /routes`, protegido con un token compartido. Debajo están las estructuras (grafo dirigido, Min-Heap indexado, Union-Find y Pila) y los algoritmos (Dijkstra y A*) de los bloques 2 y 3.

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

- Salud y estado del grafo: http://localhost:8000/health
- Documentación de la API: http://localhost:8000/docs

Para calcular rutas en tu computador, el backend debe estar corriendo (por defecto en `http://localhost:3000`) y los dos `.env` deben tener el mismo `INTERNAL_TOKEN`. Sin token, el servicio arranca igual, pero `POST /routes` responde 404 y no descarga el grafo.

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
| `BACKEND_URL` | Dirección del backend que entrega el grafo. En producción debe empezar por `https://`, para que el token nunca viaje en texto plano; no puede llevar usuario, contraseña ni parámetros |
| `INTERNAL_TOKEN` | Token compartido con el backend, de al menos 32 caracteres y el mismo valor en los dos servicios. Protege `POST /routes` y sirve para descargar el grafo. Vacío apaga `POST /routes` (responde 404). Nunca se escribe en `.env.example` |
| `MAX_SNAP_DISTANCE_M` | Opcional. A cuántos metros de la red puede quedar un clic (por defecto 200) |

## Endpoints

| Método | Ruta | Protección | Respuesta |
|---|---|---|---|
| GET | `/health` | Pública | Siempre 200, con el estado del grafo: si está cargado, su versión, cuántos nodos y tramos tiene y cuándo se cargó |
| POST | `/routes` | `Authorization: Bearer <INTERNAL_TOKEN>` | La ruta más barata entre dos clics |
| GET | `/docs` | Pública | Documentación interactiva de FastAPI |

### `POST /routes`

Solo lo llama el backend. La petición lleva los dos clics, `k` (por defecto 1), la `graphVersion` que calculó el backend y, opcionalmente, `algorithm` (`astar`, por defecto, o `dijkstra`, los mismos nombres que guarda la tabla `route_requests`):

```json
{
  "origin": { "latitude": 1.2136, "longitude": -77.2811 },
  "destination": { "latitude": 1.2150, "longitude": -77.2790 },
  "k": 1,
  "graphVersion": "940ab0350236d4a94de0b11d6ed78931",
  "algorithm": "astar"
}
```

La respuesta trae ids de la base de datos, nunca índices internos: el algoritmo, la `graphVersion` realmente usada, el nodo al que se ajustó cada clic (`origin` y `destination`, con su distancia), `totalLengthM`, `totalCost`, `exploredNodes`, `computationMs` (solo la búsqueda), `nodeIds` y `steps` (cada tramo con `segmentId`, `reversed`, `lengthM`, `damageScore` y `cost`). Las longitudes van redondeadas a centímetros y los costos a cuatro decimales, la precisión de `route_requests`. Mismo origen y destino da una ruta sin tramos.

Los errores tienen la misma forma que en el backend, `{ "error": { "code", "message", "details" } }`:

| Estado | Código | Cuándo |
|---|---|---|
| 401 | `UNAUTHORIZED` | Falta el token o es incorrecto; el token se revisa antes que el cuerpo |
| 404 | `NOT_FOUND` | `INTERNAL_TOKEN` no está configurado (igual que una ruta inexistente) |
| 404 | `NO_ROUTE` | Los sentidos únicos impiden el camino; `details` trae los dos nodos |
| 422 | `OUTSIDE_NETWORK` | Un clic quedó lejos de la red; `details` dice cuál (`origin` o `destination`) y a cuántos metros |
| 422 | `INVALID_REQUEST` | Cuerpo mal formado, coordenadas fuera de rango, `k` negativo o un campo desconocido |
| 503 | `GRAPH_UNAVAILABLE` | No hay ningún grafo cargado y no se pudo descargar |

## Cómo se carga y se mantiene el grafo

El grafo vive en memoria (unos 5 MB con la red de Pasto) y se descarga del backend con `GET /internal/graph`.

1. **En segundo plano al arrancar.** El arranque y `/health` nunca esperan al backend, que puede estar dormido en Render. Si llega una ruta antes de que termine, espera a esa misma descarga.
2. **Una sola descarga a la vez.** Un candado hace que varias peticiones simultáneas compartan la misma descarga.
3. **Cambio atómico.** El grafo nuevo se construye completo antes de reemplazar al anterior; las peticiones en curso terminan con el grafo con el que empezaron.
4. **Recarga por versión, con enfriamiento.** Si la `graphVersion` de una petición no coincide con la cargada, se recarga, salvo que la última descarga haya sido hace menos de 10 segundos.
5. **La versión guardada es la de la descarga**, y la respuesta dice cuál se usó: el backend solo guarda en caché una ruta si coincide con la que pidió.
6. **Si una recarga falla**, se sigue respondiendo con el grafo anterior; sin ningún grafo, la respuesta es 503. Tras un fallo no se vuelve a intentar hasta pasados 10 segundos.
7. **Los datos inválidos no reemplazan al grafo cargado**: el grafo los rechaza y queda el anterior.

La descarga usa `httpx2`: espera hasta 10 s para conectar y 45 s para leer (Render retiene la petición mientras un servicio dormido arranca), e intenta una segunda vez, 3 s después, solo si falló la conexión, se agotó el tiempo o el backend respondió 502, 503 o 504. Un 401 (los tokens no coinciden) o un 404 (el backend no tiene token) no se reintentan, y el registro dice exactamente qué revisar. Las redirecciones no se siguen, para que el token nunca vaya a otra dirección, y el token nunca se escribe en los registros.

## Estructura

```
app/
  __init__.py      versión del servicio
  config.py        configuración leída del entorno, con sus validaciones
  errors.py        errores en JSON con la misma forma que el backend
  geo.py           distancia haversine, la misma fórmula del backend
  main.py          creación de la aplicación, calentamiento del grafo y registros
  security.py      protección de POST /routes con INTERNAL_TOKEN
  graph/
    client.py      descarga del grafo desde el backend, con sus reintentos
    payload.py     forma de GET /internal/graph
    store.py       el grafo en memoria y las reglas para recargarlo
  routes/
    health.py      GET /health
    route_search.py  POST /routes
  routing/
    contract.py    petición y respuesta de POST /routes
    errors.py      NoRouteError, OutsideNetworkError e InvalidPointError
    locator.py     NodeLocator: del clic al nodo más cercano
    result.py      RouteResult y RouteStep
    search.py      motor de búsqueda, dijkstra y a_star
    service.py     responde una ruta con el grafo en memoria
  structures/
    graph.py       grafo dirigido con lista de adyacencia
    min_heap.py    Min-Heap indexado con decrease_key
    stack.py       Pila
    union_find.py  Union-Find con compresión de caminos y unión por tamaño
tests/             pruebas con pytest
  conftest.py      redes de calle de prueba escritas a mano y cuadrículas al azar
  api/             POST /routes, el token y la forma de los errores
  graph/           descarga del grafo (con un backend simulado) y sus reglas de recarga
  routing/         pruebas de la búsqueda de rutas y del ajuste del clic
  structures/      ejemplos y comparaciones al azar de cada estructura
render.yaml        despliegue en Render (plan gratuito, región Virginia)
```

## Estructuras de datos

Las cuatro están escritas a mano en `app/structures/`. Trabajan con índices internos de 0 a n−1: al cargar el grafo, cada nodo de `road_nodes` recibe un índice consecutivo, y los ids de la base solo aparecen al entrar y salir del grafo.

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
- **Resultado (`RouteResult`):** los tramos en orden de viaje (con su `segment_id`, si se recorren al revés, longitud, daño y costo), los nodos del camino, la distancia total, el costo total, cuántos nodos exploró la búsqueda y el algoritmo usado. Usa índices internos; `POST /routes` los traduce a los ids de la base.
- **Origen igual a destino:** no es un error; da una ruta con cero tramos y distancia cero.
- **Errores con nombre:** `NoRouteError` (no hay camino que respete los sentidos de las calles, aunque los nodos estén unidos por alguna calle), `OutsideNetworkError` (el clic quedó más lejos de la red que `MAX_SNAP_DISTANCE_M`, con la distancia real) e `InvalidPointError` (coordenadas inválidas).
- **Ajuste del clic (`NodeLocator`):** toma solo los nodos de la componente principal que encuentra el Union-Find, y devuelve el más cercano con su distancia. La búsqueda es lineal; en la Etapa 4 el Quadtree la reemplaza sin cambiar la interfaz.

Las pruebas comparan Dijkstra con Bellman-Ford, un algoritmo simple y lento, y A* con Dijkstra, sobre cuadrículas de calles al azar con calles de sentido único. También comprueban cada ruta tramo por tramo contra el grafo.

## Reglas del proyecto

- Las estructuras de datos (grafo, Min-Heap, Union-Find, Quadtree) y los algoritmos (A*, Dijkstra, DBSCAN) se escriben a mano. No se usan librerías que las implementen, como `networkx`, `heapq` o `scikit-learn`.
- Las dependencias se fijan con versión exacta y con al menos dos semanas de publicadas.
- Código, comentarios y rutas de la API en inglés; documentación en español.
- Se trabaja directo en `main`, con commits pequeños y mensajes en inglés.

## Despliegue

`render.yaml` describe el servicio web en Render: plan gratuito, región Virginia (la misma del backend), Python 3.13.3 y `GET /health` como comprobación de salud.

1. El backend debe tener `INTERNAL_TOKEN` configurado en su panel de Render (sin él, `/internal/graph` responde 404 y este servicio no puede cargar el grafo).
2. En Render se crea el servicio desde el Blueprint de este repositorio. Render pide `BACKEND_URL` (la dirección `https://` del backend) e `INTERNAL_TOKEN` (el mismo valor del backend); los dos se escriben en el panel, nunca en el repositorio.
3. Cuando termina el despliegue, `GET /health` debe mostrar `"loaded": true` con los nodos y tramos de Pasto. Si muestra `false`, los registros del servicio en Render dicen la causa (tokens distintos, backend sin token o backend dormido).

En el plan gratuito los dos servicios se duermen tras unos minutos sin uso. Como el backend es quien llama a `POST /routes`, siempre está despierto cuando este servicio necesita el grafo: la primera ruta después de dormir solo espera el despertar de este servicio y unos 300 ms de descarga.
