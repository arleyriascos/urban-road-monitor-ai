# Ficha del modelo: detector de baches

> Estado: **entrenado** (50 épocas en Colab, GPU T4). Las cifras salen de `metrics.json` y los
> datos de `manifest.json`, que quedaron en Drive (`urban-road-monitor/modelo`).

## Qué es

Un detector de objetos YOLOv8n con una sola clase (`pothole`, bache). Corre en el navegador del
celular (ONNX con onnxruntime-web) y marca los baches que ve la cámara mientras se conduce.

## Para qué sirve y para qué no

- Sirve para sugerir baches en tiempo real a una persona que conduce o va de pasajera.
- No mide la profundidad ni el peligro de un bache: la severidad la calcula el servidor con la
  repetición de reportes de varias personas.
- No es un sistema de seguridad ni reemplaza una inspección de la vía.

## Datos de entrenamiento

| Dataset | Origen | Licencia | Imágenes | Estado de la licencia |
|---|---|---|---|---|
| Pothole Detection v9 (Intel Unnati) | Roboflow Universe | MIT | 3770 | Declarada en el `data.yaml` del dataset |

- Es el único dataset de esta versión del modelo. Las clases `Drain Hole` y `Sewer Cover` del
  dataset se descartan y todo queda en la clase única `pothole`; 6 etiquetas por reparto venían
  como polígonos y se convirtieron en cajas.
- Quedaron 2997 imágenes de entrenamiento (5622 baches), 389 de validación (761) y 384 de prueba (711).
- Solo se usan datasets públicos con licencia que permita su uso; las fotos de Pasto son opcionales.
- Las copias de una misma foto (rotaciones, brillo) quedan siempre en el mismo conjunto
  (entrenamiento, validación o prueba), para que la prueba sea honesta. Ver `training/groups.py`.
- Reparto: 80 % entrenamiento, 10 % validación, 10 % prueba, con semilla 42.

## Entrenamiento

- Modelo base `yolov8n.pt`, 50 épocas, imagen de 416 px, una clase.
- Ultralytics 8.4.82 (versión fija en `training/requirements.txt`).
- Comando: ver `training/README.md`.

## Resultados en el conjunto de prueba

| Métrica | Valor |
|---|---|
| mAP50 | 0.768 |
| mAP50-95 | 0.498 |
| Precisión | 0.816 |
| Exhaustividad | 0.700 |
| F1 | 0.754 |
| Tamaño del archivo ONNX | 12.2 MB |

Con la exhaustividad de 0.70, el modelo deja pasar cerca de 3 de cada 10 baches del conjunto de
prueba. En validación dio mAP50 0.768, igual que en prueba.

La precisión y la exhaustividad son las que Ultralytics da en la confianza donde F1 es máxima.

## Límites conocidos

- Se entrenó con un solo dataset público, que viene de otras ciudades y otros pavimentos; en Pasto puede acertar menos.
- Poca luz, lluvia, sombras fuertes y parabrisas sucios bajan la exhaustividad.
- Puede confundir tapas de alcantarilla, parches y manchas de aceite con baches.
- En celulares lentos la detección se hace con menos cuadros por segundo.

## Privacidad

El modelo corre en el celular: las imágenes de la cámara no se envían a ningún servidor. Solo se
envían la posición, la hora y el tamaño aproximado de cada detección.
