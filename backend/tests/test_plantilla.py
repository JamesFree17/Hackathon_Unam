from backend import plantilla


def test_hay_32_equipos():
    assert len(plantilla.equipos()) == 32


def test_titulares_sugeridos_son_los_de_mas_jugadas():
    p = plantilla.plantilla("TB", "ataque")
    assert not p.empty
    for grupo, n in plantilla.TITULARES.items():
        sub = p[p["grupo"] == grupo]
        if sub.empty:
            continue
        tit = sub[sub["titular_sugerido"]]
        ban = sub[~sub["titular_sugerido"]]
        assert len(tit) == min(n, len(sub))
        if len(ban):
            assert tit["jugadas"].min() >= ban["jugadas"].max()


def test_qb_de_tampa_es_brady():
    p = plantilla.plantilla("TB", "ataque")
    qb = p[(p["grupo"] == "QB") & p["titular_sugerido"]]
    assert qb["displayName"].tolist() == ["Tom Brady"]


def test_lado_defensa_solo_grupos_defensivos():
    p = plantilla.plantilla("DAL", "defensa")
    assert set(p["grupo"]) <= {"DL", "LB", "DB"}


def test_mapa_de_nombres_resuelve_objetivos_conocidos():
    mapa = plantilla.llave_a_id()
    assert ("TB", "c|godwin") in mapa
    assert ("DET", "a|stbrown") in mapa
