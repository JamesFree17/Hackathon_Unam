import { useEffect, useMemo, useState } from 'react'
import { obtener, pct } from '../api'
import type { Alineacion, Jugador, Lado } from '../tipos'

interface Props {
  equipo: string
  lado: Lado
  inicial: Alineacion | null
  onConfirmar: (a: Alineacion) => void
  onVolver: () => void
}

const GRUPOS: Record<Lado, string[]> = { ataque: ['QB', 'RB', 'WR', 'TE'], defensa: ['DL', 'LB', 'DB'] }
const NOMBRE_GRUPO: Record<string, string> = {
  QB: 'Mariscal', RB: 'Corredores', WR: 'Receptores', TE: 'Ala cerrada', DL: 'Línea defensiva', LB: 'Linebackers', DB: 'Backs defensivos',
}

function detalle(j: Jugador, lado: Lado) {
  if (lado === 'ataque') {
    return j.targets ? `${j.targets} obj · éxito ${pct(j.exito)}` : `${j.jugadas} jugadas`
  }
  return j.tasa_presion != null ? `presión ${pct(j.tasa_presion)} · ${j.sacks ?? 0} sacks` : `${j.jugadas} jugadas`
}

export default function AlineacionPantalla({ equipo, lado, inicial, onConfirmar, onVolver }: Props) {
  const [jugadores, setJugadores] = useState<Jugador[]>([])
  const [titulares, setTitulares] = useState<Set<number>>(new Set())
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    setCargando(true)
    obtener<Jugador[]>(`api/equipos/${equipo}/plantilla?lado=${lado}`)
      .then(js => {
        setJugadores(js)
        const ids = inicial ? inicial.titulares : js.filter(j => j.titular_sugerido).map(j => j.nflId)
        setTitulares(new Set(ids))
      })
      .catch(() => setError('No se pudo cargar la plantilla.'))
      .finally(() => setCargando(false))
  }, [equipo, lado, inicial])

  const porGrupo = useMemo(() => {
    const m: Record<string, Jugador[]> = {}
    for (const j of jugadores) (m[j.grupo] ||= []).push(j)
    return m
  }, [jugadores])

  const alternar = (id: number) =>
    setTitulares(prev => {
      const n = new Set(prev)
      if (n.has(id)) n.delete(id)
      else n.add(id)
      return n
    })

  const confirmar = () =>
    onConfirmar({
      titulares: jugadores.filter(j => titulares.has(j.nflId)).map(j => j.nflId),
      banca: jugadores.filter(j => !titulares.has(j.nflId)).map(j => j.nflId),
    })

  return (
    <div className="space-y-5">
      <p className="text-gray-600">
        Alineación de <b>{equipo}</b> ({lado}). Toca un jugador para pasarlo entre titulares y banca. Ya vienen
        preseleccionados los que más juegan.
      </p>
      {error && <p className="text-red-700">{error}</p>}
      {cargando && <p>Cargando plantilla…</p>}
      {GRUPOS[lado].map(g => {
        const lista = porGrupo[g] ?? []
        if (!lista.length) return null
        const n = lista.filter(j => titulares.has(j.nflId)).length
        return (
          <section key={g}>
            <h3 className="font-semibold mb-2">
              {NOMBRE_GRUPO[g]} <span className="text-gray-500 font-normal">· {n} titulares</span>
            </h3>
            <div className="grid gap-2 sm:grid-cols-2">
              {lista.map(j => {
                const es = titulares.has(j.nflId)
                return (
                  <button
                    key={j.nflId}
                    onClick={() => alternar(j.nflId)}
                    className={`text-left rounded-lg border-2 p-3 ${es ? 'bg-green-50 border-green-700' : 'bg-gray-50 border-gray-300'}`}
                  >
                    <div className="flex justify-between gap-2">
                      <span className="font-semibold">{j.nombre}</span>
                      <span className={`text-xs font-bold rounded px-2 py-0.5 ${es ? 'bg-green-700 text-white' : 'bg-gray-300'}`}>
                        {es ? 'TITULAR' : 'BANCA'}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600">{j.posicion ?? j.grupo} · {detalle(j, lado)}</div>
                  </button>
                )
              })}
            </div>
          </section>
        )
      })}
      <div className="grid grid-cols-3 gap-3">
        <button onClick={onVolver} className="rounded-lg border-2 border-gray-300 p-4 font-semibold">Atrás</button>
        <button onClick={confirmar} disabled={cargando || titulares.size === 0} className="col-span-2 rounded-lg bg-green-800 text-white text-xl font-bold p-4 disabled:opacity-40">
          Confirmar alineación
        </button>
      </div>
    </div>
  )
}
