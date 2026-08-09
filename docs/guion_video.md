# Guion sugerido para el video (3–5 minutos)

Duración objetivo: **4 minutos y 45 segundos**. El recorrido sigue el mismo orden de la aplicación: introducción, margen de seguridad y luego cada pestaña de izquierda a derecha.

## 0:00–0:25 · Introducción

Abrir la aplicación desde **Vista ejecutiva** y mostrar el encabezado.

> “Hola. Este es el Asistente Inteligente de Compras de Barrio Pizza. Cada sucursal arma su orden semanal en sacos, cajas o paquetes, mientras que el consumo y el inventario se registran en unidades como kilos o litros. Revisarlo manualmente toma tiempo y puede esconder tanto faltantes como sobrepedidos. Esta herramienta convierte los cuatro CSV entregados en recomendaciones claras antes de aprobar una compra.”

Señalar el aviso de aprobación humana.

> “La aplicación ayuda a tomar la decisión, pero ninguna orden se aprueba automáticamente.”

## 0:25–0:45 · Margen de seguridad simulado

Mostrar el control lateral **Margen de seguridad simulado** y dejarlo en **0%**.

> “Este control permite simular un pequeño colchón por si la próxima semana se consume más de lo esperado. Con 10%, por ejemplo, la herramienta aumenta el consumo proyectado en 10% antes de calcular la necesidad. Esto no significa agregar siempre otro saco o caja: la recomendación solo cambia si se necesita otro formato completo. Para esta demostración lo dejo en 0%, porque así se aplica la fórmula original del reto.”

## 0:45–1:15 · Pestaña 1: Vista ejecutiva

Mostrar los indicadores y la cola de decisiones.

> “La primera pestaña es la Vista ejecutiva. Aquí se resumen las 88 combinaciones de sucursal e ingrediente. Puedo ver cuántas líneas están bien, los riesgos de quiebre, los sobrepedidos y los errores de datos.”

> “Debajo aparecen primero las decisiones de mayor prioridad. Cada tarjeta indica la sucursal, el ingrediente, lo que se pidió, lo recomendado, la diferencia y el proveedor. Las señales comparativas entre sucursales pueden coincidir con una alerta principal, pero no se cuentan como productos adicionales.”

Mencionar brevemente que los filtros laterales permiten limitar la revisión por sucursal o proveedor.

## 1:15–1:55 · Pestaña 2: Alertas

Abrir **Alertas → Alertas de compra**.

> “En Alertas puedo filtrar por severidad, diagnóstico, sucursal, proveedor y condición de perecedero. Brisas del Golf no incluyó mozzarella en su orden. La aplicación conserva el diagnóstico de producto omitido y recomienda agregar 18 cajas de 10 kilos.”

Mostrar también **Costa del Este · Harina 00** y **Via Argentina · Albahaca fresca**.

> “Costa del Este pidió 6 sacos de harina, pero necesita 13, así que faltan 7 sacos de 25 kilos. Via Argentina pidió 20 paquetes de albahaca y la recomendación es 2. Sobran 18 paquetes y, como es un producto perecedero, requiere una revisión prioritaria.”

Señalar el botón del reporte Excel y después abrir **Comportamiento inusual entre sucursales**.

> “Las alertas pueden descargarse en un Excel visual con resumen y decisiones prioritarias. La segunda sección compara una sucursal con sus pares. Como solo existen cuatro sucursales, se presenta como comportamiento inusual con confianza moderada, no como una anomalía confirmada.”

## 1:55–2:40 · Pestaña 3: Sucursales

Abrir **Sucursales → Qué debes cambiar** y seleccionar **Brisas del Golf**.

> “En Sucursales la revisión se concentra en una sede. Primero aparecen los productos que deben agregarse, aumentarse o reducirse. Para Brisas del Golf se debe agregar mozzarella y retirar 3 sacos de cebolla. También puedo mostrar los productos que no necesitan cambios y descargar un reporte completo de la sucursal.”

Abrir **Ver historial de un ingrediente**, seleccionar **Costa del Este** y **Harina 00**.

> “En el historial de Harina 00 se observa un crecimiento consistente. La tendencia supera los umbrales definidos, por eso se proyectan aproximadamente 330,27 kilos. Después de restar 30 kilos de inventario, se recomiendan 13 sacos de 25 kilos.”

Cambiar a **Marbella** y **Pepperoni**.

> “En pepperoni, los 150 kilos de S3 están muy lejos del resto. MAD detecta ese valor como atípico y lo excluye porque todavía quedan suficientes semanas válidas. La proyección limpia queda cerca de 29 kilos y las 5 cajas ordenadas son correctas. Así se evita una falsa alerta que sí produciría el promedio simple.”

## 2:40–3:20 · Pestaña 4: Mesa de compra

Abrir **Mesa de compra → Simulador** y modificar una cantidad.

> “La Mesa de compra permite cargar un nuevo CSV o editar la orden directamente. Cuando cambio una cantidad, la aplicación vuelve a validar y recalcula inmediatamente los diagnósticos. También puedo restablecer la orden original. Los datos inválidos o faltantes nunca se convierten silenciosamente en cero.”

Abrir **Orden corregida** y luego **Paquetes por proveedor**.

> “La Orden corregida muestra la cantidad original, la recomendada y la diferencia. En Paquetes por proveedor se genera una lista separada para cada proveedor, lista para descargar.”

> “El ingrediente `aji_chombo` aparece como dato pendiente porque no existe en el catálogo. Por seguridad, la herramienta no inventa su proveedor, unidad ni formato y no lo incluye en una orden corregida.”

## 3:20–3:55 · Pestaña 5: Datos y método

Abrir **Datos y método → Problemas que debes corregir** y después **Consumos inusuales**.

> “Esta pestaña separa los problemas de calidad de las alertas de compra y de los consumos históricos inusuales. Aquí aparecen el ingrediente desconocido, el producto omitido y el valor atípico de pepperoni, explicando por qué importa cada caso. Ningún registro se borra o corrige automáticamente.”

Abrir **Consumo esperado** y **Cómo calculamos**.

> “El método busca ser fácil de defender. Primero usa MAD para detectar extremos. Si existe una tendencia fuerte, usa regresión lineal; si no, utiliza el promedio de los datos limpios. Luego resta el inventario y aplica techo matemático para comprar formatos completos. El sobrante dentro del último formato es redondeo normal, no sobrepedido.”

## 3:55–4:25 · Pestaña 6: Asistente inteligente

Abrir **Asistente inteligente**, mostrar el selector y ejecutar una pregunta sugerida.

> “La última pestaña permite hacer preguntas en español. Puedo elegir entre IA generativa y Asistente local. Python calcula todas las proyecciones, necesidades y recomendaciones; Gemini solamente interpreta un contexto limitado y responde utilizando identificadores de evidencia.”

> “Si Gemini no está configurado, alcanza su límite o falla, se activa el respaldo local y el resto de la aplicación continúa funcionando.”

> “Para desarrollar el proyecto usé ChatGPT y Codex como apoyo para analizar el reto, organizar la arquitectura, generar pruebas, documentar y revisar el código. Después validé personalmente la interfaz y los casos esperados. El proceso está documentado en `AI_USAGE.md`.”

## 4:25–4:45 · Odoo y cierre

> “La aplicación todavía no está conectada a Odoo. En producción leería el catálogo, inventario y movimientos mediante API, generaría órdenes de compra en borrador por proveedor y mantendría aprobación humana, permisos y auditoría.”

> “El resultado convierte cuatro CSV en una revisión semanal rápida, explicable y accionable para la gerente de compras. Gracias.”

## Antes de grabar

- Ejecutar `pytest` y confirmar que todas las pruebas pasan.
- Abrir la entrega con `streamlit run app_intelligent.py` o utilizar el enlace público.
- Mantener el margen de seguridad en **0%** durante la demostración.
- Cerrar otras ventanas, notificaciones y archivos con información personal.
- Practicar una vez para mantener el video entre tres y cinco minutos.
- Hablar con palabras propias; este guion es una guía y no debe sonar memorizado.
- Evitar mencionar cifras que no estén visibles o verificadas en el dashboard.
- Comprobar en incógnito tanto el enlace de la aplicación como el enlace del video.
- Confirmar que ninguno de los dos enlaces solicita iniciar sesión o pedir acceso.
