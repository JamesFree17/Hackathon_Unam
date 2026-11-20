import { useEffect, useState } from 'react'
import { obtener } from '../api'
import type { Lado } from '../tipos'

interface Props {
  onContinuar: (equipo: string, rival: string, lado: Lado) => void
}

export default function Inicio({ onContinuar }: Props) {
  const [equipos, setEquipos] = useState<string[]>([])
  const [equipo, setEquipo] = useState('')
  const [rival, setRival] = useState('')
  const [lado, setLado] = useState<Lado>('ataque')
  const [error, setError] = useState('')

  useEffect(() => {
    obtener<string[]>('api/equipos').then(setEquipos).catch(() => setError('No se pudo cargar la lista de equipos.'))
  }, [])

  const listo = equipo !== '' && rival !== '' && equipo !== rival

  return (
    <div className="space-y-6">
      <p className="text-gray-600">
        Elige tu equipo, el rival y si vas a asesorar al ataque o a la defensa. Después ajustas titulares y banca.
      </p>
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
    </div>
  )
}
