"""Plantilla por equipo reconstruida desde el scouting de PFF (players.csv no trae equipo)."""
from functools import lru_cache

import numpy as np
import pandas as pd

from . import datos, extraccion

ROLES_ATAQUE = {"Pass", "Pass Block", "Pass Route"}

GRUPO_POR_POSICION = {
    "QB": "QB", "RB": "RB", "FB": "RB", "WR": "WR", "TE": "TE",
    "T": "OL", "G": "OL", "C": "OL",
    "DE": "DL", "DT": "DL", "NT": "DL",
    "OLB": "LB", "ILB": "LB", "MLB": "LB", "LB": "LB",
    "CB": "DB", "FS": "DB", "SS": "DB", "DB": "DB",
}
GRUPOS_CLAVE = {"ataque": ["QB", "RB", "WR", "TE"], "defensa": ["DL", "LB", "DB"]}
# Cuántos titulares se sugieren por grupo (según jugadas en el scouting).
TITULARES = {"QB": 1, "RB": 1, "WR": 3, "TE": 1, "DL": 4, "LB": 3, "DB": 4}
MIN_JUGADAS = 15


@lru_cache(maxsize=1)
def _registros() -> pd.DataFrame:
    p = datos.jugadas()[["gameId", "playId", "possessionTeam", "defensiveTeam"]]
    m = datos.pff().merge(p, on=["gameId", "playId"])
    m["lado"] = np.where(m["pff_role"].isin(ROLES_ATAQUE), "ataque", "defensa")
    m["equipo"] = np.where(m["lado"] == "ataque", m["possessionTeam"], m["defensiveTeam"])
    return m


def _modo(s: pd.Series):
    m = s.dropna().mode()
    return m.iat[0] if len(m) else None


@lru_cache(maxsize=1)
def tabla_completa() -> pd.DataFrame:
    """Una fila por (equipo, lado, jugador) con jugadas y métricas de PFF."""
    m = _registros().copy()
    for c in ["pff_hit", "pff_hurry", "pff_sack", "pff_sackAllowed", "pff_hurryAllowed", "pff_hitAllowed"]:
        m[c] = m[c].fillna(0)
    m["es_rush"] = m["pff_role"] == "Pass Rush"
    m["es_cob"] = m["pff_role"] == "Coverage"
    g = m.groupby(["equipo", "lado", "nflId"]).agg(
        jugadas=("playId", "size"),
        alineacion=("pff_positionLinedUp", _modo),
        snaps_rush=("es_rush", "sum"),
        snaps_cobertura=("es_cob", "sum"),
        hits=("pff_hit", "sum"),
        hurries=("pff_hurry", "sum"),
        sacks=("pff_sack", "sum"),
    ).reset_index()
    g["presiones"] = g["hits"] + g["hurries"] + g["sacks"]

    jug = datos.jugadores()[["nflId", "displayName", "officialPosition", "height", "weight"]]
    g = g.merge(jug, on="nflId", how="left")
    g["grupo"] = g["officialPosition"].map(GRUPO_POR_POSICION)
    g["llave"] = g["displayName"].map(extraccion.llave_nombre_completo)
    # Solo grupos coherentes con el lado (descarta p. ej. un DB listado como ataque).
    ok = g.apply(lambda r: r["grupo"] in GRUPOS_CLAVE[r["lado"]] or (r["lado"] == "ataque" and r["grupo"] == "OL"), axis=1)
    return g[ok].reset_index(drop=True)


@lru_cache(maxsize=1)
def llave_a_id() -> dict[tuple[str, str], int]:
    """(equipo, 'a|stbrown') -> nflId. Las llaves repetidas en un equipo se descartan."""
    t = tabla_completa()
    t = t[(t["lado"] == "ataque") & t["llave"].notna()]
    cuenta = t.groupby(["equipo", "llave"])["nflId"].nunique()
    unicos = cuenta[cuenta == 1].index
    sel = t.set_index(["equipo", "llave"]).loc[unicos]
    return {k: int(v) for k, v in sel["nflId"].groupby(level=[0, 1]).first().items()}


def ambiguos() -> list[tuple[str, str]]:
    t = tabla_completa()
    t = t[(t["lado"] == "ataque") & t["llave"].notna()]
    cuenta = t.groupby(["equipo", "llave"])["nflId"].nunique()
    return [k for k, v in cuenta.items() if v > 1]


def equipos() -> list[str]:
    return sorted(datos.jugadas()["possessionTeam"].dropna().unique().tolist())


def plantilla(equipo: str, lado: str) -> pd.DataFrame:
    """Jugadores clave del equipo con `titular_sugerido` según jugadas (más jugadas = titular)."""
    t = tabla_completa()
    t = t[(t["equipo"] == equipo) & (t["lado"] == lado) & t["grupo"].isin(GRUPOS_CLAVE[lado])]
    t = t[t["jugadas"] >= MIN_JUGADAS].sort_values(["grupo", "jugadas"], ascending=[True, False]).copy()
    t["orden"] = t.groupby("grupo").cumcount()
    t["titular_sugerido"] = t.apply(lambda r: r["orden"] < TITULARES[r["grupo"]], axis=1)
    return t.drop(columns=["orden"]).reset_index(drop=True)
