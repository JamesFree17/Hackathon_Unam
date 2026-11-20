"""Estadística de decisión: tendencias del rival con suavizado y valor esperado de jugadas.

Todo son tablas de frecuencias en pandas, sin ML. Cuando un equipo tiene pocas jugadas
en una situación, su estimación se acerca al promedio de la liga (suavizado bayesiano):
    p = (conteo_equipo + k * p_liga) / (n_equipo + k)
"""
from functools import lru_cache

import numpy as np
import pandas as pd

from . import datos, extraccion, plantilla

DISTANCIAS = ["corta", "media", "larga"]
ZONAS = ["propia", "medio", "ofensiva", "roja"]
# Éxito de una jugada: yardas >= fracción de la distancia necesaria (1.º, 2.º, 3.º y 4.º down).
FRACCION_EXITO = {1: 0.4, 2: 0.6, 3: 1.0}


def clasificar_distancia(yardas_a_primero: float) -> str:
    return "corta" if yardas_a_primero <= 3 else "media" if yardas_a_primero <= 7 else "larga"


def clasificar_zona(yardas_a_meta: float) -> str:
    if yardas_a_meta > 80:
        return "propia"
    if yardas_a_meta > 40:
        return "medio"
    return "ofensiva" if yardas_a_meta > 20 else "roja"


def confianza(n: int) -> str:
    return "alta" if n >= 25 else "media" if n >= 10 else "baja"


@lru_cache(maxsize=1)
def base() -> pd.DataFrame:
    """Jugadas de pase válidas (sin anuladas) con situación, éxito y objetivo identificado."""
    p = datos.presion_por_jugada().copy()
    p = pd.concat([p, extraccion.extraer(p)], axis=1)
    p = p[p["down"].between(1, 4) & ~p["sin_jugada"] & (p["yardsToGo"] > 0)].copy()

    p["presion"] = p["presion"].astype(bool)
    p["down_g"] = p["down"].clip(upper=3).astype(int)
    p["dist"] = p["yardsToGo"].map(clasificar_distancia)
    p["zona"] = p["yardas_meta"].map(clasificar_zona)
    frac = p["down_g"].map(FRACCION_EXITO)
    p["sack"] = p["passResult"] == "S"
    p["intercepcion"] = p["passResult"] == "IN"
    p["exito"] = (p["playResult"] >= frac * p["yardsToGo"]) & ~p["intercepcion"]
    p["cobertura"] = p["pff_passCoverage"]
    p["tipo_cob"] = p["pff_passCoverageType"]
    p["formacion"] = p["offenseFormation"]
    p["pa"] = p["pff_playAction"].fillna(0).astype(int)
    p["opcion"] = p["formacion"].astype(str) + "|" + p["pa"].astype(str)

    mapa = plantilla.llave_a_id()
    llaves = p["objetivo"].map(extraccion.llave_abreviado)
    p["objetivo_id"] = [mapa.get((t, k)) if k else None for t, k in zip(p["possessionTeam"], llaves)]
    p["objetivo_id"] = p["objetivo_id"].astype("Float64")
    return p.reset_index(drop=True)


def _ordenar(probs: dict, top: int | None = None) -> list[dict]:
    items = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
    if top:
        items = items[:top]
    return [{"nombre": str(k), "prob": round(float(v), 3)} for k, v in items]


def probabilidades(col: str, rol_equipo: str, equipo: str, down: int, dist: str, zona: str, k: float = 20) -> dict:
    """Distribución de `col` para `equipo` (como `possessionTeam` o `defensiveTeam`) en la situación.

    La liga es el prior (con zona si hay jugadas suficientes) y el equipo la ajusta.
    """
    b = base()
    dg = min(down, 3)
    liga = b[(b["down_g"] == dg) & (b["dist"] == dist)]
    liga_zona = liga[liga["zona"] == zona]
    if len(liga_zona) >= 200:
        liga = liga_zona
    eq = b[(b[rol_equipo] == equipo) & (b["down_g"] == dg) & (b["dist"] == dist)]
    prior = liga[col].dropna().value_counts(normalize=True)
    cuenta = eq[col].dropna().value_counts()
    n = int(cuenta.sum())
    cats = prior.index.union(cuenta.index)
    probs = {c: (cuenta.get(c, 0) + k * prior.get(c, 0.0)) / (n + k) for c in cats}
    return {"probs": probs, "muestra": n, "muestra_liga": int(len(liga)), "confianza": confianza(n)}


def cobertura_esperada(rival: str, down: int, dist: str, zona: str) -> dict:
    cob = probabilidades("cobertura", "defensiveTeam", rival, down, dist, zona)
    tipo = probabilidades("tipo_cob", "defensiveTeam", rival, down, dist, zona)
    return {
        "coberturas": _ordenar(cob["probs"], 5),
        "tipos": _ordenar(tipo["probs"]),
        "muestra": cob["muestra"],
        "confianza": cob["confianza"],
        "_cob": cob["probs"],
        "_tipo": tipo["probs"],
    }


def formacion_esperada(rival: str, down: int, dist: str, zona: str) -> dict:
    f = probabilidades("formacion", "possessionTeam", rival, down, dist, zona)
    return {
        "formaciones": _ordenar(f["probs"], 4),
        "muestra": f["muestra"],
        "confianza": f["confianza"],
        "_f": f["probs"],
    }


def _suav(suma: float, n: float, prior: float, m: float) -> float:
    return (suma + m * prior) / (n + m)


def opciones_ataque(dist: str, probs_cob: dict, m: float = 15, min_n: int = 40, top: int = 3) -> list[dict]:
    """Mejores (formación, play action) esperados contra la cobertura probable del rival."""
    b = base()
    s = b[(b["dist"] == dist) & b["formacion"].notna()]
    campos = {"e": "exito", "y": "playResult", "sk": "sack", "it": "intercepcion"}
    agg = {"n": ("exito", "size")} | {k: (v, "sum") for k, v in campos.items()}
    por_cob = s.groupby(["opcion", "cobertura"]).agg(**agg)
    total = s.groupby("opcion").agg(**agg)
    peso = sum(probs_cob.values()) or 1.0
    out = []
    for op, t in total.iterrows():
        if t["n"] < min_n:
            continue
        prior = {k: t[k] / t["n"] for k in campos}
        acc = dict.fromkeys(campos, 0.0)
        for cob, pc in probs_cob.items():
            fila = por_cob.loc[(op, cob)] if (op, cob) in por_cob.index else None
            n = float(fila["n"]) if fila is not None else 0.0
            for k in campos:
                suma = float(fila[k]) if fila is not None else 0.0
                acc[k] += (pc / peso) * _suav(suma, n, prior[k], m)
        formacion, pa = op.split("|")
        out.append(
            {
                "formacion": formacion,
                "play_action": pa == "1",
                "exito": round(acc["e"], 3),
                "yardas": round(acc["y"], 1),
                "riesgo_sack": round(acc["sk"], 3),
                "riesgo_int": round(acc["it"], 3),
                "muestra": int(t["n"]),
                # Premia el éxito y penaliza intercepciones y sacks.
                "puntuacion": round(acc["e"] - acc["it"] - 0.5 * acc["sk"], 3),
            }
        )
    return sorted(out, key=lambda r: r["puntuacion"], reverse=True)[:top]


def presion_de_defensa(equipo: str, dist: str, k: float = 20) -> dict:
    """Presión y sacks que genera una defensa en esa distancia, suavizada con la liga."""
    b = base()
    liga = b[b["dist"] == dist]
    eq = liga[liga["defensiveTeam"] == equipo]
    n = len(eq)
    return {
        "tasa_presion": round(_suav(eq["presion"].sum(), n, liga["presion"].mean(), k), 3),
        "tasa_sack": round(_suav(eq["sack"].sum(), n, liga["sack"].mean(), k), 3),
        "muestra": int(n),
        "confianza": confianza(n),
    }


def _zona_preferida(sub: pd.DataFrame) -> dict | None:
    z = sub.dropna(subset=["profundidad", "lado"])
    if len(z) < 3:
        return None
    g = z.groupby(["profundidad", "lado"]).agg(n=("exito", "size"), e=("exito", "mean")).reset_index()
    r = g.sort_values(["n", "e"], ascending=False).iloc[0]
    return {"profundidad": r["profundidad"], "lado": r["lado"], "muestra": int(r["n"]), "exito": round(float(r["e"]), 3)}


def receptores(equipo: str, probs_tipo: dict | None = None, m: float = 10) -> pd.DataFrame:
    """Métricas por receptor del equipo (por nflId). La puntuación pondera el éxito vs. cada tipo de cobertura."""
    b = base()
    t = b[(b["possessionTeam"] == equipo) & b["objetivo_id"].notna()]
    if t.empty:
        return pd.DataFrame(columns=["nflId", "targets", "puntuacion"])
    prior_equipo = t["exito"].mean()
    probs_tipo = probs_tipo or {"Zone": 0.65, "Man": 0.3, "Other": 0.05}
    peso = sum(probs_tipo.values()) or 1.0
    filas = []
    for pid, g in t.groupby("objetivo_id"):
        n, s = len(g), g["exito"].sum()
        general = _suav(s, n, prior_equipo, m)
        punt = 0.0
        for tipo, pt in probs_tipo.items():
            gt = g[g["tipo_cob"] == tipo]
            punt += (pt / peso) * _suav(gt["exito"].sum(), len(gt), general, m)
        comp = g[g["passResult"] == "C"]
        filas.append(
            {
                "nflId": int(pid),
                "targets": int(n),
                "completos": int(len(comp)),
                "yardas": float(comp["playResult"].sum()),
                "yardas_por_target": round(float(comp["playResult"].sum() / n), 1),
                "tds": int(g["td_ofensivo"].sum()),
                "ints": int(g["intercepcion"].sum()),
                "exito": round(float(g["exito"].mean()), 3),
                "puntuacion": round(punt, 3),
                "zona_preferida": _zona_preferida(g),
                "share": round(n / len(t), 3),
            }
        )
    return pd.DataFrame(filas)


def opciones_defensa(equipo_def: str, dist: str, zona: str, probs_form: dict, m: float = 15, m_equipo: float = 15,
                     min_n: int = 30, top: int = 3) -> list[dict]:
    """Coberturas que mejor contienen al ataque rival, mezclando la liga con los resultados propios."""
    b = base()
    s = b[(b["dist"] == dist) & b["formacion"].notna()]
    excluir = {"Miscellaneous", "Prevent"}
    if zona != "roja":
        excluir |= {"Red Zone", "Goal Line", "Bracket"}
    s = s[~s["cobertura"].isin(excluir)]
    campos = {"e": "exito", "y": "playResult", "sk": "sack", "it": "intercepcion", "pr": "presion"}
    agg = {"n": ("exito", "size")} | {k: (v, "sum") for k, v in campos.items()}
    por_cf = s.groupby(["cobertura", "formacion"]).agg(**agg)
    total = s.groupby("cobertura").agg(**agg)
    propio = b[b["defensiveTeam"] == equipo_def].groupby("cobertura").agg(**agg)
    peso = sum(probs_form.values()) or 1.0
    out = []
    for cob, t in total.iterrows():
        if t["n"] < min_n:
            continue
        prior = {k: t[k] / t["n"] for k in campos}
        est = dict.fromkeys(campos, 0.0)
        for f, pf in probs_form.items():
            fila = por_cf.loc[(cob, f)] if (cob, f) in por_cf.index else None
            n = float(fila["n"]) if fila is not None else 0.0
            for k in campos:
                suma = float(fila[k]) if fila is not None else 0.0
                est[k] += (pf / peso) * _suav(suma, n, prior[k], m)
        if cob in propio.index:
            p = propio.loc[cob]
            est = {k: _suav(float(p[k]), float(p["n"]), est[k], m_equipo) for k in campos}
            usos = int(p["n"])
        else:
            usos = 0
        out.append(
            {
                "cobertura": cob,
                "exito_permitido": round(est["e"], 3),
                "yardas_permitidas": round(est["y"], 1),
                "presion": round(est["pr"], 3),
                "sacks": round(est["sk"], 3),
                "intercepciones": round(est["it"], 3),
                "muestra": int(t["n"]),
                "usos_propios": usos,
                # Premia frenar el éxito y generar presión, sacks e intercepciones.
                "puntuacion": round(-est["e"] + est["it"] + 0.5 * est["sk"] + 0.25 * est["pr"], 3),
            }
        )
    return sorted(out, key=lambda r: r["puntuacion"], reverse=True)[:top]


def zonas_rival(rival: str, down: int, dist: str, k: float = 15) -> dict:
    """Hacia dónde tira el ataque rival (profundidad y lado), suavizado con la liga."""
    b = base()
    b = b.dropna(subset=["profundidad", "lado"]).copy()
    b["zona_pase"] = b["profundidad"] + " " + b["lado"]
    dg = min(down, 3)
    liga = b[(b["down_g"] == dg) & (b["dist"] == dist)]
    eq = liga[liga["possessionTeam"] == rival]
    prior = liga["zona_pase"].value_counts(normalize=True)
    cuenta = eq["zona_pase"].value_counts()
    n = int(cuenta.sum())
    probs = {c: (cuenta.get(c, 0) + k * prior.get(c, 0.0)) / (n + k) for c in prior.index.union(cuenta.index)}
    return {"zonas": _ordenar(probs, 3), "muestra": n, "confianza": confianza(n)}


def perfil_equipo(equipo: str) -> dict:
    """Resumen general de un equipo para el reporte previo al partido."""
    b = base()
    ata = b[b["possessionTeam"] == equipo]
    de = b[b["defensiveTeam"] == equipo]
    liga = b
    return {
        "equipo": equipo,
        "ataque": {
            "jugadas": int(len(ata)),
            "exito": round(float(ata["exito"].mean()), 3),
            "exito_liga": round(float(liga["exito"].mean()), 3),
            "sack_sufridos": round(float(ata["sack"].mean()), 3),
            "formaciones": _ordenar(ata["formacion"].value_counts(normalize=True).to_dict(), 3),
            "play_action": round(float(ata["pa"].mean()), 3),
        },
        "defensa": {
            "jugadas": int(len(de)),
            "exito_permitido": round(float(de["exito"].mean()), 3),
            "presion": round(float(de["presion"].mean()), 3),
            "presion_liga": round(float(liga["presion"].mean()), 3),
            "coberturas": _ordenar(de["cobertura"].value_counts(normalize=True).to_dict(), 4),
        },
    }
