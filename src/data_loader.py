"""Carga segura de los archivos de entrada del asistente de compras."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, TextIO

import pandas as pd


FILE_NAMES = {
    "catalogo": "ingredientes.csv",
    "historico": "consumo_historico.csv",
    "inventario": "inventario_actual.csv",
    "orden": "orden_compra_semana.csv",
}


@dataclass(frozen=True)
class DataBundle:
    """Agrupa las cuatro fuentes sin aplicar reglas de negocio."""

    catalogo: pd.DataFrame
    historico: pd.DataFrame
    inventario: pd.DataFrame
    orden: pd.DataFrame


def read_csv_source(source: Path | str | BinaryIO | TextIO) -> pd.DataFrame:
    """Lee un CSV conservando nulos y valores inválidos para poder reportarlos."""

    frame = pd.read_csv(source, dtype="object", keep_default_na=True)
    frame.columns = [str(column).strip() for column in frame.columns]
    return frame


def load_data(data_dir: Path | str) -> DataBundle:
    """Carga los cuatro CSV obligatorios desde una ruta relativa o absoluta."""

    directory = Path(data_dir)
    missing_files = [
        filename for filename in FILE_NAMES.values() if not (directory / filename).is_file()
    ]
    if missing_files:
        names = ", ".join(missing_files)
        raise FileNotFoundError(f"No se encontraron los archivos obligatorios: {names}")

    return DataBundle(
        catalogo=read_csv_source(directory / FILE_NAMES["catalogo"]),
        historico=read_csv_source(directory / FILE_NAMES["historico"]),
        inventario=read_csv_source(directory / FILE_NAMES["inventario"]),
        orden=read_csv_source(directory / FILE_NAMES["orden"]),
    )


def read_order_upload(source: BinaryIO | TextIO) -> pd.DataFrame:
    """Lee una orden subida por la usuaria sin mutar las fuentes base."""

    return read_csv_source(source)
