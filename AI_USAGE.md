# Uso de inteligencia artificial

## Herramienta utilizada

Codex se utilizó como asistente de ingeniería para:

- leer el enunciado y analizar la estructura de los cuatro CSV;
- proponer la separación entre carga, validación, proyección, compra, alertas e interfaz;
- crear una implementación inicial del motor y del dashboard;
- implementar una variante opcional de chat con Gemini sin mover los cálculos fuera de Python;
- generar pruebas unitarias y de integración;
- documentar decisiones, limitaciones y una posible integración futura con Odoo;
- ejecutar revisiones automáticas de sintaxis, pruebas y arranque de la aplicación.

La IA no sustituyó la validación humana. Las fórmulas y los resultados se contrastaron programáticamente contra los CSV entregados, incluyendo los seis casos esperados del reto.

## Revisión realizada durante esta sesión

Se verificaron explícitamente:

- columnas, cardinalidad, nulos, duplicados, tipos y cobertura sucursal–ingrediente;
- factores reales de 25 kg, 2.55 kg, 0.25 kg y demás formatos del catálogo;
- la omisión de mozzarella en Brisas del Golf;
- el ingrediente desconocido `aji_chombo` en Costa del Este;
- la proyección lineal de harina en Costa del Este;
- la exclusión robusta del valor de pepperoni de Marbella en S3;
- los sobrepedidos de cebolla y albahaca;
- que el dashboard y el asistente local funcionen sin claves externas y sean el respaldo de la integración opcional.

## Gemini en la aplicación

La variante `app_intelligent.py` puede consultar `gemini-3.6-flash` mediante el SDK oficial `google-genai`. Su función se limita a interpretar y redactar a partir de resultados que Python ya calculó. El modelo no proyecta consumo, no resta inventario, no aplica `ceil` y no decide formatos recomendados.

Antes de cada consulta se selecciona un subconjunto relevante y limitado del DataFrame procesado, se ordena por severidad y se convierte a JSON con un esquema explícito. La respuesta también debe tener una estructura fija con texto, identificadores de evidencia y una advertencia opcional. El programa valida esos campos, comprueba que las evidencias hayan sido enviadas y rechaza respuestas que expongan secretos o introduzcan datos inexistentes.

Durante el desarrollo no se proporcionó una clave real ni se afirmó haber validado una respuesta contra el servicio en vivo. Las rutas de éxito, límite `429`, respuesta inválida, prompt injection, ausencia de clave y fallback se prueban con clientes simulados. El modo local continúa disponible si Gemini no está configurado o falla.

## Ejemplo real de prompt utilizado

El prompt principal solicitó construir **“Barrio Pizza | Asistente Inteligente de Compras”** en Python y Streamlit, inspeccionar completamente los CSV antes de programar, usar MAD y una tendencia lineal con umbrales explícitos, respetar las fórmulas de compra, separar alertas de calidad y anomalías, crear pruebas con `pytest`, documentar el uso de IA y validar el arranque headless.

Otro prompt real solicitó crear una variante `intelligent`, integrar Gemini con `google-genai`, enviar solo contexto compacto, exigir evidencia estructurada, proteger la clave y mantener un fallback local para errores o límites del proveedor.

No se inventan conversaciones adicionales ni prompts que no ocurrieron.

## Riesgos de usar IA y mitigación

| Riesgo | Mitigación aplicada |
|---|---|
| Inventar columnas, costos o métricas no disponibles | El esquema obligatorio está declarado y las métricas se limitan a consumo, inventario, formatos, estados e incidencias presentes. |
| Asumir que un nulo significa cero | Los nulos se reportan; inventario o histórico faltante producen una línea no calculable. |
| Confundir unidad base con formato de compra | Las conversiones están centralizadas y cubiertas por pruebas para 25, 2.55 y 0.25. |
| Forzar umbrales para coincidir con respuestas esperadas | MAD, z-score, R² y cambio relativo están implementados con los umbrales definidos antes de comparar los resultados. |
| Ocultar duplicados o artículos desconocidos | Se registran como incidencias y no reciben metadata inventada. |
| Generar una interfaz convincente con lógica incorrecta | La lógica vive fuera de Streamlit y se prueba directamente con `pytest`. |
| Permitir que el modelo recalcule o altere cifras | El contexto contiene resultados finales calculados por Python y el mensaje de sistema prohíbe recalcularlos. |
| Exponer la clave o seguir una instrucción maliciosa del usuario | La clave nunca forma parte del contexto; se detectan intentos de prompt injection y se valida que ningún secreto aparezca en la salida. |
| Enviar más información comercial de la necesaria | Se filtran filas relevantes, se limita su cantidad y se usa una lista cerrada de columnas. En producción debe revisarse la política de privacidad antes de activar el servicio. |
| Depender de la disponibilidad o cuota gratuita de Gemini | Los errores, tiempos de espera y respuestas `429` activan el asistente local y no detienen el resto de la aplicación. |
| Declarar validaciones no ejecutadas | Los resultados finales deben reportar únicamente comandos realmente completados. |

## Partes que requieren revisión personal del candidato

Antes de entregar, el candidato debe completar honestamente estos marcadores:

- **[PENDIENTE — describir qué código revisaste manualmente y qué cambios propios hiciste]**
- **[PENDIENTE — explicar qué aprendiste o qué decisión técnica defenderías en entrevista]**
- **[PENDIENTE — indicar si utilizaste otra herramienta de IA además de Codex]**
- **[PENDIENTE — agregar cualquier prompt adicional que realmente hayas utilizado]**

También debe revisar visualmente la aplicación completa, grabar el video con sus propias palabras y aprobar el contenido final antes de publicarlo.
