import pandas as pd

from backend import datos, extraccion


def _fila(desc, resultado="C", side="TB", poss="TB", yl=33):
    return {
        "playDescription": desc,
        "passResult": resultado,
        "yardlineNumber": yl,
        "yardlineSide": side,
        "possessionTeam": poss,
    }


def test_completo_con_zona():
    df = pd.DataFrame([_fila("(3:45) (Shotgun) J.Goff pass short middle to A.St. Brown to DET 31 for 6 yards (D.Campbell).")])
    r = extraccion.extraer(df).iloc[0]
    assert r.pasador == "J.Goff"
    assert r.objetivo == "A.St. Brown"
    assert (r.profundidad, r.lado) == ("short", "middle")


def test_incompleto():
    df = pd.DataFrame([_fila("(13:35) (Shotgun) M.Stafford pass incomplete short right to C.Kupp.", "I")])
    r = extraccion.extraer(df).iloc[0]
    assert (r.pasador, r.objetivo, r.profundidad, r.lado) == ("M.Stafford", "C.Kupp", "short", "right")


def test_touchdown_y_anulado():
    ok = _fila("(1:14) (Shotgun) T.Brady pass short middle to G.Bernard for 7 yards, TOUCHDOWN.")
    anulado = _fila("(1:14) (Shotgun) T.Brady pass short middle to G.Bernard for 7 yards, TOUCHDOWN. PENALTY on TB-X.Y, Holding, 10 yards, enforced at TB 20 - No Play.")
    r = extraccion.extraer(pd.DataFrame([ok, anulado]))
    assert list(r.td_ofensivo) == [True, False]
    assert list(r.sin_jugada) == [False, True]


def test_sack_no_tiene_objetivo():
    r = extraccion.extraer(pd.DataFrame([_fila("(1:11) (Shotgun) D.Prescott sacked at TB 33 for -12 yards (S.Barrett).", "S")])).iloc[0]
    assert r.pasador == "D.Prescott" and pd.isna(r.objetivo)


def test_intercepcion_con_y_sin_objetivo():
    con = _fila("(8:44) D.Prescott pass deep middle intended for C.Lamb INTERCEPTED by C.Davis [J.Tryon] at 50.", "IN")
    sin = _fila("(:06) (Shotgun) T.Brady pass deep right INTERCEPTED by J.Lewis at DAL -8. J.Lewis to TB 42 for 66 yards (A.Marpet).", "IN")
    r = extraccion.extraer(pd.DataFrame([con, sin]))
    assert r.objetivo.iloc[0] == "C.Lamb"
    assert pd.isna(r.objetivo.iloc[1])


def test_yardas_a_la_meta():
    propia = _fila("x", yl=20, side="TB", poss="TB")
    rival = _fila("x", yl=20, side="DAL", poss="TB")
    r = extraccion.extraer(pd.DataFrame([propia, rival]))
    assert list(r.yardas_meta) == [80, 20]


def test_llaves_coinciden():
    assert extraccion.llave_abreviado("A.St. Brown") == extraccion.llave_nombre_completo("Amon-Ra St. Brown")
    assert extraccion.llave_abreviado("M.Pittman Jr.") == extraccion.llave_nombre_completo("Michael Pittman Jr.")
    assert extraccion.llave_abreviado("T.Brady") == extraccion.llave_nombre_completo("Tom Brady")


def test_cobertura_en_datos_reales():
    p = datos.jugadas()
    r = extraccion.extraer(p)
    pases = p["passResult"].isin(["C", "I", "IN"])
    assert r.loc[pases, "objetivo"].notna().mean() >= 0.90
    assert r["pasador"].notna().mean() >= 0.95
