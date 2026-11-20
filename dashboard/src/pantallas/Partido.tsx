import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { enviar, obtener, pct } from '../api'
import type {
  Alineacion, Confianza, Distancia, Lado, Objetivo, Prob, RecAtaque, RecDefensa, Recomendacion, Situacion, Sustitucion, TextoIA, Zona,
} from '../tipos'

interface Props {
  equipo: string
  rival: string
  lado: Lado
  alineacion: Alineacion
  onCambiarAlineacion: () => void
  onSustituir: (entra: number, sale: number) => void
  onReiniciar: () => void
}

const DISTANCIAS: { v: Distancia; t: string }[] = [
  { v: 'corta', t: 'Corta (1–3)' }, { v: 'media', t: 'Media (4–7)' }, { v: 'larga', t: 'Larga (8+)' },
]
const ZONAS: { v: Zona; t: string }[] = [
  { v: 'propia', t: 'Campo propio' }, { v: 'medio', t: 'Medio campo' }, { v: 'ofensiva', t: 'Campo rival' }, { v: 'roja', t: 'Zona roja' },
]

function Boton({ activo, onClick, children }: { activo: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`rounded-lg border-2 px-3 py-3 font-semibold ${activo ? 'bg-green-700 text-white border-green-700' : 'bg-white border-gray-300'}`}
    >
      {children}
    </button>
  )
}

function Etiqueta({ c, n }: { c: Confianza; n?: number }) {
  const color = c === 'alta' ? 'bg-green-100 text-green-800' : c === 'media' ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'
  return <span className={`text-xs rounded px-2 py-0.5 ${color}`}>confianza {c}{n != null ? ` · ${n} jugadas` : ''}</span>
}

function Tarjeta({ titulo, children, extra }: { titulo: string; children: React.ReactNode; extra?: React.ReactNode }) {
  return (
    <section className="rounded-lg border p-4 bg-white space-y-2">
      <div className="flex justify-between items-center gap-2">
        <h3 className="font-bold">{titulo}</h3>
        {extra}
      </div>
      {children}
    </section>
  )
}

function Barras({ datos }: { datos: Prob[] }) {
  return (
    <div style={{ width: '100%', height: 180 }}>
      <ResponsiveContainer>
        <BarChart data={datos} layout="vertical" margin={{ left: 20, right: 20 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" domain={[0, 1]} tickFormatter={v => `${Math.round(Number(v) * 100)}%`} />
          <YAxis type="category" dataKey="nombre" width={90} />
          <Tooltip formatter={v => pct(Number(v))} />
          <Bar dataKey="prob">
            {datos.map((_, i) => <Cell key={i} fill={i === 0 ? '#2F7D4F' : '#9DBFAA'} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function Sustituciones({ lista, onSustituir, motivo }: { lista: Sustitucion[]; onSustituir: (e: number, s: number) => void; motivo: string }) {
  if (!lista.length) return <p className="text-sm text-gray-500">Sin cambios recomendados con la alineación actual.</p>
  return (
    <ul className="space-y-2">
      {lista.map(s => (
        <li key={s.grupo + s.entra.nflId} className="flex items-center justify-between gap-2 rounded border border-green-700 bg-green-50 p-2">
          <span className="text-sm">
            <b>Entra {s.entra.nombre}</b> por {s.sale.nombre} ({s.grupo}) · {motivo} +{Math.round(s.mejora * 100)} pts
          </span>
          <button onClick={() => onSustituir(s.entra.nflId, s.sale.nflId)} className="rounded bg-green-700 text-white px-3 py-2 text-sm font-semibold">
            Aplicar
          </button>
        </li>
      ))}
    </ul>
  )
}

function FilaObjetivo({ o }: { o: Objetivo }) {
  const z = o.zona_preferida
  return (
    <li className="rounded border p-2">
      <div className="flex justify-between gap-2">
        <b>{o.nombre} <span className="text-gray-500 font-normal">({o.posicion ?? o.grupo})</span></b>
        <Etiqueta c={o.confianza} n={o.targets} />
      </div>
      <div className="text-sm text-gray-700">
        Éxito {pct(o.exito)} · {o.yardas_por_target} yd/obj · {o.tds} TD
        {o.porcentaje_targets != null && ` · ${pct(o.porcentaje_targets)} de los pases`}
        {z && ` · prefiere ${z.profundidad} ${z.lado} (${pct(z.exito)})`}
      </div>
    </li>
  )
}

function VistaAtaque({ r, onSustituir }: { r: RecAtaque; onSustituir: (e: number, s: number) => void }) {
  return (
    <div className="space-y-4">
      <Tarjeta titulo="Cobertura que esperamos" extra={<Etiqueta c={r.cobertura_esperada.confianza} n={r.cobertura_esperada.muestra} />}>
        <Barras datos={r.cobertura_esperada.coberturas} />
        <p className="text-sm text-gray-600">
          {r.cobertura_esperada.tipos.map(t => `${t.nombre} ${pct(t.prob)}`).join(' · ')}
        </p>
      </Tarjeta>
      <Tarjeta titulo="Mejores jugadas contra esa defensa">
        <ol className="space-y-2">
          {r.jugadas.map((j, i) => (
            <li key={j.formacion + j.play_action} className={`rounded border p-2 ${i === 0 ? 'border-green-700 bg-green-50' : ''}`}>
              <b>{i + 1}. {j.formacion} {j.play_action ? 'con play action' : 'sin play action'}</b>
              <div className="text-sm text-gray-700">
                Éxito {pct(j.exito)} · {j.yardas} yd · sack {pct(j.riesgo_sack)} · intercepción {pct(j.riesgo_int)} · {j.muestra} jugadas
              </div>
            </li>
          ))}
        </ol>
      </Tarjeta>
      <Tarjeta titulo="A quién lanzarle">
        {r.objetivos.length ? <ul className="space-y-2">{r.objetivos.map(o => <FilaObjetivo key={o.nflId} o={o} />)}</ul> : <p className="text-gray-600">{r.aviso}</p>}
      </Tarjeta>
      <Tarjeta titulo="Sustituciones sugeridas">
        <Sustituciones lista={r.sustituciones} onSustituir={onSustituir} motivo="éxito esperado" />
      </Tarjeta>
      <Tarjeta titulo="Presión del rival" extra={<Etiqueta c={r.presion_rival.confianza} n={r.presion_rival.muestra} />}>
        <p>Presiona en {pct(r.presion_rival.tasa_presion)} de los pases y sacó al QB en {pct(r.presion_rival.tasa_sack)}.</p>
      </Tarjeta>
    </div>
  )
}

function VistaDefensa({ r, onSustituir }: { r: RecDefensa; onSustituir: (e: number, s: number) => void }) {
  return (
    <div className="space-y-4">
      <Tarjeta titulo="Formación que esperamos" extra={<Etiqueta c={r.formacion_esperada.confianza} n={r.formacion_esperada.muestra} />}>
        <Barras datos={r.formacion_esperada.formaciones} />
      </Tarjeta>
      <Tarjeta titulo="Coberturas recomendadas">
        <ol className="space-y-2">
          {r.coberturas.map((c, i) => (
            <li key={c.cobertura} className={`rounded border p-2 ${i === 0 ? 'border-green-700 bg-green-50' : ''}`}>
              <b>{i + 1}. {c.cobertura}</b>
              <div className="text-sm text-gray-700">
                Permite {pct(c.exito_permitido)} de éxito · {c.yardas_permitidas} yd · presión {pct(c.presion)} · sack {pct(c.sacks)} · {c.muestra} jugadas
                {c.usos_propios > 0 && ` · la hemos usado ${c.usos_propios} veces`}
              </div>
            </li>
          ))}
        </ol>
      </Tarjeta>
      <Tarjeta titulo="A quién cubrir">
        {r.cubrir.length ? <ul className="space-y-2">{r.cubrir.map(o => <FilaObjetivo key={o.nflId} o={o} />)}</ul> : <p className="text-gray-600">Sin datos suficientes del rival.</p>}
      </Tarjeta>
      <Tarjeta titulo="Hacia dónde tira el rival" extra={<Etiqueta c={r.zonas_rival.confianza} n={r.zonas_rival.muestra} />}>
        <p>{r.zonas_rival.zonas.map(z => `${z.nombre} ${pct(z.prob)}`).join(' · ')}</p>
      </Tarjeta>
      <Tarjeta titulo="Quién presiona más (titulares)">
        {r.presionadores.length ? (
          <ul className="space-y-1">
            {r.presionadores.map(p => (
              <li key={p.nflId}><b>{p.nombre}</b> ({p.posicion ?? p.grupo}) · presión {pct(p.tasa_presion)} · {p.sacks} sacks · {p.snaps} jugadas</li>
            ))}
          </ul>
        ) : <p className="text-gray-600">Sin datos suficientes.</p>}
        <Sustituciones lista={r.sustituciones} onSustituir={onSustituir} motivo="presión" />
        {r.aviso && <p className="text-xs text-gray-500">{r.aviso}</p>}
      </Tarjeta>
    </div>
  )
}

export default function Partido({ equipo, rival, lado, alineacion, onCambiarAlineacion, onSustituir, onReiniciar }: Props) {
  const [sit, setSit] = useState<Situacion>({ down: 1, distancia: 'media', zona: 'medio' })
  const [rec, setRec] = useState<Recomendacion | null>(null)
  const [error, setError] = useState('')
  const [texto, setTexto] = useState<TextoIA | null>(null)
  const [reporte, setReporte] = useState<TextoIA | null>(null)
  const [cargandoReporte, setCargandoReporte] = useState(false)

  const cuerpo = { equipo, rival, ...sit, titulares: alineacion.titulares, banca: alineacion.banca }
  const clave = JSON.stringify(cuerpo)

  // Recomendación rápida (solo estadística).
  useEffect(() => {
    const ac = new AbortController()
    setError('')
    enviar<Recomendacion>(`api/recomendacion/${lado}`, cuerpo, ac.signal)
      .then(setRec)
      .catch(e => { if (e.name !== 'AbortError') setError('No se pudo calcular la recomendación.') })
    return () => ac.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clave, lado])

  // Explicación en lenguaje natural (IA opcional, con retraso para no saturar al cambiar botones).
  useEffect(() => {
    setTexto(null)
    const ac = new AbortController()
    const t = setTimeout(() => {
      enviar<TextoIA>('api/ia/explicacion', { ...cuerpo, lado }, ac.signal)
        .then(setTexto)
        .catch(() => {})
    }, 500)
    return () => { clearTimeout(t); ac.abort() }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clave, lado])

  const verReporte = () => {
    setCargandoReporte(true)
    obtener<TextoIA>(`api/ia/reporte/${rival}?equipo=${equipo}&lado=${lado}`)
      .then(setReporte)
      .catch(() => setReporte({ fuente: 'plantilla', texto: 'No se pudo generar el reporte.' }))
      .finally(() => setCargandoReporte(false))
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xl font-bold">{equipo} {lado === 'ataque' ? 'ataca a' : 'defiende ante'} {rival}</h2>
        <div className="flex gap-2">
          <button onClick={verReporte} disabled={cargandoReporte} className="rounded border-2 border-gray-300 px-3 py-2 text-sm font-semibold">
            {cargandoReporte ? 'Generando…' : 'Reporte previo'}
          </button>
          <button onClick={onCambiarAlineacion} className="rounded border-2 border-gray-300 px-3 py-2 text-sm font-semibold">Alineación</button>
          <button onClick={onReiniciar} className="rounded border-2 border-gray-300 px-3 py-2 text-sm font-semibold">Cambiar equipos</button>
        </div>
      </div>

      {reporte && (
        <div className="rounded-lg bg-blue-50 border border-blue-300 p-3">
          <b>Reporte previo</b> <span className="text-xs text-gray-500">({reporte.fuente === 'ia' ? 'IA' : 'resumen automático'})</span>
          <p>{reporte.texto}</p>
        </div>
      )}

      <section className="space-y-3 rounded-lg bg-gray-50 border p-3">
        <div className="grid grid-cols-4 gap-2">
          {[1, 2, 3, 4].map(d => <Boton key={d} activo={sit.down === d} onClick={() => setSit({ ...sit, down: d })}>{d}.º down</Boton>)}
        </div>
        <div className="grid grid-cols-3 gap-2">
          {DISTANCIAS.map(d => <Boton key={d.v} activo={sit.distancia === d.v} onClick={() => setSit({ ...sit, distancia: d.v })}>{d.t}</Boton>)}
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {ZONAS.map(z => <Boton key={z.v} activo={sit.zona === z.v} onClick={() => setSit({ ...sit, zona: z.v })}>{z.t}</Boton>)}
        </div>
      </section>

      <div className="rounded-lg border-2 border-green-700 bg-green-50 p-3 min-h-[3.5rem]">
        {texto ? (
          <>
            <p className="text-lg">{texto.texto}</p>
            <p className="text-xs text-gray-500">{texto.fuente === 'ia' ? 'Redactado por IA con las cifras de abajo' : 'Resumen automático (IA no disponible)'}</p>
          </>
        ) : <p className="text-gray-500">Preparando resumen…</p>}
      </div>

      {error && <p className="text-red-700">{error}</p>}
      {rec?.lado === 'ataque' && <VistaAtaque r={rec} onSustituir={onSustituir} />}
      {rec?.lado === 'defensa' && <VistaDefensa r={rec} onSustituir={onSustituir} />}
    </div>
  )
}
