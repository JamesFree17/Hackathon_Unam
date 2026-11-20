"""Validación fuera de muestra: entrena con las semanas 1-6 y evalúa en las semanas 7-8.

Responde dos preguntas con datos que el modelo no vio:
  1. ¿Predecir la cobertura del rival con su historial (suavizado) supera a usar solo la liga?
  2. ¿Las jugadas que el modelo recomienda tienen más éxito que las demás?
"""
import math
import threading

import numpy as np

from . import modelo

SEMANAS_ENTRENO = range(1, 7)
SEMANAS_PRUEBA = (7, 8)
EPS = 1e-3  # piso de probabilidad para el log-loss
KS = [2, 5, 10, 20, 40, 80]


def _top(probs: dict, n: int) -> list:
    return [c for c, _ in sorted(probs.items(), key=lambda kv: kv[1], reverse=True)[:n]]


def _evaluar_cobertura(train, test, k: float, solo_liga: bool = False) -> dict:
    memo: dict = {}
    aciertos1 = aciertos3 = 0
    logloss = 0.0
    for r in test.itertuples():
        equipo = "__liga__" if solo_liga else r.defensiveTeam
        clave = (equipo, r.down_g, r.dist, r.zona)
        if clave not in memo:
            memo[clave] = modelo.probabilidades("cobertura", "defensiveTeam", equipo, r.down_g, r.dist, r.zona, k, train)["probs"]
        p = memo[clave]
        real = r.cobertura
        aciertos1 += real == _top(p, 1)[0]
        aciertos3 += real in _top(p, 3)
        logloss += -math.log(max(p.get(real, 0.0), EPS))
    n = len(test)
    return {"top1": round(aciertos1 / n, 3), "top3": round(aciertos3 / n, 3), "log_loss": round(logloss / n, 3)}


def _evaluar_global(train, test) -> dict:
    p = train["cobertura"].value_counts(normalize=True).to_dict()
    top1, top3 = _top(p, 1)[0], _top(p, 3)
    logloss = float(np.mean([-math.log(max(p.get(c, 0.0), EPS)) for c in test["cobertura"]]))
    return {
        "top1": round(float((test["cobertura"] == top1).mean()), 3),
        "top3": round(float(test["cobertura"].isin(top3).mean()), 3),
        "log_loss": round(logloss, 3),
    }


def _evaluar_recomendacion(train, test) -> dict:
    """Compara el éxito de las jugadas que coinciden con el top 3 recomendado frente al resto."""
    memo: dict = {}
    coincide = []
    for r in test.itertuples():
        clave = (r.defensiveTeam, r.down_g, r.dist, r.zona)
        if clave not in memo:
            cob = modelo.cobertura_esperada(r.defensiveTeam, r.down_g, r.dist, r.zona, b=train)["_cob"]
            ops = modelo.opciones_ataque(r.dist, cob, b=train)
            memo[clave] = {(o["formacion"], int(o["play_action"])) for o in ops}
        coincide.append((r.formacion, int(r.pa)) in memo[clave])
    t = test.assign(coincide=coincide)
    a, b = t[t["coincide"]], t[~t["coincide"]]
    pa, pb = float(a["exito"].mean()), float(b["exito"].mean())
    # Intervalo de confianza del 95% para la diferencia de proporciones (aprox. normal).
    se = math.sqrt(pa * (1 - pa) / len(a) + pb * (1 - pb) / len(b))
    dif = pa - pb
    return {
        "jugadas_que_coinciden": int(len(a)),
        "jugadas_que_no": int(len(b)),
        "exito_coinciden": round(pa, 3),
        "exito_no": round(pb, 3),
        "diferencia": round(dif, 3),
        "ic95": [round(dif - 1.96 * se, 3), round(dif + 1.96 * se, 3)],
    }


_ESTADO: dict = {"estado": "pendiente", "resultado": None}
_LOCK = threading.Lock()


def iniciar() -> None:
    """Calcula la validación en un hilo (tarda ~1 min) sin bloquear el arranque ni las peticiones."""
    with _LOCK:
        if _ESTADO["estado"] != "pendiente":
            return
        _ESTADO["estado"] = "calculando"

    def tarea():
        try:
            _ESTADO["resultado"] = validar()
            _ESTADO["estado"] = "listo"
        except Exception:  # noqa: BLE001
            _ESTADO["estado"] = "error"

    threading.Thread(target=tarea, daemon=True).start()


def estado() -> dict:
    iniciar()
    return {"estado": _ESTADO["estado"], "resultado": _ESTADO["resultado"]}


def validar() -> dict:
    b = modelo.base()
    train = b[b["semana"].isin(SEMANAS_ENTRENO)].reset_index(drop=True)
    test = b[b["semana"].isin(SEMANAS_PRUEBA) & b["cobertura"].notna()].reset_index(drop=True)
    barrido = {k: _evaluar_cobertura(train, test, k) for k in KS}
    return {
        "entrenamiento": {"semanas": list(SEMANAS_ENTRENO), "jugadas": int(len(train))},
        "prueba": {"semanas": list(SEMANAS_PRUEBA), "jugadas": int(len(test))},
        "cobertura": {
            "promedio_global": _evaluar_global(train, test),
            "liga_por_situacion": _evaluar_cobertura(train, test, 20, solo_liga=True),
            "modelo_k20": barrido[20],
            "barrido_k": {str(k): v for k, v in barrido.items()},
        },
        "recomendacion": _evaluar_recomendacion(train, test),
    }
