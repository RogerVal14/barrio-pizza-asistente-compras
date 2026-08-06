# Guion sugerido para el video (3–5 minutos)

Duración objetivo: **4 minutos y 30 segundos**. La idea es hablar con naturalidad y usar el dashboard como apoyo, no leer cada texto.

## 0:00–0:25 · El problema

“Cada sucursal arma una orden semanal en sacos, cajas o paquetes, pero el consumo y el inventario están en otras unidades. Revisarlo al ojo toma tiempo y puede esconder tanto quiebres como desperdicio. Construí este asistente para que la gerente vea qué requiere atención antes de aprobar la compra.”

## 0:25–0:50 · Resumen ejecutivo

Abrir **Resumen ejecutivo**.

“Esta primera pantalla prioriza decisiones. Arriba veo cuántas líneas fueron revisadas, cuáles están correctas, los riesgos de quiebre, las omisiones, sobrepedidos y errores de datos. Los gráficos permiten ubicar rápidamente qué sucursal concentra alertas y de qué tipo son.”

Mencionar que los filtros laterales cambian la vista y que la recomendación requiere aprobación humana.

## 0:50–1:10 · Producto omitido

Ir a **Alertas** y mostrar mozzarella de Brisas del Golf.

“Brisas del Golf no incluyó mozzarella. La cuadrícula completa detecta la ausencia, la interpreta como cero formatos solicitados solo para evaluar la necesidad y conserva la etiqueta de producto omitido. La recomendación es 18 cajas de 10 kilos.”

## 1:10–1:35 · Tendencia creciente

Ir a **Detalle por sucursal**, seleccionar Costa del Este y Harina 00.

“Aquí el consumo crece de forma muy consistente. La regresión supera los umbrales de R² y cambio relativo, por eso se proyectan aproximadamente 330.27 kilos. Con 30 kilos de inventario, se necesitan 13 sacos de 25; la sucursal pidió 6 y faltan 7.”

## 1:35–2:00 · Valor atípico

Seleccionar Marbella y Pepperoni. Activar la comparación con promedio simple.

“En S3 aparecen 150 kilos, muy lejos del patrón. MAD lo identifica como atípico y, como quedan al menos cuatro semanas, lo excluye de la proyección robusta. El resultado limpio es 29 kilos. Con 4.7 de stock, cinco cajas son correctas. El promedio simple habría creado una señal falsa.”

## 2:00–2:20 · Sobrepedido perecedero

Mostrar Via Argentina y Albahaca fresca.

“Via Argentina pidió 20 paquetes y la recomendación es 2. El excedente es de 18 paquetes. La alerta tiene prioridad media porque la albahaca es perecedera, así que conviene revisarla antes de enviar la orden.”

Abrir brevemente **Comportamiento inusual entre sucursales**.

“La comparación entre sucursales aporta contexto al sobrepedido: Via Argentina está en 10 veces su recomendación, mientras las otras sucursales tienen una mediana de una vez. Como solo hay cuatro sucursales, lo presento como comportamiento inusual con confianza moderada, no como anomalía confirmada. Esta señal se superpone con el sobrepedido y no se cuenta como otro producto.”

## 2:20–2:50 · Edición y recálculo

Abrir **Simulador de orden** y cambiar una cantidad.

“La gerente puede cargar un CSV o editar directamente. Al modificar formatos, se repiten validaciones, proyección y clasificación. También puede restablecer la orden original. Si falta una columna o aparece un dato inválido, la aplicación no lo convierte silenciosamente.”

## 2:50–3:15 · Orden corregida por proveedor

Abrir **Orden corregida**.

“La salida es una orden completa con cantidad original, recomendada y diferencia. Está agrupada y descargable por proveedor. `aji_chombo`, que no existe en catálogo, queda separado y no entra en ninguna orden porque no sería correcto inventar su proveedor o formato.”

## 3:15–3:35 · Calidad de datos

Abrir **Calidad de datos**.

“Separé tres conceptos: alertas de compra, incidencias de calidad y anomalías históricas. Así una observación extraña no se presenta como si fuera una decisión automática de compra. Cada incidencia explica por qué importa.”

## 3:35–3:55 · Método

Abrir **Metodología**.

“El método es deliberadamente simple de defender: MAD para extremos, regresión solo con tendencia fuerte y promedio limpio en los demás casos. La compra usa techo matemático por formato completo. El sobrante dentro del último formato es redondeo normal, no sobrepedido.”

## 3:55–4:10 · Uso de IA

“Usé Codex para analizar el reto, proponer la arquitectura, crear pruebas y revisar el código. No delegué la validez del resultado: las fórmulas y los seis casos esperados se contrastan con pruebas. El archivo AI_USAGE documenta riesgos, mitigaciones y lo que aún debo completar personalmente.”

## 4:10–4:25 · Futuro con Odoo

“Esto todavía no está conectado a Odoo. En producción leería catálogo, existencias y movimientos mediante API, generaría borradores por proveedor y mantendría aprobación humana, permisos y auditoría. Empezaría en staging, sin escribir directamente en producción.”

## 4:25–4:35 · Cierre

“El resultado convierte cuatro CSV en una revisión semanal rápida, transparente y accionable. El siguiente paso sería validarlo con la gerente de compras y publicarlo para probar el flujo completo.”

## Antes de grabar

- Ejecutar `pytest` y luego `streamlit run app.py`.
- Practicar una vez para mantener el video debajo de cinco minutos.
- Evitar leer números que no estén visibles en pantalla.
- Probar el enlace del video y el de la aplicación en una ventana de incógnito.
