"""Carga de datos (solo lectura) y agregados base. Todo se calcula en memoria."""
from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
NA = ["NA"]


@lru_cache(maxsize=1)
def juegos() -> pd.DataFrame:
    return pd.read_csv(DATA / "games.csv", na_values=NA)


@lru_cache(maxsize=1)
def jugadas() -> pd.DataFrame:
    return pd.read_csv(DATA / "plays.csv", na_values=NA)


@lru_cache(maxsize=1)
def jugadores() -> pd.DataFrame:
    return pd.read_csv(DATA / "players.csv", na_values=NA)


@lru_cache(maxsize=1)
def pff() -> pd.DataFrame:
    return pd.read_csv(DATA / "pffScoutingData.csv", na_values=NA)


def tracking_juego(game_id: int, columnas: list[str] | None = None) -> pd.DataFrame:
    """Un juego de tracking (~7 MB). No se cachea: el tracking completo pesa ~810 MB."""
    usecols = columnas or ["gameId", "playId", "nflId", "frameId", "team", "x", "y", "s", "a", "event"]
    return pd.read_csv(DATA / "tracking" / f"tracking_{game_id}.csv", usecols=usecols, na_values=NA)


@lru_cache(maxsize=1)
def presion_por_jugada() -> pd.DataFrame:
    """Una fila por jugada con indicador de presión (hit, hurry o sack de PFF)."""
    p = pff()
    cols = ["pff_hit", "pff_hurry", "pff_sack"]
    marcas = p[cols].fillna(0).sum(axis=1) > 0
    por_jugada = marcas.groupby([p["gameId"], p["playId"]]).any().rename("presion").reset_index()
    return jugadas().merge(por_jugada, on=["gameId", "playId"], how="left").fillna({"presion": False})


def _agrupar(col: str) -> list[dict]:
    d = presion_por_jugada()
    g = d.groupby(col).agg(
        jugadas=("playId", "size"),
        tasa_presion=("presion", "mean"),
        tasa_sack=("passResult", lambda s: (s == "S").mean()),
        yardas_promedio=("playResult", "mean"),
    )
    g = g[g["jugadas"] >= 30].sort_values("tasa_presion", ascending=False).round(3)
    return g.reset_index().rename(columns={col: "categoria"}).to_dict("records")


def por_cobertura() -> list[dict]:
    return _agrupar("pff_passCoverage")


def por_formacion() -> list[dict]:
    return _agrupar("offenseFormation")


def resumen() -> dict:
    return {
        "juegos": int(len(juegos())),
        "jugadas": int(len(jugadas())),
        "jugadores": int(len(jugadores())),
        "semanas": sorted(int(w) for w in juegos()["week"].unique()),
        "tasa_presion": round(float(presion_por_jugada()["presion"].mean()), 3),
    }
