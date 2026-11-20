# Asistente del coach · NFL Big Data Bowl (UNAM)

Herramienta de apoyo para decidir durante un partido. El coach elige su equipo, el rival y si asesora al **ataque** o a la **defensa**. Marca sus titulares y su banca, y toca botones (down, distancia y zona del campo) para recibir recomendaciones al instante, sin escribir nada.

- Si somos **ataque**: qué defensa esperar, qué jugadas funcionan mejor contra ella, a qué receptor lanzarle y a quién sustituir.
- Si somos **defensa**: qué formación esperar, qué cobertura usar, a quién cubrir y qué defensor mete más presión.

Versión: **1.0.1**

---

## 1. Qué encontramos

Datos: jugadas de pase de las semanas 1 a 8 de 2021, 32 equipos, 122 juegos. Tras quitar las jugadas anuladas por penalización quedan **8,033 jugadas** válidas. Definiciones: una jugada tiene **éxito** si gana al menos el 40% de la distancia en 1.er down, 60% en 2.º y 100% en 3.º y 4.º. Hay **presión** si PFF marca un hit, un hurry o un sack al mariscal.

| # | Hallazgo | Cifras |
|---|---|---|
| 1 | La presión decide la jugada. | Con presión: 33.5% de éxito y 4.1 yd por jugada. Sin presión: 57.5% y 8.3 yd. Hay presión en el 36.5% de los pases (2,934 de 8,033). |
| 2 | La defensa más presionante no es la que más frena. | Cover-0 presiona más (51.0%) pero permite 46.1% de éxito. Cover-1 permite 45.4% con 39.3% de presión. Cover-3, la más usada (2,523 jugadas), permite 51.7%. |
| 3 | Zona cede más éxito que hombre, y hombre presiona más. | Zona: 50.6% de éxito y 34.4% de presión. Hombre: 45.7% y 40.6%. |
| 4 | El play action ayuda y no cuesta más sacks. | Con play action: 54.3% de éxito y 8.1 yd (1,900 jugadas). Sin él: 47.0% y 6.4 yd. Sacks: 6.6% contra 6.4%. |
| 5 | Shotgun, la formación más usada, rinde menos. | Shotgun (64% de las jugadas): 47.0%. Singleback: 54.5%. I-Form: 54.8% (283 jugadas). |
| 6 | La situación pesa mucho. | 1.er down: 55.0% de éxito. 3.er down: 39.5%. Distancia corta: 57.3%. Larga: 46.8%. |
| 7 | Los equipos difieren bastante. | Defensa que menos permite: MIN, 41.9%. La que más: IND, 57.3%. Mejor ataque: LA, 56.8%. Peor: IND, 42.1%. |

Esto lleva a la decisión de producto: las recomendaciones no son genéricas. Combinan lo que el rival suele hacer en esa situación con lo que funciona contra ello, y solo proponen jugadores que el coach tiene disponibles.

## 2. Cómo lo sabemos

**De dónde salen los números.** Todo sale de `data/`: `plays.csv`, `pffScoutingData.csv`, `players.csv` y `games.csv`. No usamos fuentes externas. El tracking (810 MB) queda fuera de esta versión.

**Método.** Son tablas de frecuencias en pandas, sin modelos de ML.
- **Rival:** se estima qué cobertura o formación usa en esa situación (down, distancia, zona del campo). Con pocas jugadas, la estimación se acerca al promedio de la liga: `p = (conteo_equipo + k · p_liga) / (n_equipo + k)`.
- **Jugadas:** se calcula el éxito esperado de cada combinación de formación y play action contra la cobertura probable. Puntuación = éxito − intercepciones − 0.5 · sacks.
- **Jugadores:** el receptor objetivo, el pasador y la zona del pase (short/deep, left/middle/right) se extraen de `playDescription`. La plantilla de cada equipo se reconstruye con los roles de PFF, porque `players.csv` no trae equipo. Los titulares sugeridos son los que más juegan.
- **Sustituciones:** se compara al mejor de la banca con el titular más débil de su posición, y solo se sugiere si la mejora supera un umbral y hay muestra suficiente.
- **IA (Amazon Nova en Bedrock):** solo redacta el resumen y el reporte previo con cifras ya calculadas. No calcula ni predice. Si falla, la app muestra un texto automático y todo lo demás funciona igual.

**Validación.**
- 25 pruebas automáticas (`pytest`) sobre extracción, plantilla, modelo, API y el respaldo cuando la IA falla.
- La extracción identifica al receptor en el **94.9%** de los pases y la mayoría se une con su `nflId` (99.7% de los identificados).
- Las probabilidades suman 1, un rival sin datos usa el promedio de la liga y el ranking respeta la alineación elegida.
- De las 8,557 jugadas originales se descartan 524: 489 anuladas por penalización ("No Play" o "NULLIFIED") y 35 sin down válido. Quedan 8,033.

**Límites que conviene conocer.**
- Los hallazgos son asociaciones, no causas. Además, un sack cuenta como presión, así que parte de la diferencia del hallazgo 1 es mecánica.
- Cada equipo tiene unas 250 jugadas de ataque y otras tantas de defensa en total, y una situación concreta (down, distancia) tiene una mediana de 25 jugadas, y una de cada cuatro tiene 8 o menos. Por eso cada recomendación muestra su muestra y una confianza (alta, media o baja).
- Solo hay jugadas de pase: la app no recomienda pase contra carrera.
- No medimos la calidad individual de cobertura. La sustitución defensiva compara solo presión (DL y LB).
- El marcador no entra al modelo porque la muestra se vuelve demasiado pequeña.
- No hicimos una validación predictiva con datos separados (por ejemplo, entrenar con semanas 1-6 y probar con 7-8). Es el siguiente paso natural.

## 3. Cómo ejecutarlo

Requisitos: Windows con PowerShell, y el entorno que prepara `.hackathon\setup.cmd` (Python 3.12 en `.venv` y Node 22).

**1. Datos.** Los CSV no están en el repositorio por su tamaño (unos 810 MB). Copia `games.csv`, `plays.csv`, `players.csv`, `pffScoutingData.csv` y la carpeta `tracking/` dentro de `data/`.

**2. (Opcional) IA.** Copia `.env.example` como `.env` y pega las llaves temporales del workshop. No se versiona ni entra al zip. Sin llaves la app funciona igual, con textos automáticos.

**3. Verificar el entorno.**

```powershell
.\.hackathon\setup.cmd --check
```

**4. Producción (un solo puerto).**

```powershell
cd dashboard
npm install
npm run build
cd ..
.\.venv\Scripts\python -m uvicorn backend.main:app --port 8000
```

Abre http://localhost:8000. El mismo servidor entrega el dashboard y la API.

**5. Desarrollo (dos terminales).**

```powershell
# Terminal 1, desde la raíz
.\.venv\Scripts\python -m uvicorn backend.main:app --reload --port 8000

# Terminal 2
cd dashboard
npm run dev
```

Abre http://localhost:5173. Vite redirige `/api` al puerto 8000.

**6. Pruebas.**

```powershell
.\.venv\Scripts\python -m pytest backend/tests -q
```

**7. Entrega.**

```powershell
.\.hackathon\setup.cmd --entregar
```

## 4. Cómo usar la app

1. **Inicio:** elige tu equipo, el rival y Ataque o Defensa.
2. **Alineación:** ya vienen marcados los titulares sugeridos. Toca a un jugador para moverlo entre titulares y banca.
3. **Partido:** elige down, distancia y zona. Arriba aparece un resumen en una o dos frases y debajo el detalle con confianza y muestra. Las sustituciones sugeridas se aplican con un botón. El botón "Reporte previo" resume al rival.

## 5. Estructura y API

```
backend/        FastAPI y análisis (extraccion, plantilla, modelo, recomendar, ia)
backend/tests/  pruebas con pytest
dashboard/      React + Vite + Tailwind + Recharts
data/           datos (solo lectura, no se versionan)
```

| Ruta | Qué hace |
|---|---|
| `GET /health` | Estado del servidor |
| `GET /api/equipos` | Los 32 equipos |
| `GET /api/equipos/{abr}/plantilla?lado=` | Jugadores con métricas y titulares sugeridos |
| `GET /api/rival/{abr}/cobertura` | Cobertura esperada del rival en una situación |
| `POST /api/recomendacion/ataque` | Jugadas, objetivos y sustituciones para el ataque |
| `POST /api/recomendacion/defensa` | Formación, coberturas, a quién cubrir y presión |
| `POST /api/ia/explicacion` | Resumen en lenguaje natural (IA o respaldo) |
| `GET /api/ia/reporte/{rival}?equipo=&lado=` | Reporte previo al partido |

## 6. Stack

Python 3.12, FastAPI, Uvicorn, Pydantic, pandas y numpy. Frontend con React 18, Vite 5, TypeScript, Tailwind 3 y Recharts. IA opcional con Strands Agents y Amazon Bedrock (modelo Nova). Versiones fijas por las reglas del hackathon; no se agregaron dependencias.

Los datos del NFL Big Data Bowl los provee NFL Next Gen Stats y los de scouting Pro Football Focus. Ver `data/README.md`.
