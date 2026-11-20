"""Recomendaciones de Ataque y Defensa que combinan el modelo estadístico con la alineación del coach."""
import math

import numpy as np
import pandas as pd

from . import modelo, plantilla

MIN_TARGETS = 8          # mínimo de objetivos para recomendar a un receptor
MIN_SNAPS_RUSH = 30      # mínimo de jugadas de pass rush para comparar presión
MEJORA_MIN_ATAQUE = 0.04  # diferencia de puntuación para sugerir una sustitución
MEJORA_MIN_PRESION = 0.03


def limpiar(o):
    """Convierte tipos de numpy/NaN a valores JSON y quita claves privadas (_x)."""
    if isinstance(o, dict):
        return {k: limpiar(v) for k, v in o.items() if not str(k).startswith("_")}
    if isinstance(o, (list, tuple)):
        return [limpiar(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if math.isnan(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if o is pd.NA:
        return None
    return o


def _situacion(down: int, distancia: str, zona: str) -> dict:
    return {"down": down, "distancia": distancia, "zona": zona}


def _persona(r) -> dict:
    return {"nflId": int(r["nflId"]), "nombre": r["displayName"], "grupo": r["grupo"], "posicion": r["alineacion"]}


# ---------- Plantilla ----------

def plantilla_con_metricas(equipo: str, lado: str) -> list[dict]:
    p = plantilla.plantilla(equipo, lado)
    if lado == "ataque":
        r = modelo.receptores(equipo)
        p = p.merge(r, on="nflId", how="left")
        p["targets"] = p["targets"].fillna(0)
    else:
        p["tasa_presion"] = np.where(p["snaps_rush"] >= MIN_SNAPS_RUSH, p["presiones"] / p["snaps_rush"].clip(lower=1), np.nan)
    cols = ["nflId", "displayName", "grupo", "alineacion", "jugadas", "titular_sugerido", "height", "weight"]
    extra = ["targets", "exito", "yardas_por_target", "tds"] if lado == "ataque" else ["snaps_rush", "presiones", "sacks", "tasa_presion"]
    return limpiar(p[cols + extra].rename(columns={"displayName": "nombre", "alineacion": "posicion"}).to_dict("records"))


# ---------- Ataque ----------

def _evaluar_banca(df: pd.DataFrame, titulares: set, banca: set, grupos: list[str], col: str, minimo: float,
                   mejora_min: float, minimo_col: str) -> list[dict]:
    """Compara al mejor jugador de la banca con el titular más débil de cada grupo."""
    out = []
    for g in grupos:
        sub = df[(df["grupo"] == g) & (df[minimo_col] >= minimo) & df[col].notna()]
        tit = sub[sub["nflId"].isin(titulares)]
        ban = sub[sub["nflId"].isin(banca)]
        if tit.empty or ban.empty:
            continue
        sale = tit.sort_values(col).iloc[0]
        entra = ban.sort_values(col, ascending=False).iloc[0]
        mejora = float(entra[col] - sale[col])
        if mejora >= mejora_min:
            out.append({"grupo": g, "entra": _persona(entra) | {col: round(float(entra[col]), 3)},
                        "sale": _persona(sale) | {col: round(float(sale[col]), 3)}, "mejora": round(mejora, 3)})
    return out


def recomendar_ataque(equipo: str, rival: str, down: int, distancia: str, zona: str,
                      titulares: list[int], banca: list[int]) -> dict:
    ce = modelo.cobertura_esperada(rival, down, distancia, zona)
    jugadas = modelo.opciones_ataque(distancia, ce["_cob"])

    p = plantilla.plantilla(equipo, "ataque").merge(modelo.receptores(equipo, ce["_tipo"]), on="nflId", how="left")
    p["targets"] = p["targets"].fillna(0)
    tit, ban = set(titulares), set(banca)

    elegibles = p[p["nflId"].isin(tit) & (p["targets"] >= MIN_TARGETS) & p["grupo"].isin(["WR", "TE", "RB"])]
    objetivos = []
    for _, r in elegibles.sort_values("puntuacion", ascending=False).head(3).iterrows():
        objetivos.append(
            _persona(r)
            | {
                "targets": int(r["targets"]),
                "exito": r["exito"],
                "yardas_por_target": r["yardas_por_target"],
                "tds": int(r["tds"]),
                "ints": int(r["ints"]),
                "puntuacion": r["puntuacion"],
                "zona_preferida": r["zona_preferida"] if isinstance(r["zona_preferida"], dict) else None,
                "confianza": modelo.confianza(int(r["targets"])),
            }
        )
    sustituciones = _evaluar_banca(p, tit, ban, ["WR", "TE", "RB"], "puntuacion", MIN_TARGETS, MEJORA_MIN_ATAQUE, "targets")

    return limpiar(
        {
            "lado": "ataque",
            "equipo": equipo,
            "rival": rival,
            "situacion": _situacion(down, distancia, zona),
            "cobertura_esperada": {k: ce[k] for k in ("coberturas", "tipos", "muestra", "confianza")},
            "jugadas": jugadas,
            "objetivos": objetivos,
            "sustituciones": sustituciones,
            "presion_rival": modelo.presion_de_defensa(rival, distancia),
            "aviso": None if objetivos else "No hay titulares con objetivos suficientes en los datos; revisa la alineación.",
        }
    )


# ---------- Defensa ----------

def recomendar_defensa(equipo: str, rival: str, down: int, distancia: str, zona: str,
                       titulares: list[int], banca: list[int]) -> dict:
    fe = modelo.formacion_esperada(rival, down, distancia, zona)
    coberturas = modelo.opciones_defensa(equipo, distancia, zona, fe["_f"])
    zr = modelo.zonas_rival(rival, down, distancia)

    rp = plantilla.plantilla(rival, "ataque").merge(modelo.receptores(rival), on="nflId", how="left")
    rp["targets"] = rp["targets"].fillna(0)
    rp = rp[(rp["targets"] >= MIN_TARGETS) & rp["grupo"].isin(["WR", "TE", "RB"])].copy()
    rp["amenaza"] = rp["share"] * rp["puntuacion"]
    amenazas = []
    for _, r in rp.sort_values("amenaza", ascending=False).head(4).iterrows():
        amenazas.append(
            _persona(r)
            | {
                "targets": int(r["targets"]),
                "porcentaje_targets": r["share"],
                "exito": r["exito"],
                "yardas_por_target": r["yardas_por_target"],
                "tds": int(r["tds"]),
                "zona_preferida": r["zona_preferida"] if isinstance(r["zona_preferida"], dict) else None,
                "confianza": modelo.confianza(int(r["targets"])),
            }
        )

    mia = plantilla.plantilla(equipo, "defensa")
    mia["tasa_presion"] = np.where(mia["snaps_rush"] >= MIN_SNAPS_RUSH, mia["presiones"] / mia["snaps_rush"].clip(lower=1), np.nan)
    tit, ban = set(titulares), set(banca)
    rushers = mia[mia["nflId"].isin(tit) & mia["tasa_presion"].notna()].sort_values("tasa_presion", ascending=False)
    mejores = [
        _persona(r) | {"tasa_presion": round(float(r["tasa_presion"]), 3), "sacks": int(r["sacks"]), "snaps": int(r["snaps_rush"])}
        for _, r in rushers.head(3).iterrows()
    ]
    sustituciones = _evaluar_banca(mia, tit, ban, ["DL", "LB"], "tasa_presion", MIN_SNAPS_RUSH, MEJORA_MIN_PRESION, "snaps_rush")

    return limpiar(
        {
            "lado": "defensa",
            "equipo": equipo,
            "rival": rival,
            "situacion": _situacion(down, distancia, zona),
            "formacion_esperada": {k: fe[k] for k in ("formaciones", "muestra", "confianza")},
            "coberturas": coberturas,
            "zonas_rival": zr,
            "cubrir": amenazas,
            "presionadores": mejores,
            "sustituciones": sustituciones,
            "aviso": "La sustitución solo compara presión (DL y LB); los datos no miden la calidad individual de cobertura.",
        }
    )


# ---------- Texto de respaldo (se usa si la IA no está disponible) ----------

def _pct(x) -> str:
    return f"{round(x * 100)}%"


def texto_respaldo(rec: dict) -> str:
    s = rec["situacion"]
    inicio = f"{s['down']}.º down, distancia {s['distancia']}, zona {s['zona']}."
    if rec["lado"] == "ataque":
        partes = [inicio]
        cob = rec["cobertura_esperada"]["coberturas"]
        if cob:
            partes.append(f"{rec['rival']} probablemente use {cob[0]['nombre']} ({_pct(cob[0]['prob'])}).")
        if rec["jugadas"]:
            j = rec["jugadas"][0]
            pa = "con play action" if j["play_action"] else "sin play action"
            partes.append(f"Mejor opción: {j['formacion']} {pa}, éxito esperado {_pct(j['exito'])}.")
        if rec["objetivos"]:
            o = rec["objetivos"][0]
            zona = ""
            if o["zona_preferida"]:
                zp = o["zona_preferida"]
                zona = f", sobre todo {zp['profundidad']} {zp['lado']}"
            partes.append(f"Busca a {o['nombre']} ({o['targets']} objetivos, {_pct(o['exito'])} de éxito{zona}).")
        for sub in rec["sustituciones"][:1]:
            partes.append(f"Considera meter a {sub['entra']['nombre']} por {sub['sale']['nombre']} ({sub['grupo']}).")
        return " ".join(partes)
    partes = [inicio]
    f = rec["formacion_esperada"]["formaciones"]
    if f:
        partes.append(f"{rec['rival']} suele usar {f[0]['nombre']} ({_pct(f[0]['prob'])}).")
    if rec["coberturas"]:
        c = rec["coberturas"][0]
        partes.append(f"Cobertura recomendada: {c['cobertura']}, permite {_pct(c['exito_permitido'])} de éxito.")
    if rec["cubrir"]:
        nombres = ", ".join(a["nombre"] for a in rec["cubrir"][:2])
        partes.append(f"Prioriza cubrir a {nombres}.")
    for sub in rec["sustituciones"][:1]:
        partes.append(f"Mete a {sub['entra']['nombre']} por {sub['sale']['nombre']} para más presión ({sub['grupo']}).")
    return " ".join(partes)
