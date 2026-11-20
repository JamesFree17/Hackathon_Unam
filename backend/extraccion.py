"""Extracción de pasador, objetivo, zona y touchdown desde `playDescription`."""
import re

import numpy as np
import pandas as pd

# Nombre abreviado de la NFL: "T.Brady", "A.St. Brown", "J.Smith-Schuster", "M.Pittman Jr."
NOMBRE = r"[A-Z]\.(?:St\.\s)?[A-Za-z'\-]+(?:\s(?:Jr|Sr|II|III|IV)\b\.?)?"

RE_PASADOR = re.compile(rf"^(?:\([^)]*\)\s*)*({NOMBRE}) (?:pass|sacked|scrambles|is sacked)")
RE_OBJETIVO = re.compile(rf" (?:to|intended for) ({NOMBRE})(?=[\s.,]|$)")
RE_ZONA = re.compile(r"\bpass (?:incomplete )?(short|deep) (left|middle|right)\b")

SUFIJOS = {"jr", "sr", "ii", "iii", "iv", "v"}


def _limpia(texto: str) -> str:
    return re.sub(r"[^a-z]", "", texto.lower())


def llave_abreviado(abreviado: str | None) -> str | None:
    """'A.St. Brown' -> 'a|stbrown'. Misma llave que `llave_nombre_completo`."""
    if not isinstance(abreviado, str) or "." not in abreviado:
        return None
    inicial, apellido = abreviado.split(".", 1)
    partes = [t for t in apellido.split() if _limpia(t) not in SUFIJOS]
    ap = _limpia("".join(partes))
    return f"{inicial.lower()}|{ap}" if inicial and ap else None


def llave_nombre_completo(nombre: str | None) -> str | None:
    """'Amon-Ra St. Brown' -> 'a|stbrown'. Ignora sufijos (Jr., III)."""
    if not isinstance(nombre, str):
        return None
    tokens = nombre.split()
    if len(tokens) < 2:
        return None
    resto = [t for t in tokens[1:] if _limpia(t) not in SUFIJOS]
    ap = _limpia("".join(resto))
    return f"{tokens[0][0].lower()}|{ap}" if ap else None


def extraer(plays: pd.DataFrame) -> pd.DataFrame:
    """Devuelve columnas derivadas, con el mismo índice que `plays`."""
    d = plays["playDescription"].fillna("")
    es_pase = plays["passResult"].isin(["C", "I", "IN"])

    pasador = d.str.extract(RE_PASADOR)[0]
    objetivo = d.str.extract(RE_OBJETIVO)[0].where(es_pase)
    zona = d.str.extract(RE_ZONA)

    sin_jugada = d.str.contains("No Play", regex=False) | d.str.contains("NULLIFIED", regex=False)
    td = (
        d.str.contains("TOUCHDOWN", regex=False)
        & (plays["passResult"] == "C")
        & ~sin_jugada
    )

    # Yardas a la meta del equipo ofensivo (50 si está en medio campo).
    yl = plays["yardlineNumber"]
    propia = plays["yardlineSide"] == plays["possessionTeam"]
    yardas_meta = np.where(plays["yardlineSide"].isna(), 50, np.where(propia, 100 - yl, yl))

    return pd.DataFrame(
        {
            "pasador": pasador,
            "objetivo": objetivo,
            "profundidad": zona[0].where(es_pase),
            "lado": zona[1].where(es_pase),
            "td_ofensivo": td,
            "sin_jugada": sin_jugada,
            "yardas_meta": yardas_meta,
        },
        index=plays.index,
    )
