import { useRef } from 'react'
import { pct } from '../api'
import type { Objetivo, Recomendacion } from '../tipos'

// Coordenadas de la cancha en yardas: 120 de largo (10 + 100 + 10) por 53.3 de ancho.
// El ataque siempre avanza de izquierda a derecha. Su zona de anotación propia está en x = 0..10.
const LARGO = 120
const ANCHO = 53.3
const COLORES = ['#dc2626', '#f59e0b', '#7c3aed']

interface Props {
  yardasMeta: number            // yardas que faltan para la zona de anotación rival (1 a 99)
  yardasPrimero: number         // yardas que faltan para el primer down
  ofensiva: string              // equipo que ataca (zona de anotación izquierda)
  defensiva: string
  rec?: Recomendacion | null
  onYardasMeta?: (n: number) => void
}

export function textoYarda(yardasMeta: number): string {
  if (yardasMeta === 50) return 'Medio campo'
  return yardasMeta > 50 ? `Yarda ${100 - yardasMeta} propia` : `Yarda ${yardasMeta} rival`
}

// "short left" -> posición dentro de la cancha, vista con el ataque hacia la derecha.
// Para el mariscal, su izquierda queda arriba en pantalla.
const Y_LADO: Record<string, number> = { left: 13, middle: ANCHO / 2, right: ANCHO - 13 }
const profundidad = (p: string) => (p === 'deep' ? 24 : 7)

function apellido(nombre: string): string {
  const t = nombre.split(' ')
  return t.length > 1 ? t[t.length - 1] : nombre
}

// `n` separa los objetivos que comparten zona para que sus rótulos no se encimen.
function PuntoObjetivo({ o, i, los, n }: { o: Objetivo; i: number; los: number; n: number }) {
  const z = o.zona_preferida
  if (!z) return null
  const base = Y_LADO[z.lado] ?? ANCHO / 2
  const x = Math.min(los + profundidad(z.profundidad) + n * 3, 108)
  const y = base + n * 7 > ANCHO - 6 ? base - n * 7 : base + n * 7
  const qx = Math.max(los - 5, 11)
  const color = COLORES[i % COLORES.length]
  return (
    <g>
      <line x1={qx} y1={ANCHO / 2} x2={x} y2={y} stroke={color} strokeWidth={0.7} strokeDasharray="1.6 1" markerEnd={`url(#punta${i})`} />
      <circle cx={x} cy={y} r={2.2} fill={color} stroke="#fff" strokeWidth={0.4} />
      <text x={x} y={y - 3.2} fontSize={2.8} fill="#fff" textAnchor="middle" stroke="#000" strokeWidth={0.5} paintOrder="stroke" fontWeight="bold">
        {apellido(o.nombre)} {pct(z.exito)}
      </text>
    </g>
  )
}

export default function Cancha({ yardasMeta, yardasPrimero, ofensiva, defensiva, rec, onYardasMeta }: Props) {
  const ref = useRef<SVGSVGElement>(null)
  const arrastrando = useRef(false)
  const los = LARGO - 10 - yardasMeta
  const primero = Math.min(los + yardasPrimero, 110)
  const interactiva = !!onYardasMeta

  const mover = (clientX: number) => {
    if (!ref.current || !onYardasMeta) return
    const r = ref.current.getBoundingClientRect()
    const x = ((clientX - r.left) / r.width) * LARGO
    onYardasMeta(Math.max(1, Math.min(99, Math.round(110 - x))))
  }

  // Líneas de yarda y números.
  const lineas = []
  for (let x = 10; x <= 110; x += 5) {
    lineas.push(<line key={x} x1={x} y1={0} x2={x} y2={ANCHO} stroke="#fff" strokeOpacity={x % 10 === 0 ? 0.75 : 0.35} strokeWidth={x % 10 === 0 ? 0.3 : 0.2} />)
  }
  const numeros = []
  for (let x = 20; x <= 100; x += 10) {
    const n = Math.min(x - 10, 110 - x)
    for (const y of [9, 47]) {
      numeros.push(<text key={`${x}-${y}`} x={x} y={y} fontSize={4} fill="#fff" fillOpacity={0.55} textAnchor="middle" fontWeight="bold">{n}</text>)
    }
  }
  const marcas = []
  for (let x = 11; x < 110; x++) {
    for (const y of [22.6, 29.4]) marcas.push(<line key={`${x}-${y}`} x1={x} y1={y} x2={x} y2={y + 0.9} stroke="#fff" strokeOpacity={0.4} strokeWidth={0.15} />)
  }

  // Zonas donde el rival suele tirar (cuando asesoramos a la defensa).
  const zonasRival =
    rec?.lado === 'defensa'
      ? rec.zonas_rival.zonas.map(z => {
          const [prof, lat] = z.nombre.split(' ')
          const x0 = prof === 'deep' ? los + 10 : los
          const x1 = prof === 'deep' ? Math.min(los + 35, 110) : Math.min(los + 10, 110)
          const y0 = lat === 'left' ? 0 : lat === 'middle' ? ANCHO / 3 : (2 * ANCHO) / 3
          return { ...z, x0, w: Math.max(x1 - x0, 0), y0, h: ANCHO / 3 }
        })
      : []

  const objetivos: Objetivo[] = rec?.lado === 'ataque' ? rec.objetivos : rec?.lado === 'defensa' ? rec.cubrir.slice(0, 3) : []

  return (
    <div className="space-y-1">
      <svg
        ref={ref}
        viewBox={`0 0 ${LARGO} ${ANCHO}`}
        className={`w-full rounded-lg border-2 border-green-900 ${interactiva ? 'cursor-ew-resize' : ''}`}
        style={{ touchAction: interactiva ? 'none' : 'auto' }}
        role="img"
        aria-label={`Cancha. ${textoYarda(yardasMeta)}, ${yardasPrimero} yardas para el primer down`}
        onPointerDown={e => {
          if (!interactiva) return
          arrastrando.current = true
          e.currentTarget.setPointerCapture(e.pointerId)
          mover(e.clientX)
        }}
        onPointerMove={e => arrastrando.current && mover(e.clientX)}
        onPointerUp={() => { arrastrando.current = false }}
      >
        <defs>
          {COLORES.map((c, i) => (
            <marker key={i} id={`punta${i}`} markerWidth="4" markerHeight="4" refX="3" refY="2" orient="auto">
              <path d="M0,0 L4,2 L0,4 z" fill={c} />
            </marker>
          ))}
        </defs>
        <rect width={LARGO} height={ANCHO} fill="#2f7d4f" />
        {[0, 2, 4, 6, 8, 10].map(i => (
          <rect key={i} x={10 + i * 10} width={10} height={ANCHO} fill="#000" fillOpacity={0.05} />
        ))}
        <rect x={0} width={10} height={ANCHO} fill="#14532d" />
        <rect x={110} width={10} height={ANCHO} fill="#7f1d1d" />
        <text x={5} y={ANCHO / 2} fontSize={5} fill="#fff" textAnchor="middle" transform={`rotate(-90 5 ${ANCHO / 2})`} fontWeight="bold" letterSpacing={1}>{ofensiva}</text>
        <text x={115} y={ANCHO / 2} fontSize={5} fill="#fff" textAnchor="middle" transform={`rotate(90 115 ${ANCHO / 2})`} fontWeight="bold" letterSpacing={1}>{defensiva}</text>
        {lineas}
        {marcas}
        {numeros}

        {zonasRival.map(z => (
          <g key={z.nombre}>
            <rect x={z.x0} y={z.y0} width={z.w} height={z.h} fill="#dc2626" fillOpacity={Math.min(z.prob * 2.2, 0.7)} stroke="#fff" strokeOpacity={0.3} strokeWidth={0.2} />
            {z.w > 6 && <text x={z.x0 + z.w / 2} y={z.y0 + z.h / 2 + 1.2} fontSize={3.4} fill="#fff" textAnchor="middle" fontWeight="bold">{pct(z.prob)}</text>}
          </g>
        ))}

        <line x1={los} y1={0} x2={los} y2={ANCHO} stroke="#2563eb" strokeWidth={0.8} />
        <line x1={primero} y1={0} x2={primero} y2={ANCHO} stroke="#facc15" strokeWidth={0.8} />
        <ellipse cx={los} cy={ANCHO / 2} rx={1.6} ry={1} fill="#92400e" stroke="#fff" strokeWidth={0.25} />

        {objetivos.map((o, i) => {
          const zona = o.zona_preferida ? `${o.zona_preferida.profundidad}-${o.zona_preferida.lado}` : ''
          const n = objetivos.slice(0, i).filter(p => p.zona_preferida && `${p.zona_preferida.profundidad}-${p.zona_preferida.lado}` === zona).length
          return <PuntoObjetivo key={o.nflId} o={o} i={i} los={los} n={n} />
        })}

        <text x={60} y={ANCHO - 1.6} fontSize={2.6} fill="#fff" fillOpacity={0.7} textAnchor="middle">
          {ofensiva} ataca →
        </text>
      </svg>
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
        <span className="font-semibold">{textoYarda(yardasMeta)} · faltan {yardasPrimero} para el primer down</span>
        <span className="flex flex-wrap gap-3 text-xs opacity-75">
          <span><span className="inline-block w-3 h-1 align-middle bg-blue-600" /> línea de scrimmage</span>
          <span><span className="inline-block w-3 h-1 align-middle bg-yellow-400" /> primer down</span>
          {interactiva && <span>Toca o arrastra la cancha para mover el balón</span>}
        </span>
      </div>
    </div>
  )
}
