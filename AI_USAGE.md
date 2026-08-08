# Uso de inteligencia artificial

## Herramienta utilizada

ChatGPT + Codex se utilizó como asistente de ingeniería para:

- leer el enunciado y analizar la estructura de los cuatro CSV;
- proponer la separación entre carga, validación, proyección, compra, alertas e interfaz;
- crear una implementación inicial del motor y del dashboard;
- implementar una variante opcional de chat con Gemini sin mover los cálculos fuera de Python;
- generar pruebas unitarias y de integración;
- documentar decisiones, limitaciones y una posible integración futura con Odoo;
- ejecutar revisiones automáticas de sintaxis, pruebas y arranque de la aplicación.


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

La clave de Gemini se configuró mediante secretos y no se escribió directamente en el código ni se compartió en el repositorio. Se comprobó desde la aplicación que el servicio podía responder utilizando los resultados calculados y devolver identificadores de evidencia. Las rutas de límite `429`, respuesta inválida, prompt injection, ausencia de clave y fallback también se cubren mediante clientes simulados para no depender del servicio externo durante las pruebas automatizadas. El modo local continúa disponible si Gemini no está configurado o falla.

## Ejemplo real de prompt utilizado

El prompt principal solicitó construir **“Barrio Pizza | Asistente Inteligente de Compras”** en Python y Streamlit, inspeccionar completamente los CSV antes de programar, usar MAD y una tendencia lineal con umbrales explícitos, respetar las fórmulas de compra, separar alertas de calidad y anomalías, crear pruebas con `pytest`, documentar el uso de IA y validar el arranque headless.

Otro prompt real que hice fue crear una variante `intelligent`, integrar Gemini con `google-genai`, enviar solo contexto compacto, exigir evidencia estructurada, proteger la clave y mantener un fallback local para errores o límites del proveedor.



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

## Revisión y participación personal

### Qué revisé y qué cambios propuse

Probé personalmente la aplicación en el navegador y recorrí sus diferentes secciones. Revisé las alertas, recomendaciones, gráficos, filtros, comparación entre sucursales, asistente local, chat con Gemini y archivos descargables. También comprobé casos importantes como la mozzarella omitida, el faltante de harina, el valor atípico de pepperoni y los sobrepedidos de cebolla y albahaca.

Durante el proceso fui proponiendo cambios para que la herramienta fuera más fácil de entender para cualquier persona a simple vista. Por ejemplo, pedí simplificar algunas explicaciones técnicas, aclarar qué significa un formato de compra, mejorar los filtros, separar el asistente en su propia pestaña y hacer que las comparaciones entre sucursales fueran más claras. También trabajé en detalles visuales como la barra lateral, el tamaño de los gráficos, el cursor de pizza y los reportes descargables en Excel.

### Qué aprendí y qué decisión defendería

Aprendí que no siempre es necesario utilizar un modelo complicado para construir una buena solución de inteligencia artificial. En este reto era más importante que los cálculos fueran correctos, claros y fáciles de explicar.

Una decisión que defendería en una entrevista es el método de proyección utilizado. La herramienta detecta semanas atípicas con MAD y utiliza una tendencia lineal solamente cuando realmente existe suficiente evidencia. Cuando no hay una tendencia fuerte, usa un promedio limpio. Me parece una buena decisión porque evita generar alertas falsas y permite explicar de dónde salió cada recomendación.

También defendería que Gemini no haga los cálculos. Python calcula el consumo esperado, la necesidad y los formatos recomendados. Gemini solamente ayuda a explicar esos resultados en términos mas amigables.

### Otras herramientas de IA utilizadas

Además de ChatGPT y Codex para apoyar el desarrollo, integré y probé Gemini dentro de la aplicación utilizando el SDK oficial `google-genai`.

Gemini se usa solamente para responder preguntas sobre resultados que Python ya calculó. La clave se configuró mediante secretos y nunca se escribió directamente en el código ni se subió a GitHub. También se dejó el asistente local como respaldo por si Gemini no está configurado, falla o alcanza un límite de uso.

### Otros prompts utilizados

Durante el desarrollo también fui haciendo solicitudes más específicas, como:

- revisar completamente la comparación de órdenes entre sucursales;
- evitar que una misma línea se contara varias veces por tener diferentes alertas;
- explicar resultados estadísticos con palabras más sencillas;
- rediseñar el dashboard tomando como referencia la página pública de Barrio Pizza;
- mejorar la barra lateral, los gráficos, los filtros y la navegación;
- agregar y ajustar el cursor de pizza;
- integrar Gemini sin permitirle cambiar o recalcular cifras;
- ordenar mejor el chat y agregar algunas preguntas sugeridas;
- explicar dentro del dashboard qué significa un formato de compra;
- crear reportes Excel más visuales como alternativa a los CSV;
- probar el funcionamiento, la compilación y el arranque de la aplicación.


