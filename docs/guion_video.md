# Guion sugerido para el video (3–5 minutos)

Duración objetivo: **4 minutos y 30 segundos**. La idea es hablar con naturalidad y usar el dashboard como apoyo. No es necesario leer todos los textos ni mostrar todas las tablas.

## 0:00–0:25 · El problema de negocio

Mostrar la aplicación desde **Vista ejecutiva**.

> “Cada sucursal arma su orden semanal en sacos, cajas o paquetes, mientras que el consumo y el inventario se registran en unidades como kilos o litros. Revisar todo manualmente toma tiempo y puede esconder faltantes o sobrepedidos. Construí este asistente para que la gerente identifique en pocos segundos qué necesita revisar antes de aprobar una compra.”

## 0:25–0:50 · Vista ejecutiva

Señalar los indicadores superiores y la cola de decisiones.

> “La Vista ejecutiva resume las 88 combinaciones de sucursal e ingrediente. Aquí puedo ver cuántas líneas están bien, los riesgos de quiebre, los sobrepedidos y los errores de datos. Las tarjetas prioritarias me dicen directamente qué producto cambiar, en qué sucursal y en qué formato de compra. Las recomendaciones siempre quedan pendientes de aprobación humana.”

Mencionar brevemente que el margen de seguridad está en **0%** y que los filtros laterales cambian el alcance de la revisión.

## 0:50–1:15 · Producto omitido y faltante

Abrir **Alertas → Alertas de compra**.

> “Brisas del Golf no incluyó mozzarella en su orden. La aplicación detecta la ausencia, conserva el diagnóstico de producto omitido y recomienda agregar 18 cajas de 10 kilos. También vemos que Costa del Este pidió 6 sacos de Harina 00, pero necesita 13; por eso faltan 7 sacos de 25 kilos.”

Mostrar el botón **Descargar reporte visual de alertas (Excel)**.

> “La gerente puede descargar un reporte visual con resumen, decisiones prioritarias y detalle completo. El CSV se mantiene como una opción avanzada.”

## 1:15–1:35 · Comparación entre sucursales

Abrir **Alertas → Comportamiento inusual entre sucursales**.

> “Esta comparación agrega contexto. Por ejemplo, Via Argentina está pidiendo albahaca muy por encima de su recomendación y del comportamiento de las otras sucursales. Como solo tenemos cuatro sucursales, lo presento como comportamiento inusual con confianza moderada, no como una anomalía confirmada. Si coincide con un sobrepedido, sigue siendo una sola línea de producto y no se cuenta dos veces.”

## 1:35–2:05 · Tendencia creciente

Abrir **Sucursales → Ver historial de un ingrediente**. Seleccionar **Costa del Este** y **Harina 00**.

> “El consumo de Harina 00 crece de forma consistente. La regresión supera los umbrales de R² y cambio relativo, por eso se usa una tendencia lineal y se proyectan aproximadamente 330,27 kilos. Con 30 kilos de inventario se necesitan 13 sacos de 25. La sucursal pidió 6, así que faltan 7.”

Señalar el gráfico S1–S6, la proyección S7 y la explicación del método.

## 2:05–2:30 · Valor histórico atípico

En la misma sección, seleccionar **Marbella** y **Pepperoni**. Activar la comparación con el promedio simple si está disponible.

> “En S3 aparecen 150 kilos de pepperoni, muy lejos del resto del histórico. MAD lo identifica como atípico y, como quedan suficientes observaciones, lo excluye de la proyección robusta. El resultado limpio es cercano a 29 kilos. Con 4,7 kilos de inventario, las 5 cajas ordenadas son correctas. Usar el promedio simple habría generado una alerta falsa.”

## 2:30–2:50 · Sobrepedido perecedero

Regresar a **Alertas** y mostrar **Via Argentina · Albahaca fresca**.

> “Via Argentina pidió 20 paquetes de albahaca y la recomendación es 2. Sobran 18 paquetes. La aplicación resalta que es un producto perecedero, por lo que conviene revisar el exceso antes de enviar la orden.”

## 2:50–3:15 · Edición y recálculo

Abrir **Mesa de compra → Simulador** y modificar una cantidad.

> “La gerente puede cargar un nuevo CSV o editar las cantidades directamente. Al cambiar una orden, la aplicación vuelve a validar los datos y actualiza inmediatamente los diagnósticos y recomendaciones. También puede restablecer la orden original. Los valores inválidos no se convierten silenciosamente en cero.”

## 3:15–3:35 · Orden corregida por proveedor

Abrir **Mesa de compra → Orden corregida** y después **Paquetes por proveedor**.

> “La orden corregida incluye la cantidad original, la recomendada y el cambio sugerido. También se organiza por proveedor para descargar cada parte por separado. `aji_chombo`, que no existe en el catálogo, queda como dato pendiente y no entra en una orden porque no sería correcto inventar su proveedor, unidad o formato.”

## 3:35–3:55 · Calidad de datos y método

Abrir **Datos y método → Problemas que debes corregir** y **Consumos inusuales**.

> “Aquí separé los problemas de calidad, las alertas de compra y los consumos históricos inusuales. Nada se elimina o corrige automáticamente. En ‘Cómo calculamos’ se explica el método: MAD para valores extremos, tendencia lineal solo cuando existe evidencia fuerte y promedio limpio en los demás casos. La compra usa techo matemático porque no existe medio saco o media caja.”

## 3:55–4:15 · Asistente inteligente y uso de IA

Abrir **Asistente inteligente**, mostrar el selector entre **IA generativa** y **Asistente local** y ejecutar una pregunta sugerida.

> “El asistente permite consultar los resultados en español. Python sigue calculando todas las cifras; Gemini solamente interpreta un contexto limitado y responde con identificadores de evidencia. Si Gemini no está disponible, la aplicación utiliza el asistente local y el resto del dashboard sigue funcionando.”

> “Para construir el proyecto usé ChatGPT y Codex como apoyo para analizar el reto, organizar la arquitectura, generar pruebas, documentar y revisar el código. Después validé personalmente la interfaz y los casos esperados. Todo está explicado con transparencia en `AI_USAGE.md`.”

## 4:15–4:30 · Integración futura con Odoo y cierre

> “La aplicación todavía no está conectada a Odoo. En producción leería catálogo, inventario y movimientos mediante API, generaría órdenes de compra en borrador por proveedor y mantendría aprobación humana, permisos y auditoría. El resultado actual convierte cuatro CSV en una revisión semanal clara, explicable y accionable.”

## Antes de grabar

- Ejecutar `pytest` y confirmar que todas las pruebas pasan.
- Abrir la entrega con `streamlit run app_intelligent.py` o utilizar el enlace público.
- Mantener el margen de seguridad en **0%** para mostrar los resultados originales.
- Cerrar otras ventanas, notificaciones y cualquier archivo que pueda mostrar información personal.
- Practicar una vez para mantener el video entre tres y cinco minutos.
- Hablar con palabras propias; el guion es una guía, no un texto obligatorio.
- Evitar mencionar cifras que no estén visibles o verificadas en el dashboard.
- Comprobar en incógnito el enlace de la aplicación y el enlace del video.
- Confirmar que ninguno de los dos enlaces solicita iniciar sesión o pedir acceso.
