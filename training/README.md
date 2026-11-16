# Entrenamiento del detector de baches

Herramientas para preparar los datos, entrenar, medir y exportar el modelo que corre en la
cámara del celular. **No forman parte del servicio de Render**: viven en el repositorio para que
el proceso se pueda repetir, pero no se instalan en producción (`training/requirements.txt` es
aparte de `requirements.txt`).

## Resumen del proceso

1. Descargar los datasets públicos (formato YOLOv8) y anotar su licencia.
2. Revisarlos y juntarlos en un solo dataset de una clase.
3. Entrenar YOLOv8n en Google Colab.
4. Medir con el conjunto de prueba y exportar a ONNX.
5. Copiar el modelo al frontend y completar la ficha (`MODEL_CARD.md`).

La forma más fácil es abrir `training/colab/entrenar_baches.ipynb` en Colab y correr las celdas
en orden. Los mismos pasos, a mano:

```bash
pip install -r training/requirements.txt

# Revisar sin escribir nada (muestra el archivo y la línea de cada problema)
python -m training.prepare --source training/data/raw/potholes --output training/data/pothole --audit-only

# Preparar (varias fuentes: repetir --source)
python -m training.prepare --source training/data/raw/potholes --output training/data/pothole

# Entrenar (50 épocas, 416 px, una clase)
python -m training.train --data training/data/pothole/data.yaml --device 0

# Medir con el conjunto de prueba (escribe metrics.json junto a la corrida)
python -m training.evaluate --weights training/runs/pothole/weights/best.pt \
    --data training/data/pothole/data.yaml

# Exportar para el navegador (escribe model_info.json junto al modelo)
python -m training.export --weights training/runs/pothole/weights/best.pt --format onnx
```

## Qué hace cada módulo

| Módulo | Función |
|---|---|
| `labels.py` | Lee y valida los archivos de etiquetas YOLO (una caja por línea). |
| `classes.py` | Lee las clases y la licencia del `data.yaml` de un dataset. |
| `remap.py` | Deja solo los baches y los pasa a la clase 0 (otros datasets usan otros números). |
| `audit.py` | Revisa una fuente: etiquetas inválidas, clases fuera de rango, imágenes sin cajas. |
| `groups.py` | Agrupa las copias de una misma foto (`nombre.rf.<hash>.jpg`). |
| `split.py` | Reparte los grupos en entrenamiento, validación y prueba (80/10/10, semilla fija). |
| `prepare.py` | Une las fuentes en un dataset único con `data.yaml` y `manifest.json`. |
| `yolo.py` | Único lugar que importa Ultralytics (se instala solo donde se entrena). |
| `train.py`, `evaluate.py`, `export.py` | Entrenar, medir y exportar. |

## Decisiones que conviene recordar

- **Se reparte por foto, no por imagen.** Los datasets de Roboflow traen cada foto original
  varias veces (volteada, con brillo distinto). Si las copias cayeran en conjuntos distintos, la
  prueba sería demasiado fácil y las métricas, engañosas.
- **Ultralytics 8.4.82 fijado.** Desde la 8.4.83 ya no se puede exportar a TensorFlow.js. ONNX
  funciona en cualquier versión y es el formato recomendado; TensorFlow.js queda como opción
  (`--format tfjs`) solo con esa versión y Python menor que 3.13.
- **Las imágenes y los pesos no se suben a Git** (`.gitignore`); solo el código y la ficha.
- **Las partes que llaman a Ultralytics se prueban con un doble** (`tests/training_scripts/fake_yolo.py`):
  verifican los argumentos que se envían, no el entrenamiento real. Eso se comprueba corriendo el cuaderno.

## Pruebas

```bash
pytest tests/training_scripts
```
