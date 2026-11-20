import math

from backend import modelo


def test_clasificacion():
    assert [modelo.clasificar_distancia(x) for x in (1, 3, 4, 7, 8, 20)] == ["corta", "corta", "media", "media", "larga", "larga"]
    assert [modelo.clasificar_zona(x) for x in (95, 81, 80, 41, 40, 21, 20, 1)] == [
        "propia", "propia", "medio", "medio", "ofensiva", "ofensiva", "roja", "roja"]


def test_probabilidades_suman_uno():
    r = modelo.cobertura_esperada("TB", 3, "larga", "medio")
    assert math.isclose(sum(r["_cob"].values()), 1.0, rel_tol=1e-6)
    assert math.isclose(sum(r["_tipo"].values()), 1.0, rel_tol=1e-6)


def test_rival_desconocido_usa_la_liga():
    r = modelo.cobertura_esperada("XXX", 1, "larga", "medio")
    assert r["muestra"] == 0 and r["confianza"] == "baja"
    assert math.isclose(sum(r["_cob"].values()), 1.0, rel_tol=1e-6)


def test_poca_muestra_se_acerca_a_la_liga():
    liga = modelo.cobertura_esperada("XXX", 2, "media", "medio")["_cob"]
    for eq in ("TB", "DAL"):
        r = modelo.cobertura_esperada(eq, 2, "media", "medio")
        # Con k=20 el equipo nunca se aleja más de lo razonable de la liga.
        assert max(abs(r["_cob"].get(c, 0) - liga.get(c, 0)) for c in liga) < 0.35


def test_opciones_de_ataque_ordenadas():
    probs = modelo.cobertura_esperada("TB", 3, "larga", "medio")["_cob"]
    ops = modelo.opciones_ataque("larga", probs)
    assert len(ops) == 3
    assert ops == sorted(ops, key=lambda r: r["puntuacion"], reverse=True)
    assert all(0 <= o["exito"] <= 1 for o in ops)


def test_opciones_de_defensa_ordenadas():
    f = modelo.formacion_esperada("KC", 3, "larga", "medio")["_f"]
    ops = modelo.opciones_defensa("TB", "larga", "medio", f)
    assert ops and ops == sorted(ops, key=lambda r: r["puntuacion"], reverse=True)
    assert all(o["cobertura"] not in ("Red Zone", "Goal Line") for o in ops)


def test_receptores_de_tampa():
    r = modelo.receptores("TB")
    assert r["targets"].sum() > 200
    assert r["puntuacion"].between(0, 1).all()
