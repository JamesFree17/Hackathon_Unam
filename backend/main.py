"""API de la plantilla. Desarrollo: uvicorn backend.main:app --reload (con .venv activo)."""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def cargar_env():
    f = Path(__file__).resolve().parent.parent / ".env"
    if f.exists():
        for linea in f.read_text(encoding="utf-8-sig").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


cargar_env()

from contextlib import asynccontextmanager  # noqa: E402
from typing import Literal  # noqa: E402

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from . import datos, ia, modelo, plantilla, recomendar  # noqa: E402

Distancia = Literal["corta", "media", "larga"]
Zona = Literal["propia", "medio", "ofensiva", "roja"]
Lado = Literal["ataque", "defensa"]


@asynccontextmanager
async def lifespan(_: FastAPI):
    modelo.base()  # calienta las tablas al arrancar (todo en memoria, sin escribir a disco)
    plantilla.tabla_completa()
    yield


app = FastAPI(title="Hackathon NFL UNAM", lifespan=lifespan)


class Situacion(BaseModel):
    equipo: str = Field(min_length=2, max_length=4)
    rival: str = Field(min_length=2, max_length=4)
    down: int = Field(ge=1, le=4)
    distancia: Distancia
    zona: Zona
    titulares: list[int] = Field(default_factory=list, max_length=60)
    banca: list[int] = Field(default_factory=list, max_length=60)


class SituacionIA(Situacion):
    lado: Lado


def _equipo(abr: str) -> str:
    abr = abr.upper()
    if abr not in plantilla.equipos():
        raise HTTPException(status_code=404, detail=f"Equipo desconocido: {abr}")
    return abr


def _recomendar(lado: str, s: Situacion) -> dict:
    equipo, rival = _equipo(s.equipo), _equipo(s.rival)
    if equipo == rival:
        raise HTTPException(status_code=422, detail="El equipo y el rival deben ser distintos")
    f = recomendar.recomendar_ataque if lado == "ataque" else recomendar.recomendar_defensa
    return f(equipo, rival, s.down, s.distancia, s.zona, s.titulares, s.banca)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/resumen")
def api_resumen() -> dict:
    return datos.resumen()


@app.get("/api/presion/cobertura")
def api_cobertura() -> list[dict]:
    return datos.por_cobertura()


@app.get("/api/presion/formacion")
def api_formacion() -> list[dict]:
    return datos.por_formacion()


@app.get("/api/equipos")
def api_equipos() -> list[str]:
    return plantilla.equipos()


@app.get("/api/equipos/{abr}/plantilla")
def api_plantilla(abr: str, lado: Lado) -> list[dict]:
    return recomendar.plantilla_con_metricas(_equipo(abr), lado)


@app.get("/api/jugadas/muestra")
def api_muestra(n: int = 10) -> list[dict]:
    b = modelo.base().head(max(1, min(n, 50)))
    cols = ["gameId", "playId", "possessionTeam", "pasador", "objetivo", "objetivo_id", "profundidad", "lado", "td_ofensivo", "yardas_meta"]
    return recomendar.limpiar(b[cols].to_dict("records"))


@app.get("/api/rival/{abr}/cobertura")
def api_rival_cobertura(abr: str, down: int, distancia: Distancia, zona: Zona) -> dict:
    if not 1 <= down <= 4:
        raise HTTPException(status_code=422, detail="down debe estar entre 1 y 4")
    r = modelo.cobertura_esperada(_equipo(abr), down, distancia, zona)
    return recomendar.limpiar(r)


@app.post("/api/recomendacion/ataque")
def api_ataque(s: Situacion) -> dict:
    return _recomendar("ataque", s)


@app.post("/api/recomendacion/defensa")
def api_defensa(s: Situacion) -> dict:
    return _recomendar("defensa", s)


@app.post("/api/ia/explicacion")
def api_ia_explicacion(s: SituacionIA) -> dict:
    """Siempre devuelve texto: de la IA si está disponible o, si no, de una plantilla."""
    rec = _recomendar(s.lado, s)
    return {"recomendacion": rec} | ia.explicar(rec)


@app.get("/api/ia/reporte/{rival}")
def api_ia_reporte(rival: str, equipo: str, lado: Lado) -> dict:
    return ia.reporte(_equipo(equipo), _equipo(rival), lado)


# El build del dashboard se sirve en la misma URL y puerto. Va al final para no tapar /api.
_dist = RAIZ / "dashboard" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="dashboard")
