import { useState } from 'react'
import AlineacionPantalla from './pantallas/AlineacionPantalla'
import Inicio from './pantallas/Inicio'
import Partido from './pantallas/Partido'
import type { Alineacion, Lado } from './tipos'

type Paso = 'inicio' | 'alineacion' | 'partido'

export default function App() {
  const [paso, setPaso] = useState<Paso>('inicio')
  const [equipo, setEquipo] = useState('')
  const [rival, setRival] = useState('')
  const [lado, setLado] = useState<Lado>('ataque')
  const [alineacion, setAlineacion] = useState<Alineacion | null>(null)

  // Intercambia un titular por un jugador de la banca (sustitución sugerida).
  const sustituir = (entra: number, sale: number) =>
    setAlineacion(a =>
      a && {
        titulares: [...a.titulares.filter(id => id !== sale), entra],
        banca: [...a.banca.filter(id => id !== entra), sale],
      },
    )

  return (
    <main className="mx-auto max-w-3xl p-4 space-y-4">
      <header>
        <h1 className="text-2xl font-bold">Asistente del coach · NFL</h1>
        <p className="text-sm text-gray-500">Jugadas de pase, semanas 1–8 de 2021. Recomendaciones basadas en estadística.</p>
      </header>

      {paso === 'inicio' && (
        <Inicio
          onContinuar={(e, r, l) => {
            setEquipo(e); setRival(r); setLado(l); setAlineacion(null); setPaso('alineacion')
          }}
        />
      )}
      {paso === 'alineacion' && (
        <AlineacionPantalla
          equipo={equipo}
          lado={lado}
          inicial={alineacion}
          onVolver={() => setPaso(alineacion ? 'partido' : 'inicio')}
          onConfirmar={a => { setAlineacion(a); setPaso('partido') }}
        />
      )}
      {paso === 'partido' && alineacion && (
        <Partido
          equipo={equipo}
          rival={rival}
          lado={lado}
          alineacion={alineacion}
          onCambiarAlineacion={() => setPaso('alineacion')}
          onSustituir={sustituir}
          onReiniciar={() => setPaso('inicio')}
        />
      )}
    </main>
  )
}
