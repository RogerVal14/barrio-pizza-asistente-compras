"""Pruebas del comportamiento inusual entre sucursales."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.benchmarking import (
    detect_cross_branch_order_anomalies,
    scope_cross_branch_behaviors,
    summarize_attention_overlap,
)
from src.data_loader import load_data
from src.forecasting import forecast_all
from src.purchasing import build_purchase_review
from src.ui_helpers import answer_local_question
from src.validation import validate_data


def _review(
    ordered: list[float],
    recommended: list[float],
    *,
    ingredient_id: str = "ingrediente_nuevo",
    perishable: bool = False,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for index, (order, recommendation) in enumerate(
        zip(ordered, recommended, strict=True)
    ):
        difference = order - recommendation
        if recommendation > 0 and order == 0:
            state = "OMITIDO"
        elif difference < 0:
            state = "FALTANTE"
        elif difference > 0:
            state = "SOBREPEDIDO"
        else:
            state = "CORRECTO" if recommendation > 0 else "SIN NECESIDAD"
        rows.append(
            {
                "sucursal": f"Sucursal nueva {index + 1}",
                "ingrediente_id": ingredient_id,
                "nombre": "Ingrediente dinámico",
                "proveedor": "Proveedor dinámico",
                "unidad_base": "kg",
                "formato_compra": "Caja 5 kg",
                "unidad_base_por_formato": 5.0,
                "consumo_proyectado": 50.0,
                "inventario_actual": 5.0,
                "formatos_ordenados": order,
                "formatos_recomendados": recommendation,
                "diferencia_formatos": difference,
                "cantidad_ordenada_base": order * 5,
                "cantidad_recomendada_base": recommendation * 5,
                "estado": state,
                "razon_dato_incompleto": None,
                "es_perecedero_bool": perishable,
            }
        )
    return pd.DataFrame(rows)


def test_detects_order_far_above_peer_pattern() -> None:
    behaviors = detect_cross_branch_order_anomalies(
        _review([10, 10, 10, 30], [10, 10, 10, 10])
    )

    assert len(behaviors) == 1
    row = behaviors.iloc[0]
    assert row["sucursal"] == "Sucursal nueva 4"
    assert row["direccion"] == "MUY POR ENCIMA"
    assert row["factor_vs_recomendacion"] == pytest.approx(3.0)
    assert row["mediana_factor_pares"] == pytest.approx(1.0)
    assert row["cantidad_pares"] == 3
    assert row["nivel_confianza"] == "Moderada"


def test_detects_order_far_below_peer_pattern() -> None:
    behaviors = detect_cross_branch_order_anomalies(
        _review([10, 10, 10, 4], [10, 10, 10, 10])
    )

    assert len(behaviors) == 1
    assert behaviors.iloc[0]["direccion"] == "MUY POR DEBAJO"
    assert behaviors.iloc[0]["severidad"] == "Alta"


def test_different_branch_sizes_are_not_unusual_when_orders_match_need() -> None:
    behaviors = detect_cross_branch_order_anomalies(
        _review([2, 5, 10, 20], [2, 5, 10, 20])
    )

    assert behaviors.empty


def test_modified_z_score_is_used_when_peer_mad_is_positive() -> None:
    behaviors = detect_cross_branch_order_anomalies(
        _review([8, 10, 12, 30], [10, 10, 10, 10])
    )

    candidate = behaviors[behaviors["sucursal"] == "Sucursal nueva 4"].iloc[0]
    assert candidate["modified_z_score"] > 3.5
    assert candidate["metodo_deteccion"].startswith("Modified z-score")


def test_recommendation_zero_is_explicit_and_contains_no_nan_or_infinity() -> None:
    behaviors = detect_cross_branch_order_anomalies(
        _review([0, 0, 0, 3], [0, 0, 0, 0], perishable=True)
    )

    assert len(behaviors) == 1
    row = behaviors.iloc[0]
    assert row["direccion"] == "MUY POR ENCIMA"
    assert row["factor_vs_recomendacion"] == "No aplica (recomendación = 0)"
    assert row["ratio_sucursal"] == "No aplica (recomendación = 0)"
    assert row["severidad"] == "Media"
    assert not behaviors.isna().any().any()
    numeric = behaviors.select_dtypes(include=[np.number])
    assert np.isfinite(numeric.to_numpy(dtype=float)).all()


def test_unknown_ingredient_is_excluded_using_catalog_ids() -> None:
    review = _review(
        [10, 10, 10, 30],
        [10, 10, 10, 10],
        ingredient_id="fuera_de_catalogo",
    )

    behaviors = detect_cross_branch_order_anomalies(
        review,
        catalog_ingredient_ids={"ingrediente_conocido"},
    )

    assert behaviors.empty


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("inventario_actual", np.nan),
        ("consumo_proyectado", np.nan),
        ("estado", "DATO INCOMPLETO"),
    ],
)
def test_incomplete_data_is_excluded(column: str, value: object) -> None:
    review = _review([10, 10, 10, 30], [10, 10, 10, 10])
    review.loc[3, column] = value

    behaviors = detect_cross_branch_order_anomalies(review)

    assert behaviors.empty


def test_non_integer_or_invalid_quantities_are_excluded() -> None:
    review = _review([10, 10, 10, 30], [10, 10, 10, 10])
    for column in [
        "formatos_ordenados",
        "diferencia_formatos",
        "cantidad_ordenada_base",
    ]:
        review[column] = review[column].astype(float)
    review.loc[3, "formatos_ordenados"] = 30.5
    review.loc[3, "diferencia_formatos"] = 20.5
    review.loc[3, "cantidad_ordenada_base"] = 152.5

    behaviors = detect_cross_branch_order_anomalies(review)

    assert behaviors.empty


def test_two_comparable_branches_produce_low_confidence() -> None:
    behaviors = detect_cross_branch_order_anomalies(
        _review([10, 10, 30], [10, 10, 10])
    )

    assert len(behaviors) == 1
    assert behaviors.iloc[0]["cantidad_pares"] == 2
    assert behaviors.iloc[0]["nivel_confianza"] == "Baja"


def test_requires_at_least_two_other_branches() -> None:
    behaviors = detect_cross_branch_order_anomalies(
        _review([10, 40], [10, 10])
    )

    assert behaviors.empty


def test_mad_zero_uses_explicit_fallback_without_nan() -> None:
    behaviors = detect_cross_branch_order_anomalies(
        _review([10, 10, 10, 30], [10, 10, 10, 10])
    )

    row = behaviors.iloc[0]
    assert row["mad_factor_pares"] == pytest.approx(0.0)
    assert row["modified_z_score"] == "No aplica"
    assert "MAD igual a cero" in row["metodo_deteccion"]


def test_scope_merge_preserves_unique_lines() -> None:
    review = _review([10, 10, 10, 30], [10, 10, 10, 10])
    behaviors = detect_cross_branch_order_anomalies(review)

    scoped = scope_cross_branch_behaviors(behaviors, review)

    assert len(scoped) == len(behaviors)
    assert not scoped.duplicated(["sucursal", "ingrediente_id"]).any()


def test_scope_merge_rejects_duplicate_review_keys() -> None:
    review = _review([10, 10, 10, 30], [10, 10, 10, 10])
    behaviors = detect_cross_branch_order_anomalies(review)
    duplicated_review = pd.concat([review, review.iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="duplicadas"):
        scope_cross_branch_behaviors(behaviors, duplicated_review)


def test_omitted_product_remains_primary_and_overlap_is_not_double_counted() -> None:
    review = _review([10, 10, 10, 0], [10, 10, 10, 10])
    behaviors = detect_cross_branch_order_anomalies(review)
    omitted = behaviors.iloc[0]
    primary_alerts = pd.DataFrame(
        {
            "sucursal": [omitted["sucursal"]],
            "ingrediente_id": [omitted["ingrediente_id"]],
        }
    )

    summary = summarize_attention_overlap(primary_alerts, behaviors)

    assert omitted["diagnostico_principal"] == "Producto omitido"
    assert omitted["mensaje"].startswith("PRODUCTO OMITIDO:")
    assert "Contexto secundario" in omitted["mensaje"]
    assert summary["alertas_principales"] == 1
    assert summary["comportamientos_inusuales"] == 1
    assert summary["superposicion"] == 1
    assert summary["lineas_unicas"] == 1


def test_original_data_produces_unique_moderate_confidence_cases() -> None:
    bundle = load_data(Path("datos"))
    validated = validate_data(
        bundle.catalogo,
        bundle.historico,
        bundle.inventario,
        bundle.orden,
    )
    forecasts, _ = forecast_all(validated.historico, validated.combinaciones)
    review = build_purchase_review(validated, forecasts)

    behaviors = detect_cross_branch_order_anomalies(
        review,
        catalog_ingredient_ids=validated.catalogo["ingrediente_id"],
    )
    cases = set(zip(behaviors["sucursal"], behaviors["ingrediente"]))

    assert len(behaviors) == 4
    assert not behaviors.duplicated(["sucursal", "ingrediente_id"]).any()
    assert set(behaviors["nivel_confianza"]) == {"Moderada"}
    assert ("Brisas del Golf", "Mozzarella") in cases
    assert ("Costa del Este", "Harina 00") in cases
    assert ("Brisas del Golf", "Cebolla blanca") in cases
    assert ("Via Argentina", "Albahaca fresca") in cases


def test_local_assistant_uses_cautious_terminology() -> None:
    review = _review([10, 10, 10, 30], [10, 10, 10, 10])
    behaviors = detect_cross_branch_order_anomalies(review)

    answer = answer_local_question(
        "¿Qué comportamientos inusuales hay entre sucursales?",
        review,
        pd.DataFrame(),
        pd.DataFrame(columns=["nivel"]),
        pd.DataFrame(),
        behaviors,
    )

    assert "1 comportamiento inusual" in answer
    assert "Sucursal nueva 4" in answer
    assert "confianza moderada" in answer
