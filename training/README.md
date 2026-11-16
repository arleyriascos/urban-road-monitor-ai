# Entrenamiento del modelo de baches

Esta carpeta tiene lo necesario para entrenar el modelo de visión de Urban Road Monitor: un YOLOv8n de una sola clase, "bache", que luego corre en el navegador del celular.

No forma parte del servicio que corre en Render. Ese servicio solo usa `requirements.txt` de la raíz del repositorio; las herramientas de entrenamiento tienen su propio `training/requirements.txt`.

## Qué hace cada paso

1. **Preparar los datos:** revisar los datasets descargados, dejar una sola clase y repartir las fotos entre entrenamiento, validación y prueba sin que una foto y sus copias aumentadas queden en grupos distintos.
2. **Entrenar:** ajustar un YOLOv8n ya entrenado con esas fotos.
3. **Evaluar:** medir qué tan bien detecta baches en fotos que nunca vio.
4. **Exportar:** convertir el modelo a un formato que corra en el navegador.

Los pasos se van agregando a esta carpeta en ese orden. Esta primera versión del README solo describe el objetivo; la guía completa queda al final.
