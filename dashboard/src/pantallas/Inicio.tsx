import { useEffect, useState } from 'react'
import { obtener, pct } from '../api'
import Cancha from '../componentes/Cancha'
import type { Lado } from '../tipos'

interface Props {
  onContinuar: (equipo: string, rival: string, lado: Lado) => void
  onMetodo: () => void
}

interface Hallazgos {
  jugadas: number
  equipos: number
  juegos: number
  tasa_presion: number
  exito_con_presion: number
  exito_sin_presion: number
  exito_play_action: number
  exito_sin_play_action: number
}

function Dato({ grande, texto }: { grande: string; texto: string }) {
  return (
    <div className="rounded-lg bg-white/10 border border-white/20 p-3 text-center">
      <div className="text-3xl font-extrabold">{grande}</div>
      <div className="text-sm text-green-100">{texto}</div>
    </div>
  )
}

export default function Inicio({ onContinuar, onMetodo }: Props) {
  const [equipos, setEquipos] = useState<string[]>([])
  const [equipo, setEquipo] = useState('')
  const [rival, setRival] = useState('')
  const [lado, setLado] = useState<Lado>('ataque')
  const [error, setError] = useState('')
  const [h, setH] = useState<Hallazgos | null>(null)

  useEffect(() => {
    obtener<string[]>('api/equipos').then(setEquipos).catch(() => setError('No se pudo cargar la lista de equipos.'))
    obtener<Hallazgos>('api/hallazgos').then(setH).catch(() => {})
  }, [])

  const listo = equipo !== '' && rival !== '' && equipo !== rival

  return (
    <div className="space-y-6">
      <section className="rounded-2xl bg-gradient-to-br from-green-950 via-green-900 to-green-700 text-white p-5 space-y-4 shadow-lg">
        <div>
          <p className="text-sm uppercase tracking-widest text-green-200">NFL Big Data Bowl · UNAM</p>
          <h2 className="text-3xl sm:text-4xl font-extrabold leading-tight">La decisión correcta, en segundos.</h2>
          <p className="text-green-100 mt-1">
            Estadística de {h ? `${h.jugadas.toLocaleString('es-MX')} jugadas de pase y ${h.equipos} equipos` : 'toda la liga'} convertida en
            recomendaciones para el ataque y la defensa, sin escribir una sola palabra.
          </p>
        </div>
        <Cancha yardasMeta={35} yardasPrimero={10} ofensiva="LOCAL" defensiva="RIVAL" />
        {h && (
          <div className="grid gap-3 sm:grid-cols-3">
            <Dato grande={pct(h.tasa_presion)} texto="de los pases sufren presión sobre el mariscal" />
            <Dato grande={`${pct(h.exito_sin_presion)} → ${pct(h.exito_con_presion)}`} texto="éxito de la jugada sin presión → con presión" />
            <Dato grande={`${pct(h.exito_sin_play_action)} → ${pct(h.exito_play_action)}`} texto="éxito sin play action → con play action" />
          </div>
        )}
      </section>

      <section className="space-y-4">
        <h3 className="text-xl font-bold">Empieza un partido</h3>
        {error && <p className="text-red-700">{error}</p>}
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block">
            <span className="font-semibold">Mi equipo</span>
            <select className="mt-1 w-full border rounded p-3 text-lg" value={equipo} onChange={e => setEquipo(e.target.value)}>
              <option value="">Selecciona…</option>
              {equipos.map(e => <option key={e} value={e}>{e}</option>)}
            </select>
          </label>
          <label className="block">
            <span className="font-semibold">Rival</span>
            <select className="mt-1 w-full border rounded p-3 text-lg" value={rival} onChange={e => setRival(e.target.value)}>
              <option value="">Selecciona…</option>
              {equipos.map(e => <option key={e} value={e}>{e}</option>)}
            </select>
          </label>
        </div>
        <div className="grid grid-cols-2 gap-3">
          {(['ataque', 'defensa'] as Lado[]).map(l => (
            <button
              key={l}
              onClick={() => setLado(l)}
              className={`rounded-lg p-4 text-xl font-bold border-2 ${lado === l ? 'bg-green-700 text-white border-green-700' : 'bg-white border-gray-300'}`}
            >
              {l === 'ataque' ? 'Somos ATAQUE' : 'Somos DEFENSA'}
            </button>
          ))}
        </div>
        {equipo !== '' && equipo === rival && <p className="text-red-700">El rival debe ser distinto a tu equipo.</p>}
        <button
          disabled={!listo}
          onClick={() => onContinuar(equipo, rival, lado)}
          className="w-full rounded-lg bg-green-800 text-white text-xl font-bold p-4 disabled:opacity-40"
        >
          Continuar a la alineación
        </button>
        <button onClick={onMetodo} className="w-full text-green-800 underline">¿Qué tan confiable es? Ver método y validación</button>
      </section>
    </div>
  )
}
