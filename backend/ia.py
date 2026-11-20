"""IA opcional: Amazon Bedrock (Nova) con Strands Agents.

La IA solo redacta a partir de cifras ya calculadas por `modelo`/`recomendar`; no calcula nada.
Si falla, los endpoints devuelven un texto de respaldo y la app sigue funcionando.
"""
import json
import os

from . import modelo, plantilla, recomendar

_CACHE: dict[str, str] = {}
_CACHE_MAX = 300

SISTEMA = (
    "Eres analista de apoyo para un entrenador de la NFL. Responde en español, en 2 o 3 frases "
    "cortas y directas, listas para leerse en segundos durante un partido. Usa SOLO las cifras "
    "proporcionadas, sin inventar datos ni jugadores. Si la confianza es baja o la muestra es "
    "pequeña, dilo. Los datos son jugadas de pase de las semanas 1 a 8 de 2021."
)


def _modelo():
    from botocore.config import Config
    from strands.models import BedrockModel

    # Solo región y modelo: las credenciales las resuelve boto3 (rol en AWS, .env en local).
    return BedrockModel(
        model_id=os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-pro-v1:0"),
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
        boto_client_config=Config(connect_timeout=5, read_timeout=30, retries={"max_attempts": 1}),
    )


def _consultar(prompt: str) -> str:
    clave = prompt
    if clave in _CACHE:
        return _CACHE[clave]
    from strands import Agent

    agente = Agent(model=_modelo(), system_prompt=SISTEMA, callback_handler=None)
    texto = str(agente(prompt)).strip()
    if not texto:
        raise RuntimeError("respuesta vacía")
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[clave] = texto
    return texto


def _con_respaldo(prompt: str, respaldo: str) -> dict:
    try:
        return {"fuente": "ia", "texto": _consultar(prompt)}
    except Exception as e:  # noqa: BLE001  (la IA es opcional: nunca debe romper la app)
        return {"fuente": "plantilla", "texto": respaldo, "error": type(e).__name__}


def explicar(rec: dict) -> dict:
    prompt = (
        "Explica al entrenador por qué conviene esta recomendación y qué hacer primero. "
        f"Lado: {rec['lado']}. Recomendación (JSON): {json.dumps(rec, ensure_ascii=False)}"
    )
    return _con_respaldo(prompt, recomendar.texto_respaldo(rec))


def datos_reporte(equipo: str, rival: str, lado: str) -> dict:
    perfil = modelo.perfil_equipo(rival)
    if lado == "ataque":
        r = modelo.receptores(equipo).merge(plantilla.plantilla(equipo, "ataque"), on="nflId")
        r = r[r["targets"] >= recomendar.MIN_TARGETS].sort_values("puntuacion", ascending=False).head(3)
        propios = [{"nombre": x["displayName"], "targets": int(x["targets"]), "exito": float(x["exito"])} for _, x in r.iterrows()]
        return {"lado": lado, "equipo": equipo, "rival": rival, "defensa_rival": perfil["defensa"], "mis_mejores_objetivos": propios}
    r = modelo.receptores(rival).merge(plantilla.plantilla(rival, "ataque"), on="nflId")
    r = r[r["targets"] >= recomendar.MIN_TARGETS].sort_values("share", ascending=False).head(3)
    amen = [{"nombre": x["displayName"], "targets": int(x["targets"]), "exito": float(x["exito"])} for _, x in r.iterrows()]
    return {"lado": lado, "equipo": equipo, "rival": rival, "ataque_rival": perfil["ataque"], "receptores_rival": amen}


def _respaldo_reporte(d: dict) -> str:
    if d["lado"] == "ataque":
        de = d["defensa_rival"]
        cob = ", ".join(f"{c['nombre']} ({round(c['prob'] * 100)}%)" for c in de["coberturas"][:3])
        txt = f"{d['rival']} defiende con {cob}. Presiona en {round(de['presion'] * 100)}% de los pases (liga: {round(de['presion_liga'] * 100)}%)."
        if d["mis_mejores_objetivos"]:
            txt += " Tus mejores objetivos: " + ", ".join(o["nombre"] for o in d["mis_mejores_objetivos"]) + "."
        return txt
    at = d["ataque_rival"]
    form = ", ".join(f"{f['nombre']} ({round(f['prob'] * 100)}%)" for f in at["formaciones"])
    txt = f"{d['rival']} ataca desde {form}, con {round(at['exito'] * 100)}% de éxito (liga: {round(at['exito_liga'] * 100)}%)."
    if d["receptores_rival"]:
        txt += " Receptores más usados: " + ", ".join(o["nombre"] for o in d["receptores_rival"]) + "."
    return txt


def reporte(equipo: str, rival: str, lado: str) -> dict:
    d = datos_reporte(equipo, rival, lado)
    d = recomendar.limpiar(d)
    prompt = (
        "Escribe un reporte previo al partido (máximo 4 frases) sobre el rival, con lo más "
        f"importante a explotar o vigilar. Datos (JSON): {json.dumps(d, ensure_ascii=False)}"
    )
    return _con_respaldo(prompt, _respaldo_reporte(d))
