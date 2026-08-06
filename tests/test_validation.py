"""Pruebas de esquema, integridad y calidad de datos."""

from __future__ import annotations

import pandas as pd

from src.validation import validate_data


def issue_codes(result: object) -> set[str]:
    return set(result.incidencias["codigo"].astype(str))


def test_missing_required_column_is_reported(minimal_frames: tuple[pd.DataFrame, ...]) -> None:
    catalog, historical, inventory, order = minimal_frames
    result = validate_data(catalog, historical, inventory, order.drop(columns="cantidad_formatos"))
    assert "COLUMNA_AUSENTE" in issue_codes(result)
    assert result.has_blocking_schema_errors


def test_null_negative_duplicate_and_fractional_values_are_reported(
    minimal_frames: tuple[pd.DataFrame, ...]
) -> None:
    catalog, historical, inventory, order = minimal_frames
    problematic = pd.concat([order, order], ignore_index=True).astype(
        {"cantidad_formatos": "object"}
    )
    problematic.loc[0, "cantidad_formatos"] = -1.5
    result = validate_data(catalog, historical, inventory, problematic)
    codes = issue_codes(result)
    assert "CANTIDAD_NEGATIVA" in codes
    assert "FORMATO_NO_ENTERO" in codes
    assert "CLAVE_DUPLICADA" in codes


def test_unknown_ingredient_is_not_enriched(minimal_frames: tuple[pd.DataFrame, ...]) -> None:
    catalog, historical, inventory, order = minimal_frames
    unknown = pd.DataFrame(
        [{"sucursal": "Sucursal nueva", "ingrediente_id": "fantasma", "cantidad_formatos": 3}]
    )
    result = validate_data(catalog, historical, inventory, pd.concat([order, unknown]))
    unknown_issues = result.incidencias[
        result.incidencias["codigo"] == "INGREDIENTE_DESCONOCIDO"
    ]
    assert len(unknown_issues) == 1
    assert unknown_issues.iloc[0]["ingrediente_id"] == "fantasma"


def test_incomplete_history_is_reported(minimal_frames: tuple[pd.DataFrame, ...]) -> None:
    catalog, historical, inventory, order = minimal_frames
    result = validate_data(catalog, historical.iloc[:2], inventory, order)
    assert "HISTORICO_INCOMPLETO" in issue_codes(result)


def test_duplicate_week_is_reported(minimal_frames: tuple[pd.DataFrame, ...]) -> None:
    catalog, historical, inventory, order = minimal_frames
    duplicated = pd.concat([historical, historical.iloc[[0]]], ignore_index=True)
    result = validate_data(catalog, duplicated, inventory, order)
    assert "SEMANA_DUPLICADA" in issue_codes(result)


def test_non_numeric_history_is_reported(minimal_frames: tuple[pd.DataFrame, ...]) -> None:
    catalog, historical, inventory, order = minimal_frames
    historical = historical.astype({"consumo_unidad_base": "object"})
    historical.loc[0, "consumo_unidad_base"] = "sin dato"
    result = validate_data(catalog, historical, inventory, order)
    assert "VALOR_NO_NUMERICO" in issue_codes(result)
    assert "HISTORICO_INCOMPLETO" in issue_codes(result)
