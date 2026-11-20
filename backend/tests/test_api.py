from fastapi.testclient import TestClient

from backend import ia
from backend.main import app

c = TestClient(app)


def _situacion(**kw):
    base = {"equipo": "TB", "rival": "DAL", "down": 3, "distancia": "larga", "zona": "medio", "titulares": [], "banca": []}
    return base | kw


def _ids(equipo, lado):
    p = c.get(f"/api/equipos/{equipo}/plantilla", params={"lado": lado}).json()
    return [x["nflId"] for x in p if x["titular_sugerido"]], [x["nflId"] for x in p if not x["titular_sugerido"]]


def test_health_y_equipos():
    assert c.get("/health").json() == {"status": "ok"}
    assert len(c.get("/api/equipos").json()) == 32


def test_validacion_y_404():
    assert c.get("/api/equipos/ZZZ/plantilla", params={"lado": "ataque"}).status_code == 404
    assert c.post("/api/recomendacion/ataque", json=_situacion(down=9)).status_code == 422
    assert c.post("/api/recomendacion/ataque", json=_situacion(distancia="x")).status_code == 422
    assert c.post("/api/recomendacion/ataque", json=_situacion(rival="TB")).status_code == 422


def test_recomendacion_ataque_respeta_alineacion():
    tit, ban = _ids("TB", "ataque")
    r = c.post("/api/recomendacion/ataque", json=_situacion(titulares=tit, banca=ban)).json()
    assert r["jugadas"] and r["cobertura_esperada"]["coberturas"]
    assert {o["nflId"] for o in r["objetivos"]} <= set(tit)
    # Sin titulares no se recomienda a nadie.
    vacio = c.post("/api/recomendacion/ataque", json=_situacion()).json()
    assert vacio["objetivos"] == [] and vacio["aviso"]


def test_recomendacion_defensa():
    tit, ban = _ids("TB", "defensa")
    r = c.post("/api/recomendacion/defensa", json=_situacion(equipo="TB", rival="DAL", titulares=tit, banca=ban)).json()
    assert r["coberturas"] and r["formacion_esperada"]["formaciones"] and r["cubrir"]
    assert {p["nflId"] for p in r["presionadores"]} <= set(tit)


def test_ia_usa_respaldo_si_falla(monkeypatch):
    def falla(_):
        raise RuntimeError("sin IA")

    monkeypatch.setattr(ia, "_consultar", falla)
    tit, ban = _ids("TB", "ataque")
    r = c.post("/api/ia/explicacion", json=_situacion(lado="ataque", titulares=tit, banca=ban)).json()
    assert r["fuente"] == "plantilla" and r["texto"]
    rep = c.get("/api/ia/reporte/DAL", params={"equipo": "TB", "lado": "ataque"}).json()
    assert rep["fuente"] == "plantilla" and "DAL" in rep["texto"]
    rep2 = c.get("/api/ia/reporte/DAL", params={"equipo": "TB", "lado": "defensa"}).json()
    assert rep2["fuente"] == "plantilla" and rep2["texto"]


def test_yardas_exactas_mandan_sobre_las_categorias():
    cuerpo = {"equipo": "TB", "rival": "DAL", "down": 3, "yardas_meta": 15, "yardas_primero": 2}
    r = c.post("/api/recomendacion/ataque", json=cuerpo).json()
    assert r["situacion"]["zona"] == "roja" and r["situacion"]["distancia"] == "corta"
    assert r["situacion"]["yardas_meta"] == 15
    # Si hay yardas y categorías, ganan las yardas.
    r2 = c.post("/api/recomendacion/ataque", json=cuerpo | {"zona": "propia", "distancia": "larga"}).json()
    assert r2["situacion"]["zona"] == "roja"
    # Sin ninguna de las dos es un error de validación.
    assert c.post("/api/recomendacion/ataque", json={"equipo": "TB", "rival": "DAL", "down": 1}).status_code == 422
    assert c.post("/api/recomendacion/ataque", json=cuerpo | {"yardas_meta": 150}).status_code == 422


def test_hallazgos_son_coherentes():
    h = c.get("/api/hallazgos").json()
    assert h["equipos"] == 32 and h["juegos"] == 122
    assert h["exito_sin_presion"] > h["exito_con_presion"]


def test_validacion_devuelve_estado(monkeypatch):
    from backend import validacion

    monkeypatch.setattr(validacion, "estado", lambda: {"estado": "calculando", "resultado": None})
    assert c.get("/api/validacion").json() == {"estado": "calculando", "resultado": None}
