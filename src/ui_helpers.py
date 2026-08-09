"""Utilidades de presentación, filtros y consultas locales en español."""

from __future__ import annotations

import unicodedata

import pandas as pd

from src.alerts import format_number, purchase_format_phrase


SEVERITY_ICONS = {"Crítica": "🔴", "Alta": "🟠", "Media": "🟡", "Baja": "🔵"}
STATE_ICONS = {
    "OMITIDO": "⛔",
    "FALTANTE": "⚠️",
    "SOBREPEDIDO": "📦",
    "CORRECTO": "✅",
    "SIN NECESIDAD": "◻️",
    "DATO INCOMPLETO": "❓",
}


def normalize_text(text: object) -> str:
    """Normaliza mayúsculas y tildes para interpretar consultas sencillas."""

    value = unicodedata.normalize("NFKD", str(text).lower())
    return "".join(char for char in value if not unicodedata.combining(char))


def dataframe_to_csv_bytes(frame: pd.DataFrame) -> bytes:
    """Genera CSV UTF-8 con BOM para abrir correctamente en Excel."""

    return frame.to_csv(index=False).encode("utf-8-sig")


def filter_rows(
    frame: pd.DataFrame,
    *,
    branches: list[str] | None = None,
    suppliers: list[str] | None = None,
    ingredients: list[str] | None = None,
    alert_types: list[str] | None = None,
    severities: list[str] | None = None,
    perishability: list[str] | None = None,
    methods: list[str] | None = None,
) -> pd.DataFrame:
    """Aplica filtros únicamente cuando la columna correspondiente existe."""

    result = frame.copy()
    mappings = [
        ("sucursal", branches),
        ("proveedor", suppliers),
        ("ingrediente", ingredients),
        ("tipo_alerta", alert_types),
        ("severidad", severities),
        ("es_perecedero", perishability),
        ("metodo_proyeccion", methods),
    ]
    for column, selected in mappings:
        if selected and column in result.columns:
            result = result[result[column].isin(selected)]
    return result


def _find_entity(question: str, values: pd.Series) -> str | None:
    normalized_question = normalize_text(question)
    candidates = sorted(values.dropna().astype(str).unique(), key=len, reverse=True)
    for candidate in candidates:
        normalized_candidate = normalize_text(candidate)
        if normalized_candidate in normalized_question:
            return candidate
        meaningful_words = [word for word in normalized_candidate.split() if len(word) >= 5]
        if meaningful_words and all(word in normalized_question for word in meaningful_words):
            return candidate
    return None


def _top_counts(frame: pd.DataFrame, column: str) -> str:
    if frame.empty:
        return "No hay resultados para esta consulta."
    counts = frame[column].value_counts()
    maximum = int(counts.max())
    leaders = counts[counts == maximum].index.astype(str).tolist()
    return f"{', '.join(leaders)} ({maximum} alerta{'s' if maximum != 1 else ''})."


def answer_local_question(
    question: str,
    review: pd.DataFrame,
    purchase_alerts: pd.DataFrame,
    quality_issues: pd.DataFrame,
    forecasts: pd.DataFrame,
    cross_branch_anomalies: pd.DataFrame | None = None,
) -> str:
    """Responde intenciones frecuentes con reglas locales y resultados del DataFrame."""

    if not question or not question.strip():
        return "Escribe una pregunta o selecciona una sugerencia."
    normalized = normalize_text(question)
    peer_anomalies = (
        cross_branch_anomalies
        if cross_branch_anomalies is not None
        else pd.DataFrame()
    )

    if any(term in normalized for term in ["datos tienen errores", "errores de datos", "calidad"]):
        errors = quality_issues[quality_issues["nivel"] == "Error"]
        if errors.empty:
            return "No se detectaron errores de calidad de datos."
        summary = errors["codigo"].value_counts()
        details = "; ".join(f"{code}: {count}" for code, count in summary.items())
        return f"Se detectaron {len(errors)} incidencias de error. {details}."

    if "tendencia" in normalized:
        trends = forecasts[forecasts["metodo_proyeccion"] == "Tendencia lineal"]
        if trends.empty:
            return "No se detectaron tendencias fuertes con los umbrales definidos."
        merged = trends.merge(
            review[["sucursal", "ingrediente_id", "nombre"]].drop_duplicates(),
            on=["sucursal", "ingrediente_id"],
            how="left",
            validate="one_to_one",
        )
        items = [
            f"{row.nombre} en {row.sucursal} (R²={format_number(row.r2)})"
            for row in merged.itertuples()
        ]
        return "Presentan tendencia fuerte: " + "; ".join(items) + "."

    rare_order_intent = (
        "orden" in normalized
        and any(term in normalized for term in ["rara", "raro", "atipic", "inusual"])
    ) or "entre sucursales" in normalized
    if rare_order_intent:
        if peer_anomalies.empty:
            return "No se detectó comportamiento inusual entre sucursales comparables."
        details = "; ".join(
            f"{row.sucursal} · {row.ingrediente}: {row.diagnostico_principal}; "
            f"contexto {str(row.direccion).lower()}, ratio {row.ratio_sucursal}, "
            f"mediana {row.ratio_mediana_pares}, diferencia "
            f"{int(row.diferencia_formatos):+d} formatos, {int(row.cantidad_pares)} pares, "
            f"confianza {str(row.nivel_confianza).lower()}"
            for row in peer_anomalies.itertuples()
        )
        count = len(peer_anomalies)
        prefix = (
            "Se detectó 1 comportamiento inusual entre sucursales"
            if count == 1
            else f"Se detectaron {count} comportamientos inusuales entre sucursales"
        )
        return f"{prefix}: {details}."

    if "omitid" in normalized or "olvid" in normalized:
        omitted = purchase_alerts[purchase_alerts["tipo_alerta"] == "OMITIDO"]
        if omitted.empty:
            return "No hay productos omitidos con necesidad positiva."
        return "Productos omitidos: " + "; ".join(
            f"{row.ingrediente} en {row.sucursal}: agregar {purchase_format_phrase(row.formato_compra, int(row.formatos_recomendados))}"
            for row in omitted.itertuples()
        ) + "."

    if "pereceder" in normalized and any(
        term in normalized for term in ["sobrepedido", "demasiad", "de mas"]
    ):
        rows = purchase_alerts[
            (purchase_alerts["tipo_alerta"] == "SOBREPEDIDO")
            & (purchase_alerts["es_perecedero"] == "Sí")
        ]
        if rows.empty:
            return "No hay sobrepedidos perecederos."
        return "Sobrepedidos perecederos: " + "; ".join(
            f"{row.sucursal} · {row.ingrediente}: retirar {purchase_format_phrase(row.formato_compra, int(row.diferencia_formatos))}"
            for row in rows.itertuples()
        ) + "."

    increase_order_intent = "orden" in normalized and any(
        term in normalized
        for term in ["aumentar", "incrementar", "subir", "pedir mas", "necesitan mas"]
    )
    if increase_order_intent:
        rows = purchase_alerts[
            purchase_alerts["tipo_alerta"].isin(["FALTANTE", "OMITIDO"])
        ]
        if rows.empty:
            return "Ninguna sucursal necesita aumentar su orden con la revisión actual."
        summaries = []
        for branch_name, group in rows.groupby("sucursal", sort=True):
            details = "; ".join(
                f"{row.ingrediente}: agregar "
                f"{purchase_format_phrase(row.formato_compra, abs(int(row.diferencia_formatos)))}"
                for row in group.itertuples()
            )
            summaries.append(
                f"{branch_name} debe ajustar {len(group)} "
                f"línea{'s' if len(group) != 1 else ''}: {details}"
            )
        return "Sucursales que necesitan aumentar su orden: " + ". ".join(summaries) + "."

    supplier = _find_entity(question, review["proveedor"])
    if supplier and any(term in normalized for term in ["pedir", "proveedor", "orden"]):
        rows = review[
            (review["proveedor"] == supplier)
            & review["formatos_recomendados"].notna()
            & (review["formatos_recomendados"] > 0)
        ]
        if rows.empty:
            return f"No hay cantidades recomendadas positivas para {supplier}."
        by_product = (
            rows.groupby(["nombre", "formato_compra"], as_index=False)["formatos_recomendados"]
            .sum()
            .sort_values("formatos_recomendados", ascending=False)
        )
        details = "; ".join(
            f"{row.nombre}: {purchase_format_phrase(row.formato_compra, int(row.formatos_recomendados))}"
            for row in by_product.itertuples()
        )
        return f"Orden recomendada para {supplier}, sumada entre sucursales: {details}."

    if "sucursal" in normalized and any(
        term in normalized for term in ["mas alert", "mas riesgo", "quiebre"]
    ):
        relevant = purchase_alerts
        if "quiebre" in normalized or "riesgo" in normalized:
            relevant = relevant[relevant["tipo_alerta"].isin(["FALTANTE", "OMITIDO"])]
        return "La sucursal con mayor cantidad es: " + _top_counts(relevant, "sucursal")

    ingredient = _find_entity(question, review["nombre"])
    if ingredient:
        matches = purchase_alerts[purchase_alerts["ingrediente"] == ingredient]
        if any(term in normalized for term in ["demasiad", "sobrepedido", "de mas"]):
            matches = matches[matches["tipo_alerta"] == "SOBREPEDIDO"]
        if matches.empty:
            return f"No hay alertas que coincidan con {ingredient}."
        return " ".join(matches["mensaje"].astype(str).tolist())

    branch = _find_entity(question, review["sucursal"])
    if branch:
        matches = purchase_alerts[purchase_alerts["sucursal"] == branch]
        if matches.empty:
            return f"{branch} no tiene alertas de compra con la revisión actual."
        return f"{branch} tiene {len(matches)} alertas: " + "; ".join(
            f"{row.tipo_alerta.lower()} de {row.ingrediente}"
            for row in matches.itertuples()
        ) + "."

    return (
        "No identifiqué una intención compatible. Prueba con una sucursal, un ingrediente, "
        "un proveedor, órdenes raras entre sucursales, productos omitidos, sobrepedidos "
        "perecederos, tendencias o errores de datos."
    )


def friendly_review_table(review: pd.DataFrame) -> pd.DataFrame:
    """Selecciona y renombra columnas para la tabla principal de negocio."""

    columns = {
        "sucursal": "Sucursal",
        "nombre": "Ingrediente",
        "proveedor": "Proveedor",
        "formato_compra": "Formato de compra",
        "inventario_actual": "Inventario actual",
        "consumo_proyectado": "Proyección",
        "necesidad_base": "Necesidad",
        "formatos_ordenados": "Formatos ordenados",
        "formatos_recomendados": "Formatos recomendados",
        "diferencia_formatos": "Diferencia",
        "unidad_base": "Unidad base",
        "estado": "Estado",
        "metodo_proyeccion": "Método",
        "nivel_confianza": "Confianza",
    }
    available = [column for column in columns if column in review]
    return review[available].rename(columns=columns)


def friendly_corrected_order(corrected: pd.DataFrame) -> pd.DataFrame:
    """Convierte la orden corregida en decisiones comprensibles para compras."""

    decision_labels = {
        "OMITIDO": "Agregar producto",
        "FALTANTE": "Aumentar pedido",
        "SOBREPEDIDO": "Reducir pedido",
        "DATO INCOMPLETO": "Revisar datos",
        "CORRECTO": "Sin cambios",
        "SIN NECESIDAD": "Sin cambios",
    }
    priorities = {
        "OMITIDO": 0,
        "FALTANTE": 1,
        "SOBREPEDIDO": 2,
        "DATO INCOMPLETO": 3,
        "CORRECTO": 4,
        "SIN NECESIDAD": 5,
    }

    def integer(value: object) -> int | None:
        if value is None or pd.isna(value):
            return None
        return int(round(float(value)))

    def quantity(value: object, format_name: object) -> str:
        number = integer(value)
        if number is None:
            return "No calculable"
        return purchase_format_phrase(format_name, number)

    rows: list[dict[str, object]] = []
    for row in corrected.itertuples(index=False):
        state = str(getattr(row, "estado", "DATO INCOMPLETO"))
        format_name = getattr(row, "formato_compra", "formato")
        original = integer(getattr(row, "cantidad_formatos_original", None))
        recommended = integer(getattr(row, "cantidad_formatos_corregida", None))
        difference = integer(getattr(row, "diferencia_formatos_corregir", None))
        if recommended is None or difference is None:
            change = "Confirmar los datos antes de decidir"
        elif difference < 0:
            change = f"Agregar {purchase_format_phrase(format_name, abs(difference))}"
        elif difference > 0:
            change = f"Retirar {purchase_format_phrase(format_name, difference)}"
        else:
            change = "Mantener la cantidad actual"
        rows.append(
            {
                "_estado": state,
                "_prioridad": priorities.get(state, 99),
                "Decisión": decision_labels.get(state, "Revisar"),
                "Sucursal": getattr(row, "sucursal", ""),
                "Ingrediente": getattr(row, "nombre", ""),
                "Pedido actual": quantity(original, format_name),
                "Cantidad sugerida": quantity(recommended, format_name),
                "Cambio": change,
                "Proveedor": getattr(row, "proveedor", ""),
                "Formato de compra": format_name,
            }
        )
    result = pd.DataFrame(
        rows,
        columns=[
            "_estado",
            "_prioridad",
            "Decisión",
            "Sucursal",
            "Ingrediente",
            "Pedido actual",
            "Cantidad sugerida",
            "Cambio",
            "Proveedor",
            "Formato de compra",
        ],
    )
    if result.empty:
        return result
    return result.sort_values(
        ["_prioridad", "Sucursal", "Ingrediente"],
        na_position="last",
    ).reset_index(drop=True)


def inject_app_css(st_module: object) -> None:
    """Aplica una identidad visual cálida sin afirmar colores corporativos oficiales."""

    st_module.markdown(
        """
        <style>
        :root { --bp-terracotta:#C95F3D; --bp-ink:#2E2925; --bp-cream:#FFF8EF; --bp-gold:#E5A23B; }
        .stApp { background: linear-gradient(180deg, #FFFDF9 0%, #FFF8EF 100%); }
        [data-testid="stSidebar"] { background: #2E2925; }
        [data-testid="stSidebar"] * { color: #FFF8EF; }
        [data-testid="stMetric"] { background: white; border: 1px solid #E8DED2; border-radius: 14px; padding: 12px; box-shadow: 0 3px 12px rgba(46,41,37,.06); }
        .bp-hero { background: linear-gradient(135deg,#2E2925 0%,#5A3328 100%); color:white; padding:1.55rem 1.7rem; border-radius:18px; margin-bottom:1rem; }
        .bp-hero h1 { margin:0; font-size:2rem; }
        .bp-hero p { margin:.45rem 0 0; color:#F8E8D5; }
        .bp-human { display:inline-block; margin-top:.7rem; padding:.3rem .7rem; border-radius:999px; background:#FFF2CF; color:#5A3B00; font-size:.85rem; font-weight:600; }
        .bp-alert { background:white; border-left:6px solid #C95F3D; padding:1rem 1.1rem; border-radius:12px; margin:.65rem 0; box-shadow:0 2px 8px rgba(46,41,37,.08); }
        .bp-alert small { color:#6A615A; }
        .bp-note { background:#FFF2CF; border:1px solid #E8C874; border-radius:12px; padding:.8rem 1rem; }
        div[data-baseweb="tab-list"] { gap:.25rem; }
        button[data-baseweb="tab"] { border-radius:10px 10px 0 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )
