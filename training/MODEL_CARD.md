# Ficha del modelo: detector de baches

> Estado: **pendiente de entrenar**. Los campos marcados con `POR COMPLETAR` se llenan con
> `metrics.json` y `manifest.json` cuando termine el entrenamiento en Colab.

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
| Potholes Detection | Roboflow Universe | POR COMPLETAR | POR COMPLETAR | Confirmar en la página |
| Otros datasets abiertos | POR COMPLETAR | POR COMPLETAR | POR COMPLETAR | Confirmar en la página |

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
| mAP50 | POR COMPLETAR |
| mAP50-95 | POR COMPLETAR |
| Precisión | POR COMPLETAR |
| Exhaustividad | POR COMPLETAR |
| F1 | POR COMPLETAR |
| Tamaño del archivo ONNX | POR COMPLETAR |

La precisión y la exhaustividad son las que Ultralytics da en la confianza donde F1 es máxima.

## Límites conocidos

- Los datasets públicos vienen de otras ciudades y otros pavimentos; en Pasto puede acertar menos.
- Poca luz, lluvia, sombras fuertes y parabrisas sucios bajan la exhaustividad.
- Puede confundir tapas de alcantarilla, parches y manchas de aceite con baches.
- En celulares lentos la detección se hace con menos cuadros por segundo.

## Privacidad

El modelo corre en el celular: las imágenes de la cámara no se envían a ningún servidor. Solo se
envían la posición, la hora y el tamaño aproximado de cada detección.
