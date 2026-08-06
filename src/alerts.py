"""Construcción de alertas accionables en lenguaje de negocio."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


ALERT_COLUMNS = [
    "alerta_id",
    "categoria",
    "tipo_alerta",
    "severidad",
    "sucursal",
    "ingrediente_id",
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
    "metodo_proyeccion",
    "razon",
    "accion_recomendada",
    "mensaje",
]

_PLURALS = {
    "saco": "sacos",
    "bolsa": "bolsas",
    "caja": "cajas",
    "lata": "latas",
    "balde": "baldes",
    "paquete": "paquetes",
    "kilo": "kilos",
    "unidad": "unidades",
    "pieza": "piezas",
}


def format_number(value: object, decimals: int = 2) -> str:
    """Muestra enteros sin .0 y decimales sin ceros innecesarios."""

    if value is None or pd.isna(value):
        return "—"
    number = float(value)
    if math.isclose(number, round(number), abs_tol=10 ** (-(decimals + 1))):
        return f"{int(round(number)):,}".replace(",", ".")
    text = f"{number:,.{decimals}f}".rstrip("0").rstrip(".")
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def purchase_format_phrase(format_name: object, quantity: int) -> str:
    """Convierte 'Saco 25 kg' en '7 sacos de 25 kg'."""

    if pd.isna(format_name):
        return f"{quantity} formatos"
    parts = str(format_name).strip().split(maxsplit=1)
    noun = parts[0]
    normalized = noun.lower()
    label = noun.lower() if quantity == 1 else _PLURALS.get(normalized, f"{noun.lower()}s")
    detail = parts[1] if len(parts) > 1 else ""
    detail = detail.replace("x ", "").strip()
    connector = f" de {detail}" if detail else ""
    return f"{quantity} {label}{connector}"


def _severity(row: pd.Series) -> str:
    state = row["estado"]
    if state == "OMITIDO":
        return "Crítica"
    if state == "FALTANTE":
        recommended = float(row["formatos_recomendados"])
        missing = max(-float(row["diferencia_formatos"]), 0.0)
        return "Crítica" if recommended > 0 and missing / recommended >= 0.50 else "Alta"
    if state == "SOBREPEDIDO":
        return "Media" if bool(row["es_perecedero_bool"]) else "Baja"
    return "Alta"


def _alert_text(row: pd.Series) -> tuple[str, str, str]:
    ordered = int(row["formatos_ordenados"])
    recommended = int(row["formatos_recomendados"])
    difference = int(row["diferencia_formatos"])
    ordered_phrase = purchase_format_phrase(row["formato_compra"], ordered)
    recommended_phrase = purchase_format_phrase(row["formato_compra"], recommended)
    unit = row["unidad_base"]
    ordered_base = format_number(row["cantidad_ordenada_base"])
    recommended_base = format_number(row["cantidad_recomendada_base"])
    ingredient = row["nombre"]
    branch = row["sucursal"]

    if row["estado"] == "OMITIDO":
        reason = "El producto no aparece en la orden y la necesidad proyectada es positiva."
        action = f"Agregar {recommended_phrase} a la orden antes de aprobarla."
        message = (
            f"PRODUCTO OMITIDO: {branch} no incluyó {ingredient} en su orden. "
            f"Se recomiendan {recommended_phrase}, equivalentes a {recommended_base} {unit}, "
            "para cubrir la necesidad proyectada."
        )
    elif row["estado"] == "FALTANTE":
        missing = abs(difference)
        missing_phrase = purchase_format_phrase(row["formato_compra"], missing)
        missing_base = format_number(abs(row["diferencia_base"]))
        reason = "La cantidad ordenada no cubre la necesidad proyectada después del inventario."
        action = f"Aumentar la orden en {missing_phrase}."
        message = (
            f"RIESGO DE QUIEBRE: {branch} pidió {ordered_phrase} de {ingredient}, equivalentes a "
            f"{ordered_base} {unit}, pero la recomendación es de {recommended_phrase}. "
            f"Faltan {missing_phrase}, equivalentes a {missing_base} {unit}."
        )
    else:
        excess = difference
        excess_phrase = purchase_format_phrase(row["formato_compra"], excess)
        reason = "Se pidió al menos un formato completo adicional sobre la recomendación."
        if bool(row["es_perecedero_bool"]):
            reason += " El ingrediente es perecedero."
        action = f"Revisar y, si no existe una razón operativa, retirar {excess_phrase}."
        message = (
            f"SOBREPEDIDO: {branch} pidió {ordered_phrase} de {ingredient}, equivalentes a "
            f"{ordered_base} {unit}, pero la recomendación es de {recommended_phrase} "
            f"({recommended_base} {unit}). Se podrían retirar {excess_phrase} de la orden."
        )
        if bool(row["es_perecedero_bool"]):
            message += " Es un producto perecedero y requiere revisión prioritaria."
    return reason, action, message


def build_purchase_alerts(review: pd.DataFrame) -> pd.DataFrame:
    """Genera alertas de compra separadas de incidencias y anomalías históricas."""

    actionable = review[review["estado"].isin(["OMITIDO", "FALTANTE", "SOBREPEDIDO"])].copy()
    alerts: list[dict[str, object]] = []
    for index, row in actionable.iterrows():
        reason, action, message = _alert_text(row)
        alerts.append(
            {
                "alerta_id": f"COMPRA-{len(alerts) + 1:03d}",
                "categoria": "Alerta de compra",
                "tipo_alerta": row["estado"],
                "severidad": _severity(row),
                "sucursal": row["sucursal"],
                "ingrediente_id": row["ingrediente_id"],
                "ingrediente": row["nombre"],
                "proveedor": row["proveedor"],
                "es_perecedero": "Sí" if row["es_perecedero_bool"] else "No",
                "formato_compra": row["formato_compra"],
                "formatos_ordenados": int(row["formatos_ordenados"]),
                "cantidad_ordenada_base": row["cantidad_ordenada_base"],
                "formatos_recomendados": int(row["formatos_recomendados"]),
                "cantidad_recomendada_base": row["cantidad_recomendada_base"],
                "diferencia_formatos": int(row["diferencia_formatos"]),
                "unidad_base": row["unidad_base"],
                "metodo_proyeccion": row["metodo_proyeccion"],
                "razon": reason,
                "accion_recomendada": action,
                "mensaje": message,
            }
        )
    frame = pd.DataFrame(alerts, columns=ALERT_COLUMNS)
    if frame.empty:
        return frame
    severity_order = pd.CategoricalDtype(["Crítica", "Alta", "Media", "Baja"], ordered=True)
    frame["severidad"] = frame["severidad"].astype(severity_order)
    frame = frame.sort_values(
        ["severidad", "sucursal", "ingrediente"], na_position="last"
    ).reset_index(drop=True)
    frame["severidad"] = frame["severidad"].astype("object")
    return frame


def build_anomaly_alerts(outliers: pd.DataFrame, catalog: pd.DataFrame) -> pd.DataFrame:
    """Enriquece anomalías históricas sin mezclarlas con alertas de compra."""

    if outliers.empty:
        return outliers.copy()
    metadata = catalog[["ingrediente_id", "nombre", "unidad_base"]].drop_duplicates(
        "ingrediente_id", keep=False
    )
    result = outliers.merge(
        metadata,
        on="ingrediente_id",
        how="left",
        validate="many_to_one",
    )
    result["categoria"] = "Anomalía histórica"
    result["severidad"] = "Baja"
    result["detalle"] = result.apply(
        lambda row: (
            f"{row['sucursal']} · {row['nombre']} · {row['semana']}: "
            f"{format_number(row['consumo_unidad_base'])} {row['unidad_base']} fue detectado como atípico"
            + (" y se excluyó de la proyección." if row["excluido_proyeccion"] else ".")
        ),
        axis=1,
    )
    return result


def build_quality_alerts(issues: pd.DataFrame) -> pd.DataFrame:
    """Añade severidad operativa a las incidencias de calidad."""

    quality = issues.copy()
    if quality.empty:
        quality["severidad"] = pd.Series(dtype="object")
        return quality
    critical_codes = {"INGREDIENTE_DESCONOCIDO", "INVENTARIO_FALTANTE", "COLUMNA_AUSENTE"}
    quality["severidad"] = np.where(
        quality["codigo"].isin(critical_codes),
        "Crítica",
        np.where(quality["nivel"].eq("Error"), "Alta", "Baja"),
    )
    return quality
