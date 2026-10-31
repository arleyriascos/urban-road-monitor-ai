# Urban Road Monitor — servicio de IA

Servicio en Python con FastAPI del proyecto final Urban Road Monitor (Estructura de Datos). Calcula las rutas sobre la red vial de Pasto y, más adelante, agrupará las detecciones de baches.

El servicio no se conecta a la base de datos: el backend le entrega los datos que necesita. El frontend nunca lo llama directamente; solo habla con el backend.

## Estado

Bloque 1 de la Etapa 2: estructura base del servicio y endpoint de salud. Las estructuras de datos y los algoritmos de ruta llegan en los bloques siguientes.

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
tests/             pruebas con pytest
render.yaml        despliegue en Render (plan gratuito, región Virginia)
```

## Reglas del proyecto

- Las estructuras de datos (grafo, Min-Heap, Union-Find, Quadtree) y los algoritmos (A*, Dijkstra, DBSCAN) se escriben a mano. No se usan librerías que las implementen, como `networkx`, `heapq` o `scikit-learn`.
- Las dependencias se fijan con versión exacta y con al menos dos semanas de publicadas.
- Código, comentarios y rutas de la API en inglés; documentación en español.
- Se trabaja directo en `main`, con commits pequeños y mensajes en inglés.

## Despliegue

`render.yaml` describe el servicio web en Render: plan gratuito, región Virginia (la misma del backend), Python 3.13.3 y `GET /health` como comprobación de salud. `BACKEND_URL` e `INTERNAL_TOKEN` se escriben en el panel de Render, nunca en el repositorio. El servicio se crea en Render en el bloque 5 de la Etapa 2.
