"""Barrio Pizza | Asistente Inteligente de Compras."""

from __future__ import annotations

from datetime import date
from html import escape
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.alerts import (
    build_anomaly_alerts,
    build_purchase_alerts,
    build_quality_alerts,
    format_number,
)
from src.benchmarking import (
    detect_cross_branch_order_anomalies,
    scope_cross_branch_behaviors,
    summarize_attention_overlap,
)
from src.data_loader import DataBundle, load_data, read_order_upload
from src.forecasting import forecast_all, week_number
from src.purchasing import build_purchase_review, corrected_order, unknown_order_lines
from src.ui_helpers import (
    SEVERITY_ICONS,
    answer_local_question,
    dataframe_to_csv_bytes,
    filter_rows,
    friendly_review_table,
    inject_app_css,
)
from src.validation import validate_data


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "datos"
PLOT_COLORS = ["#C95F3D", "#E5A23B", "#6D8A61", "#5F7595", "#8B6F62"]


st.set_page_config(
    page_title="Barrio Pizza | Asistente Inteligente de Compras",
    page_icon="🍕",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_app_css(st)


@st.cache_data(show_spinner=False)
def load_default_data() -> DataBundle:
    """Carga las fuentes base una vez por sesión y por versión de archivo."""

    return load_data(DATA_DIR)


def run_pipeline(bundle: DataBundle, order: pd.DataFrame, safety_margin: float) -> dict[str, object]:
    """Ejecuta validación, proyección, compra y alertas sin lógica visual."""

    validated = validate_data(bundle.catalogo, bundle.historico, bundle.inventario, order)
    forecasts, outliers = forecast_all(validated.historico, validated.combinaciones)
    review = build_purchase_review(validated, forecasts, safety_margin=safety_margin)
    purchase_alerts = build_purchase_alerts(review)
    cross_branch_anomalies = detect_cross_branch_order_anomalies(
        review,
        catalog_ingredient_ids=validated.catalogo["ingrediente_id"],
    )
    quality = build_quality_alerts(validated.incidencias)
    anomalies = build_anomaly_alerts(outliers, validated.catalogo)
    return {
        "validated": validated,
        "forecasts": forecasts,
        "outliers": outliers,
        "review": review,
        "purchase_alerts": purchase_alerts,
        "cross_branch_anomalies": cross_branch_anomalies,
        "quality": quality,
        "anomalies": anomalies,
        "unknown_order": unknown_order_lines(validated),
        "corrected": corrected_order(review),
    }


def apply_review_filters(review: pd.DataFrame, filters: dict[str, list[str]]) -> pd.DataFrame:
    """Filtra las líneas revisadas usando los mismos controles del dashboard."""

    result = review.copy()
    mappings = [
        ("sucursal", filters["sucursales"]),
        ("proveedor", filters["proveedores"]),
        ("nombre", filters["ingredientes"]),
        ("metodo_proyeccion", filters["metodos"]),
    ]
    for column, selected in mappings:
        if selected:
            result = result[result[column].isin(selected)]
    if filters["perecedero"]:
        labels = result["es_perecedero_bool"].map({True: "Sí", False: "No"})
        result = result[labels.isin(filters["perecedero"])]
    return result


def format_display_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Evita presentar cantidades de formatos con sufijo decimal."""

    result = frame.copy()
    for column in result.columns:
        if "Formato" in str(column) or "formatos" in str(column):
            numeric = pd.to_numeric(result[column], errors="coerce")
            if numeric.notna().any():
                result[column] = numeric.round().astype("Int64")
    return result


def show_alert_cards(alerts: pd.DataFrame, limit: int = 8) -> None:
    if alerts.empty:
        st.success("✅ No hay alertas de compra para la selección actual.")
        return
    for row in alerts.head(limit).itertuples():
        icon = SEVERITY_ICONS.get(row.severidad, "ℹ️")
        st.markdown(
            f"""
            <div class="bp-alert">
              <strong>{icon} {escape(str(row.severidad))} · {escape(str(row.tipo_alerta))}</strong><br>
              {escape(str(row.mensaje))}<br>
              <small><b>Acción:</b> {escape(str(row.accion_recomendada))} ·
              <b>Proveedor:</b> {escape(str(row.proveedor))}</small>
            </div>
            """,
            unsafe_allow_html=True,
        )


def kpi_block(
    review: pd.DataFrame,
    alerts: pd.DataFrame,
    quality: pd.DataFrame,
    cross_branch_anomalies: pd.DataFrame,
) -> None:
    correct = int(review["estado"].isin(["CORRECTO", "SIN NECESIDAD"]).sum())
    risks = int((alerts["tipo_alerta"] == "FALTANTE").sum()) if not alerts.empty else 0
    omitted = int((alerts["tipo_alerta"] == "OMITIDO").sum()) if not alerts.empty else 0
    over = int((alerts["tipo_alerta"] == "SOBREPEDIDO").sum()) if not alerts.empty else 0
    errors = int((quality["nivel"] == "Error").sum()) if not quality.empty else 0
    affected = set(alerts["sucursal"].dropna()) if not alerts.empty else set()
    if not quality.empty:
        affected.update(quality.loc[quality["nivel"] == "Error", "sucursal"].dropna())
    if not cross_branch_anomalies.empty:
        affected.update(cross_branch_anomalies["sucursal"].dropna())
    overlap = summarize_attention_overlap(alerts, cross_branch_anomalies)

    first = st.columns(4)
    first[0].metric("📋 Líneas revisadas", len(review))
    first[1].metric("✅ Líneas correctas", correct)
    first[2].metric("⚠️ Riesgos de quiebre", risks)
    first[3].metric("⛔ Productos omitidos", omitted)
    second = st.columns(4)
    second[0].metric("📦 Sobrepedidos", over)
    second[1].metric("🧩 Errores de datos", errors)
    second[2].metric("🏪 Sucursales afectadas", len(affected))
    second[3].metric("📌 Líneas con atención", overlap["lineas_unicas"])
    st.markdown(
        f"""
        <div class="bp-note"><b>Las categorías pueden superponerse:</b> faltante,
        sobrepedido y producto omitido son diagnósticos principales de la línea; el
        comportamiento inusual es contexto comparativo. Hay
        {overlap['comportamientos_inusuales']} señales contextuales y
        {overlap['superposicion']} coinciden con una alerta principal.
        El total de <b>{overlap['lineas_unicas']} líneas con atención</b> usa la combinación
        sucursal–ingrediente y no cuenta esas coincidencias como productos adicionales.</div>
        """,
        unsafe_allow_html=True,
    )


def empty_chart(message: str) -> None:
    st.info(f"ℹ️ {message}")


def render_executive(
    review: pd.DataFrame,
    alerts: pd.DataFrame,
    quality: pd.DataFrame,
    cross_branch_anomalies: pd.DataFrame,
) -> None:
    st.subheader("Resumen ejecutivo")
    kpi_block(review, alerts, quality, cross_branch_anomalies)
    st.markdown("#### Alertas prioritarias")
    show_alert_cards(alerts, limit=5)

    left, right = st.columns(2)
    with left:
        st.markdown("#### Alertas por sucursal")
        if alerts.empty:
            empty_chart("No hay alertas para graficar.")
        else:
            counts = alerts.groupby(["sucursal", "severidad"], as_index=False).size()
            figure = px.bar(
                counts,
                x="sucursal",
                y="size",
                color="severidad",
                text="size",
                labels={"sucursal": "Sucursal", "size": "Alertas", "severidad": "Severidad"},
                color_discrete_map={
                    "Crítica": "#B33A3A",
                    "Alta": "#E07032",
                    "Media": "#E5A23B",
                    "Baja": "#5F7595",
                },
            )
            figure.update_traces(textposition="outside")
            figure.update_layout(height=370, margin=dict(t=20, b=20))
            st.plotly_chart(figure, width="stretch")
    with right:
        st.markdown("#### Alertas por tipo")
        if alerts.empty:
            empty_chart("No hay alertas para graficar.")
        else:
            counts = alerts["tipo_alerta"].value_counts().rename_axis("tipo").reset_index(name="cantidad")
            figure = px.pie(
                counts,
                names="tipo",
                values="cantidad",
                hole=0.55,
                color_discrete_sequence=PLOT_COLORS,
            )
            figure.update_traces(textinfo="label+value")
            figure.update_layout(height=370, margin=dict(t=20, b=20), showlegend=True)
            st.plotly_chart(figure, width="stretch")

    correct = int(review["estado"].isin(["CORRECTO", "SIN NECESIDAD"]).sum())
    percentage = 100.0 * correct / len(review) if len(review) else 0.0
    st.markdown("#### Líneas sin ajuste requerido")
    gauge = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=percentage,
            number={"suffix": "%", "valueformat": ".1f"},
            title={"text": "Porcentaje correcto"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#6D8A61"},
                "steps": [
                    {"range": [0, 60], "color": "#F5D6CF"},
                    {"range": [60, 85], "color": "#FBE8BF"},
                    {"range": [85, 100], "color": "#DDE8D9"},
                ],
            },
        )
    )
    gauge.update_layout(height=260, margin=dict(t=55, b=20))
    st.plotly_chart(gauge, width="stretch")


def render_alerts(alerts: pd.DataFrame) -> None:
    st.subheader("Alertas accionables")
    st.caption(
        "Usa estos controles para afinar esta pestaña. Al iniciar se muestran todas las alertas "
        "que cumplen los filtros generales de la barra lateral."
    )

    def options_for(column: str, preferred_order: list[str] | None = None) -> list[str]:
        values = set(alerts[column].dropna().astype(str)) if column in alerts else set()
        if preferred_order is not None:
            ordered = [value for value in preferred_order if value in values]
            return [*ordered, *sorted(values.difference(ordered))]
        return sorted(values)

    severity_options = options_for("severidad", ["Crítica", "Alta", "Media", "Baja"])
    type_options = options_for("tipo_alerta", ["OMITIDO", "FALTANTE", "SOBREPEDIDO"])
    branch_options = options_for("sucursal")
    supplier_options = options_for("proveedor")
    ingredient_options = options_for("ingrediente")
    perishability_options = options_for("es_perecedero", ["Sí", "No"])

    with st.container(border=True):
        first_row = st.columns(3)
        selected_severity = first_row[0].selectbox(
            "Severidad",
            ["Todas", *severity_options],
            key="actionable_severity_filter",
        )
        selected_type = first_row[1].selectbox(
            "Tipo de alerta",
            ["Todos", *type_options],
            key="actionable_type_filter",
        )
        selected_branch = first_row[2].selectbox(
            "Sucursal",
            ["Todas", *branch_options],
            key="actionable_branch_filter",
        )

        second_row = st.columns(3)
        selected_supplier = second_row[0].selectbox(
            "Proveedor",
            ["Todos", *supplier_options],
            key="actionable_supplier_filter",
        )
        selected_ingredient = second_row[1].selectbox(
            "Ingrediente",
            ["Todos", *ingredient_options],
            key="actionable_ingredient_filter",
        )
        selected_perishability = second_row[2].selectbox(
            "Perecedero",
            ["Todos", *perishability_options],
            key="actionable_perishability_filter",
        )

    visible = alerts.copy()
    selections = [
        ("severidad", selected_severity, "Todas"),
        ("tipo_alerta", selected_type, "Todos"),
        ("sucursal", selected_branch, "Todas"),
        ("proveedor", selected_supplier, "Todos"),
        ("ingrediente", selected_ingredient, "Todos"),
        ("es_perecedero", selected_perishability, "Todos"),
    ]
    for column, selected, all_label in selections:
        if selected != all_label:
            visible = visible[visible[column].astype(str) == selected]

    st.caption(f"Mostrando {len(visible)} de {len(alerts)} alertas en esta selección.")
    show_alert_cards(visible, limit=20)
    st.markdown("#### Tabla de alertas")
    table_columns = [
        "severidad",
        "tipo_alerta",
        "sucursal",
        "ingrediente",
        "proveedor",
        "es_perecedero",
        "formato_compra",
        "formatos_ordenados",
        "cantidad_ordenada_base",
        "formatos_recomendados",
        "cantidad_recomendada_base",
        "diferencia_formatos",
        "unidad_base",
        "razon",
        "accion_recomendada",
    ]
    table = visible[table_columns].copy() if not visible.empty else pd.DataFrame(columns=table_columns)
    st.dataframe(format_display_frame(table), width="stretch", hide_index=True)
    st.download_button(
        "⬇️ Descargar alertas filtradas",
        dataframe_to_csv_bytes(table),
        file_name="alertas_compra_filtradas.csv",
        mime="text/csv",
        width="stretch",
    )


def show_cross_branch_cards(anomalies: pd.DataFrame, limit: int = 12) -> None:
    """Presenta benchmarking accionable sin depender únicamente del color."""

    if anomalies.empty:
        st.success(
            "✅ No se detectó comportamiento inusual entre sucursales para la selección."
        )
        return
    for row in anomalies.head(limit).itertuples():
        icon = SEVERITY_ICONS.get(row.severidad, "ℹ️")
        headline = (
            f"{icon} {row.severidad} · PRODUCTO OMITIDO"
            if row.diagnostico_principal == "Producto omitido"
            else f"{icon} {row.severidad} · COMPORTAMIENTO INUSUAL · {row.direccion}"
        )
        difference = int(row.diferencia_formatos)
        st.markdown(
            f"""
            <div class="bp-alert">
              <strong>{escape(headline)}</strong><br>
              {escape(str(row.mensaje))}<br>
              <small><b>Diagnóstico principal:</b> {escape(str(row.diagnostico_principal))} ·
              <b>Sucursales comparables:</b> {int(row.cantidad_pares)} ·
              <b>Ratio de la sucursal:</b> {escape(str(row.ratio_sucursal))} ·
              <b>Mediana de los pares:</b> {escape(str(row.ratio_mediana_pares))} ·
              <b>Diferencia:</b> {difference:+d} formatos<br>
              <b>Método:</b> {escape(str(row.metodo_deteccion))} ·
              <b>Confianza:</b> {escape(str(row.nivel_confianza))}<br>
              <b>Acción:</b> {escape(str(row.accion_recomendada))}</small>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_cross_branch_anomalies(
    review: pd.DataFrame,
    anomalies: pd.DataFrame,
) -> None:
    """Muestra las órdenes inusuales después de normalizar por recomendación."""

    st.subheader("Comportamiento inusual entre sucursales")
    st.markdown(
        """
        <div class="bp-note"><b>Comparación justa:</b> no se comparan cantidades absolutas,
        porque una sucursal con mayor demanda puede comprar legítimamente más. Para el mismo
        ingrediente se calcula <code>formatos ordenados / formatos recomendados</code> y cada
        sucursal se contrasta contra la mediana de las demás. Se requieren al menos dos pares
        y una diferencia mínima de un formato completo. Con solo cuatro sucursales, estas
        señales son contexto para revisión humana y no anomalías confirmadas.</div>
        """,
        unsafe_allow_html=True,
    )

    high = int((anomalies["direccion"] == "MUY POR ENCIMA").sum()) if not anomalies.empty else 0
    low = int((anomalies["direccion"] == "MUY POR DEBAJO").sum()) if not anomalies.empty else 0
    branches = anomalies["sucursal"].nunique() if not anomalies.empty else 0
    ingredients = anomalies["ingrediente"].nunique() if not anomalies.empty else 0
    metrics = st.columns(4)
    metrics[0].metric("⬆️ Muy por encima", high)
    metrics[1].metric("⬇️ Muy por debajo", low)
    metrics[2].metric("🏪 Sucursales señaladas", branches)
    metrics[3].metric("🧺 Ingredientes señalados", ingredients)

    st.markdown("#### Casos que requieren explicación")
    show_cross_branch_cards(anomalies)

    comparable = review[
        review["formatos_ordenados"].notna()
        & review["formatos_recomendados"].notna()
        & (review["estado"] != "DATO INCOMPLETO")
    ].copy()
    comparable["clasificacion_benchmark"] = "Sin señal inusual"
    if not comparable.empty and not anomalies.empty:
        markers = anomalies[["sucursal", "ingrediente_id", "direccion"]]
        comparable = comparable.drop(columns="clasificacion_benchmark").merge(
            markers,
            on=["sucursal", "ingrediente_id"],
            how="left",
            validate="one_to_one",
        )
        comparable["clasificacion_benchmark"] = comparable["direccion"].map(
            {
                "MUY POR ENCIMA": "Comportamiento inusual · por encima",
                "MUY POR DEBAJO": "Comportamiento inusual · por debajo",
            }
        ).fillna("Sin señal inusual")
    comparable["Perecedero"] = comparable["es_perecedero_bool"].map(
        {True: "Sí", False: "No"}
    )

    left, right = st.columns([3, 2])
    with left:
        st.markdown("#### Orden frente a recomendación")
        if comparable.empty:
            empty_chart("No existen líneas calculables para comparar.")
        else:
            figure = px.scatter(
                comparable,
                x="formatos_recomendados",
                y="formatos_ordenados",
                color="clasificacion_benchmark",
                symbol="Perecedero",
                hover_name="nombre",
                hover_data={
                    "sucursal": True,
                    "proveedor": True,
                    "diferencia_formatos": ":.0f",
                    "formatos_recomendados": ":.0f",
                    "formatos_ordenados": ":.0f",
                    "clasificacion_benchmark": False,
                },
                labels={
                    "formatos_recomendados": "Formatos recomendados",
                    "formatos_ordenados": "Formatos ordenados",
                    "clasificacion_benchmark": "Resultado",
                },
                color_discrete_map={
                    "Sin señal inusual": "#6D8A61",
                    "Comportamiento inusual · por encima": "#C95F3D",
                    "Comportamiento inusual · por debajo": "#B33A3A",
                },
            )
            maximum = max(
                float(comparable["formatos_recomendados"].max()),
                float(comparable["formatos_ordenados"].max()),
                1.0,
            )
            figure.add_trace(
                go.Scatter(
                    x=[0, maximum * 1.05],
                    y=[0, maximum * 1.05],
                    mode="lines",
                    name="Orden = recomendación",
                    line={"color": "#2E2925", "dash": "dot", "width": 2},
                    hoverinfo="skip",
                )
            )
            figure.update_layout(
                height=430,
                margin=dict(t=20, b=30),
                legend_title_text="Clasificación",
            )
            st.plotly_chart(figure, width="stretch")
    with right:
        st.markdown("#### Señales por sucursal")
        if anomalies.empty:
            empty_chart("No hay comportamientos inusuales para graficar.")
        else:
            counts = (
                anomalies.groupby(["sucursal", "direccion"], as_index=False)
                .size()
                .rename(columns={"size": "cantidad"})
            )
            figure = px.bar(
                counts,
                x="cantidad",
                y="sucursal",
                color="direccion",
                text="cantidad",
                orientation="h",
                labels={
                    "cantidad": "Comportamientos inusuales",
                    "sucursal": "Sucursal",
                    "direccion": "Dirección",
                },
                color_discrete_map={
                    "MUY POR ENCIMA": "#C95F3D",
                    "MUY POR DEBAJO": "#B33A3A",
                },
            )
            figure.update_layout(height=430, margin=dict(t=20, b=30))
            st.plotly_chart(figure, width="stretch")

    st.markdown("#### Evidencia del benchmarking")
    columns = [
        "severidad",
        "diagnostico_principal",
        "direccion",
        "sucursal",
        "ingrediente",
        "proveedor",
        "es_perecedero",
        "formato_compra",
        "formatos_ordenados",
        "formatos_recomendados",
        "diferencia_formatos",
        "ratio_sucursal",
        "ratio_mediana_pares",
        "cantidad_pares",
        "mad_factor_pares",
        "modified_z_score",
        "metodo_deteccion",
        "nivel_confianza",
        "razon",
        "accion_recomendada",
    ]
    table = anomalies[columns].copy() if not anomalies.empty else pd.DataFrame(columns=columns)
    st.dataframe(format_display_frame(table), width="stretch", hide_index=True)
    st.download_button(
        "⬇️ Descargar comportamiento inusual entre sucursales",
        dataframe_to_csv_bytes(table),
        file_name="comportamiento_inusual_entre_sucursales.csv",
        mime="text/csv",
        width="stretch",
    )
    st.caption(
        "Limitación: los CSV no contienen clientes, ventas ni volumen de transacciones. "
        "La normalización usa la recomendación calculada como referencia de escala, no pedidos por cliente."
    )


def render_branch_detail(
    validated: object,
    review: pd.DataFrame,
    forecasts: pd.DataFrame,
    outliers: pd.DataFrame,
) -> None:
    st.subheader("Detalle por sucursal")
    if not validated.sucursales:
        st.warning("No hay sucursales válidas en el histórico.")
        return
    branch = st.selectbox("Sucursal", validated.sucursales, key="detail_branch")
    branch_review = review[review["sucursal"] == branch]
    alerts_count = int(branch_review["estado"].isin(["OMITIDO", "FALTANTE", "SOBREPEDIDO"]).sum())
    cols = st.columns(4)
    cols[0].metric("Ingredientes revisados", len(branch_review))
    cols[1].metric("Alertas de compra", alerts_count)
    cols[2].metric("Líneas correctas", int(branch_review["estado"].isin(["CORRECTO", "SIN NECESIDAD"]).sum()))
    cols[3].metric("Datos incompletos", int((branch_review["estado"] == "DATO INCOMPLETO").sum()))
    st.dataframe(
        format_display_frame(friendly_review_table(branch_review)),
        width="stretch",
        hide_index=True,
    )

    if branch_review.empty:
        return
    ingredient_names = branch_review.sort_values("nombre")["nombre"].dropna().tolist()
    ingredient_name = st.selectbox("Ingrediente para analizar", ingredient_names)
    selected = branch_review[branch_review["nombre"] == ingredient_name].iloc[0]
    ingredient_id = selected["ingrediente_id"]
    history = validated.historico[
        (validated.historico["sucursal"] == branch)
        & (validated.historico["ingrediente_id"] == ingredient_id)
    ].copy()
    history["semana_numero"] = history["semana"].map(week_number)
    history["consumo_numerico"] = pd.to_numeric(history["consumo_unidad_base"], errors="coerce")
    history = history.sort_values("semana_numero")
    selected_forecast = forecasts[
        (forecasts["sucursal"] == branch) & (forecasts["ingrediente_id"] == ingredient_id)
    ].iloc[0]

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=history["semana"],
            y=history["consumo_numerico"],
            mode="lines+markers+text",
            name="Consumo observado",
            line={"color": "#5F7595", "width": 3},
            marker={"size": 9},
            hovertemplate="%{x}: %{y}<extra></extra>",
        )
    )
    selected_outliers = outliers[
        (outliers["sucursal"] == branch) & (outliers["ingrediente_id"] == ingredient_id)
    ]
    if not selected_outliers.empty:
        figure.add_trace(
            go.Scatter(
                x=selected_outliers["semana"],
                y=selected_outliers["consumo_unidad_base"],
                mode="markers+text",
                text=["Atípico"] * len(selected_outliers),
                textposition="top center",
                name="Valor atípico",
                marker={"size": 15, "symbol": "x", "color": "#B33A3A"},
            )
        )
    if pd.notna(selected_forecast["consumo_proyectado"]):
        next_number = int(selected_forecast["semana_proyectada_numero"])
        figure.add_trace(
            go.Scatter(
                x=[f"S{next_number}"],
                y=[selected_forecast["consumo_proyectado"]],
                mode="markers+text",
                text=["Proyección"],
                textposition="top center",
                name="Proyección robusta",
                marker={"size": 15, "symbol": "diamond", "color": "#C95F3D"},
            )
        )
    if st.checkbox("Comparar con el promedio simple de seis semanas", value=False):
        simple = selected_forecast["promedio_simple_6s"]
        if pd.notna(simple):
            figure.add_hline(
                y=float(simple),
                line_dash="dot",
                line_color="#E5A23B",
                annotation_text=f"Promedio simple: {format_number(simple)}",
            )
    figure.update_layout(
        title=f"Histórico y proyección · {ingredient_name}",
        xaxis_title="Semana",
        yaxis_title=f"Consumo ({selected['unidad_base']})",
        height=430,
        margin=dict(t=60, b=30),
        hovermode="x unified",
    )
    st.plotly_chart(figure, width="stretch")

    metric_cols = st.columns(5)
    metric_cols[0].metric("Inventario", f"{format_number(selected['inventario_actual'])} {selected['unidad_base']}")
    metric_cols[1].metric("Proyección", f"{format_number(selected['consumo_proyectado'])} {selected['unidad_base']}")
    metric_cols[2].metric("Necesidad", f"{format_number(selected['necesidad_base'])} {selected['unidad_base']}")
    metric_cols[3].metric("Orden", f"{format_number(selected['formatos_ordenados'])} formatos")
    metric_cols[4].metric("Recomendación", f"{format_number(selected['formatos_recomendados'])} formatos")
    st.markdown(
        f"<div class='bp-note'><b>Método:</b> {escape(str(selected_forecast['metodo_proyeccion']))} · "
        f"<b>Confianza:</b> {escape(str(selected_forecast['nivel_confianza']))}<br>"
        f"{escape(str(selected_forecast['explicacion_metodo']))}</div>",
        unsafe_allow_html=True,
    )


def render_simulator(bundle: DataBundle, pipeline: dict[str, object]) -> None:
    st.subheader("Simulador de orden")
    st.caption("Carga o edita una orden. Cada cambio vuelve a ejecutar las mismas validaciones y fórmulas.")
    uploaded = st.file_uploader("Cargar un nuevo orden_compra_semana.csv", type=["csv"])
    if uploaded is not None:
        try:
            uploaded_order = read_order_upload(BytesIO(uploaded.getvalue()))
            st.markdown("##### Vista previa y validación")
            st.dataframe(uploaded_order.head(25), width="stretch", hide_index=True)
            preview_validation = validate_data(
                bundle.catalogo, bundle.historico, bundle.inventario, uploaded_order
            )
            schema_errors = preview_validation.incidencias[
                preview_validation.incidencias["codigo"] == "COLUMNA_AUSENTE"
            ]
            if not schema_errors.empty:
                st.error("El archivo no puede usarse porque faltan columnas obligatorias.")
                st.dataframe(schema_errors, width="stretch", hide_index=True)
            else:
                count_errors = int((preview_validation.incidencias["nivel"] == "Error").sum())
                if count_errors:
                    st.warning(
                        f"El archivo contiene {count_errors} incidencias de error. Se conservarán y las líneas afectadas no se calcularán."
                    )
                else:
                    st.success("El esquema es válido y no contiene errores bloqueantes.")
                if st.button("Usar esta orden en el simulador", type="primary"):
                    current = uploaded_order.copy()
                    numeric_quantity = pd.to_numeric(
                        current["cantidad_formatos"], errors="coerce"
                    )
                    current["cantidad_formatos"] = numeric_quantity.where(
                        numeric_quantity.notna(), current["cantidad_formatos"]
                    )
                    st.session_state.working_order = current
                    st.session_state.editor_version += 1
                    st.rerun()
        except Exception as exc:
            st.error(f"No fue posible leer el archivo: {exc}")

    controls = st.columns([1, 1, 3])
    if controls[0].button("↩️ Restablecer original", width="stretch"):
        original = bundle.orden.copy()
        original["cantidad_formatos"] = pd.to_numeric(original["cantidad_formatos"], errors="coerce")
        st.session_state.working_order = original
        st.session_state.editor_version += 1
        st.rerun()
    controls[1].metric("Líneas actuales", len(st.session_state.working_order))
    controls[2].caption("Puedes agregar o eliminar filas. Los ingredientes desconocidos permanecen visibles como errores de datos.")

    editor_key = f"order_editor_{st.session_state.editor_version}"
    quantity_numeric = pd.to_numeric(
        st.session_state.working_order["cantidad_formatos"], errors="coerce"
    )
    quantity_has_invalid = bool(
        st.session_state.working_order["cantidad_formatos"].notna().any()
        and quantity_numeric.isna().any()
    )
    quantity_config = (
        st.column_config.TextColumn(
            "Cantidad de formatos",
            help="Corrige el valor no numérico; luego se habilitará la edición numérica.",
            required=True,
        )
        if quantity_has_invalid
        else st.column_config.NumberColumn(
            "Cantidad de formatos", min_value=0.0, step=1.0, required=True
        )
    )
    edited = st.data_editor(
        st.session_state.working_order,
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        key=editor_key,
        column_config={
            "sucursal": st.column_config.TextColumn("Sucursal", required=True),
            "ingrediente_id": st.column_config.TextColumn("Ingrediente ID", required=True),
            "cantidad_formatos": quantity_config,
        },
    )
    normalized_current = st.session_state.working_order.reset_index(drop=True)
    normalized_edited = edited.reset_index(drop=True)
    if not normalized_edited.equals(normalized_current):
        st.session_state.working_order = normalized_edited
        st.rerun()

    current_issues = pipeline["quality"]
    errors = current_issues[current_issues["nivel"] == "Error"]
    if errors.empty:
        st.success("✅ La orden actual no agrega errores de calidad bloqueantes.")
    else:
        st.warning(f"⚠️ La revisión actual conserva {len(errors)} errores de datos; consulta la pestaña Calidad de datos.")


def render_corrected(pipeline: dict[str, object]) -> None:
    st.subheader("Orden corregida")
    st.caption("Incluye todo el catálogo conocido. Las cantidades no calculables quedan vacías para revisión humana.")
    corrected = pipeline["corrected"].copy()
    for column in [
        "cantidad_formatos_original",
        "cantidad_formatos_corregida",
        "diferencia_formatos_corregir",
    ]:
        corrected[column] = pd.to_numeric(corrected[column], errors="coerce").round().astype("Int64")
    st.download_button(
        "⬇️ Descargar orden corregida completa",
        dataframe_to_csv_bytes(corrected),
        file_name="orden_corregida_completa.csv",
        mime="text/csv",
        width="stretch",
    )
    st.dataframe(corrected, width="stretch", hide_index=True)

    st.markdown("#### Órdenes por proveedor")
    suppliers = corrected["proveedor"].dropna().sort_values().unique().tolist()
    for supplier in suppliers:
        supplier_order = corrected[corrected["proveedor"] == supplier]
        with st.expander(f"📦 {supplier} · {len(supplier_order)} líneas"):
            st.dataframe(supplier_order, width="stretch", hide_index=True)
            safe_name = "".join(char.lower() if char.isalnum() else "_" for char in supplier).strip("_")
            st.download_button(
                f"Descargar CSV de {supplier}",
                dataframe_to_csv_bytes(supplier_order),
                file_name=f"orden_{safe_name}.csv",
                mime="text/csv",
                key=f"download_{safe_name}",
            )

    st.markdown("#### Datos pendientes por corregir")
    unknown = pipeline["unknown_order"]
    if unknown.empty:
        st.success("No hay ingredientes desconocidos pendientes.")
    else:
        st.error(
            "Estas líneas no se incluyen en ninguna orden a proveedor porque no existe metadata confiable en el catálogo."
        )
        st.dataframe(format_display_frame(unknown), width="stretch", hide_index=True)


def render_quality(pipeline: dict[str, object]) -> None:
    st.subheader("Calidad de datos")
    issues = pipeline["quality"]
    anomalies = pipeline["anomalies"]
    errors = issues[issues["nivel"] == "Error"] if not issues.empty else issues
    warnings = issues[issues["nivel"] == "Advertencia"] if not issues.empty else issues
    cols = st.columns(4)
    cols[0].metric("❌ Errores", len(errors))
    cols[1].metric("⚠️ Advertencias", len(warnings))
    cols[2].metric("❓ Productos desconocidos", int((issues["codigo"] == "INGREDIENTE_DESCONOCIDO").sum()) if not issues.empty else 0)
    cols[3].metric("📈 Atípicos históricos", len(anomalies))

    st.markdown(
        "<div class='bp-note'><b>Separación deliberada:</b> una incidencia de calidad indica que el dato necesita corrección; "
        "una alerta de compra compara orden y recomendación; una anomalía histórica informa un valor extremo conservando el original.</div>",
        unsafe_allow_html=True,
    )
    with st.expander("❌ Errores", expanded=True):
        if errors.empty:
            st.success("No se detectaron errores.")
        else:
            st.dataframe(errors, width="stretch", hide_index=True)
    with st.expander("⚠️ Advertencias y productos omitidos", expanded=True):
        if warnings.empty:
            st.success("No se detectaron advertencias.")
        else:
            st.dataframe(warnings, width="stretch", hide_index=True)
    with st.expander("📉 Históricos incompletos"):
        incomplete = issues[issues["codigo"].isin(["HISTORICO_INCOMPLETO", "HISTORICO_FALTANTE"])]
        if incomplete.empty:
            st.success("Las combinaciones tienen el histórico esperado.")
        else:
            st.dataframe(incomplete, width="stretch", hide_index=True)
    with st.expander("🔎 Valores atípicos detectados", expanded=True):
        if anomalies.empty:
            st.info("No se detectaron valores atípicos con MAD.")
        else:
            columns = [
                "sucursal",
                "nombre",
                "semana",
                "consumo_unidad_base",
                "unidad_base",
                "mediana",
                "mad",
                "modified_z_score",
                "excluido_proyeccion",
                "detalle",
            ]
            st.dataframe(anomalies[columns], width="stretch", hide_index=True)


def render_methodology(margin: float) -> None:
    st.subheader("Metodología")
    st.markdown(
        """
        #### Fórmula de compra

        1. `necesidad_base = max(consumo_proyectado - inventario_actual, 0)`
        2. `formatos_recomendados = ceil(necesidad_base / unidad_base_por_formato)`
        3. `cantidad_ordenada_base = cantidad_formatos_ordenados × unidad_base_por_formato`
        4. `diferencia_formatos = cantidad_formatos_ordenados - formatos_recomendados`

        El excedente inevitable dentro del último saco, caja, lata, paquete o unidad es **redondeo normal**. Solo se marca
        sobrepedido si la orden supera la recomendación por al menos un formato entero.

        #### Proyección transparente

        Las semanas se ordenan por su número. Se calcula mediana y MAD; con MAD mayor que cero, un modified z-score
        absoluto superior a 3.5 marca un atípico. Solo se excluye si quedan al menos cuatro observaciones. Luego se ajusta
        una regresión lineal simple. La tendencia se usa únicamente con `R² ≥ 0.80` y cambio estimado de al menos 15% del
        promedio limpio; de lo contrario se usa el promedio robusto. Las proyecciones nunca son negativas.

        Con una o dos semanas válidas se permite una referencia básica con confianza baja. Sin histórico no se inventa
        una proyección. Si falta inventario, la línea queda como **DATO INCOMPLETO** y no se supone stock cero.

        #### Comportamiento inusual entre sucursales

        Para comparar sucursales de tamaños distintos se usa el factor
        `formatos_ordenados / formatos_recomendados` por ingrediente. Cada sucursal se excluye de su propio grupo de
        comparación y se contrasta contra la mediana y MAD de al menos dos pares. Con `MAD > 0` se utiliza modified
        z-score absoluto superior a 3.5. Cuando MAD es cero, se exige que la orden sea al menos el doble o como máximo
        la mitad del factor mediano. En todos los casos debe existir una diferencia mínima de un formato completo.
        Una recomendación igual a cero se maneja como **ratio no aplicable**, sin dividir por cero. Se excluyen del
        benchmarking ingredientes desconocidos, inventario o proyección faltante, datos no calculables y formatos no
        enteros. Dos pares implican confianza baja; tres o más, confianza moderada. No se asigna confianza alta.

        Esta comparación no usa pedidos por cliente porque los CSV no contienen clientes ni ventas. La recomendación
        calculada funciona como referencia de escala para no confundir una sucursal de mayor demanda con una señal.
        Puede superponerse con una alerta principal y no se cuenta como otro producto. En una omisión, **Producto
        omitido** permanece como diagnóstico principal y la comparación entre sucursales es contexto secundario.

        #### Limitaciones

        Los archivos no contienen precios, ventas, clientes, lead times ni nivel de servicio. Por eso esta versión no
        calcula ahorro monetario, días de inventario o demanda por cliente. Las recomendaciones son apoyo a la decisión y
        requieren aprobación humana.
        """
    )
    if margin:
        st.warning(
            f"La simulación actual aplica un margen de seguridad de {margin:.0%} sobre la proyección. "
            "Este ajuste no forma parte de la fórmula original."
        )
    else:
        st.info("La simulación actual usa margen de seguridad 0%, igual a la fórmula original.")


def render_local_assistant(pipeline: dict[str, object]) -> None:
    st.subheader("💬 Pregúntale a tus datos")
    st.caption(
        "Asistente local de consultas basado en reglas. No es un modelo generativo y no envía datos a servicios externos."
    )
    alerts = pipeline["purchase_alerts"]
    review = pipeline["review"]
    overorders = alerts[alerts["tipo_alerta"] == "SOBREPEDIDO"].sort_values(
        "diferencia_formatos", ascending=False
    )
    example_ingredient = (
        overorders.iloc[0]["ingrediente"]
        if not overorders.empty
        else review["nombre"].dropna().iloc[0]
    )
    supplier_totals = (
        review[review["formatos_recomendados"].notna()]
        .groupby("proveedor")["formatos_recomendados"]
        .sum()
        .sort_values(ascending=False)
    )
    example_supplier = supplier_totals.index[0] if not supplier_totals.empty else "el proveedor"
    suggestions = [
        "¿Qué sucursal tiene más riesgos de quiebre?",
        f"¿Quién está pidiendo demasiado {example_ingredient}?",
        "¿Qué productos fueron omitidos?",
        "¿Cuáles sobrepedidos son perecederos?",
        f"¿Qué debo pedirle a {example_supplier}?",
        "¿Qué sucursal tiene más alertas?",
        "¿Qué comportamientos inusuales hay entre sucursales?",
        "¿Qué ingredientes presentan tendencias?",
        "¿Qué datos tienen errores?",
    ]
    for start in range(0, len(suggestions), 4):
        columns = st.columns(4)
        for column, suggestion in zip(columns, suggestions[start : start + 4]):
            column.button(
                suggestion,
                key=f"suggestion_{start}_{suggestion}",
                width="stretch",
                on_click=lambda value=suggestion: st.session_state.update(
                    assistant_question_input=value
                ),
            )
    question = st.text_input(
        "Pregunta",
        placeholder="Ejemplo: ¿Qué productos fueron omitidos?",
        key="assistant_question_input",
    )
    if question:
        answer = answer_local_question(
            question,
            pipeline["review"],
            pipeline["purchase_alerts"],
            pipeline["quality"],
            pipeline["forecasts"],
            pipeline["cross_branch_anomalies"],
        )
        st.markdown(f"<div class='bp-note'><b>Respuesta:</b> {escape(answer)}</div>", unsafe_allow_html=True)


try:
    bundle = load_default_data()
except Exception as exc:
    st.error(f"No fue posible cargar los archivos de datos: {exc}")
    st.stop()

if "working_order" not in st.session_state:
    initial_order = bundle.orden.copy()
    initial_order["cantidad_formatos"] = pd.to_numeric(
        initial_order["cantidad_formatos"], errors="coerce"
    )
    st.session_state.working_order = initial_order
if "editor_version" not in st.session_state:
    st.session_state.editor_version = 0

st.markdown(
    """
    <div class="bp-hero">
      <h1>🍕 Barrio Pizza | Asistente Inteligente de Compras</h1>
      <p>Revisa órdenes semanales, detecta faltantes, sobrepedidos, omisiones y problemas de datos en segundos.</p>
      <span class="bp-human">👤 Recomendaciones sujetas a aprobación humana</span>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Controles de revisión")
    historical_weeks = bundle.historico.get("semana", pd.Series(dtype="object")).dropna().astype(str)
    max_week = max(historical_weeks, key=week_number) if not historical_weeks.empty else "sin semana"
    st.caption(f"Revisión posterior a {max_week} · {date.today().strftime('%d/%m/%Y')}")
    margin_percent = st.slider(
        "Margen de seguridad simulado",
        min_value=0,
        max_value=20,
        value=0,
        step=1,
        help="Simulación opcional; no forma parte de la fórmula original.",
    )
    if margin_percent:
        st.warning(f"Simulación activa: +{margin_percent}% sobre la proyección.")

pipeline = run_pipeline(bundle, st.session_state.working_order, margin_percent / 100.0)
validated = pipeline["validated"]
review = pipeline["review"]
purchase_alerts = pipeline["purchase_alerts"]
cross_branch_anomalies = pipeline["cross_branch_anomalies"]
quality = pipeline["quality"]

with st.sidebar:
    st.divider()
    st.subheader("Filtros")
    filter_values = {
        "sucursales": st.multiselect("Sucursal", sorted(review["sucursal"].dropna().unique())),
        "proveedores": st.multiselect("Proveedor", sorted(review["proveedor"].dropna().unique())),
        "ingredientes": st.multiselect("Ingrediente", sorted(review["nombre"].dropna().unique())),
        "tipos": st.multiselect(
            "Tipo de alerta", sorted(purchase_alerts["tipo_alerta"].dropna().unique()) if not purchase_alerts.empty else []
        ),
        "direcciones": st.multiselect(
            "Comportamiento inusual entre sucursales",
            sorted(cross_branch_anomalies["direccion"].dropna().unique())
            if not cross_branch_anomalies.empty
            else [],
        ),
        "severidades": st.multiselect(
            "Severidad", [item for item in ["Crítica", "Alta", "Media", "Baja"] if item in set(purchase_alerts.get("severidad", []))]
        ),
        "perecedero": st.multiselect("Perecedero", ["Sí", "No"]),
        "metodos": st.multiselect("Método de proyección", sorted(review["metodo_proyeccion"].dropna().unique())),
    }

filtered_review = apply_review_filters(review, filter_values)
filtered_alerts = filter_rows(
    purchase_alerts,
    branches=filter_values["sucursales"],
    suppliers=filter_values["proveedores"],
    ingredients=filter_values["ingredientes"],
    alert_types=filter_values["tipos"],
    severities=filter_values["severidades"],
    perishability=filter_values["perecedero"],
    methods=filter_values["metodos"],
)
filtered_quality = quality.copy()
if filter_values["sucursales"] and not filtered_quality.empty:
    filtered_quality = filtered_quality[
        filtered_quality["sucursal"].isna()
        | filtered_quality["sucursal"].isin(filter_values["sucursales"])
    ]
filtered_cross_branch = scope_cross_branch_behaviors(
    cross_branch_anomalies,
    filtered_review,
)
if not filtered_cross_branch.empty:
    if filter_values["severidades"]:
        filtered_cross_branch = filtered_cross_branch[
            filtered_cross_branch["severidad"].isin(filter_values["severidades"])
        ]
    if filter_values["direcciones"]:
        filtered_cross_branch = filtered_cross_branch[
            filtered_cross_branch["direccion"].isin(filter_values["direcciones"])
        ]

st.caption(
    f"Fuente: 4 CSV locales · {len(validated.sucursales)} sucursales · "
    f"{validated.catalogo['ingrediente_id'].nunique()} ingredientes de catálogo · sin API keys"
)

tabs = st.tabs(
    [
        "📊 Resumen ejecutivo",
        "🚨 Alertas",
        "🔎 Comportamiento inusual entre sucursales",
        "🏪 Detalle por sucursal",
        "🧪 Simulador de orden",
        "📦 Orden corregida",
        "🧩 Calidad de datos",
        "💬 Pregúntale a tus datos",
        "📐 Metodología",
    ]
)
with tabs[0]:
    render_executive(
        filtered_review,
        filtered_alerts,
        filtered_quality,
        filtered_cross_branch,
    )
with tabs[1]:
    render_alerts(filtered_alerts)
with tabs[2]:
    render_cross_branch_anomalies(filtered_review, filtered_cross_branch)
with tabs[3]:
    render_branch_detail(validated, review, pipeline["forecasts"], pipeline["outliers"])
with tabs[4]:
    render_simulator(bundle, pipeline)
with tabs[5]:
    render_corrected(pipeline)
with tabs[6]:
    render_quality(pipeline)
with tabs[7]:
    render_local_assistant(pipeline)
with tabs[8]:
    render_methodology(margin_percent / 100.0)
