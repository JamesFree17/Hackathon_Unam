import { useEffect, useState } from 'react'
import { obtener, pct } from '../api'

interface Metricas { top1: number; top3: number; log_loss: number }
interface Validacion {
  estado: 'pendiente' | 'calculando' | 'listo' | 'error'
  resultado: null | {
    entrenamiento: { semanas: number[]; jugadas: number }
    prueba: { semanas: number[]; jugadas: number }
    cobertura: {
      promedio_global: Metricas
      liga_por_situacion: Metricas
      modelo_k20: Metricas
      barrido_k: Record<string, Metricas>
    }
    recomendacion: {
      jugadas_que_coinciden: number
      jugadas_que_no: number
      exito_coinciden: number
      exito_no: number
      diferencia: number
      ic95: [number, number]
    }
  }
}

const rango = (s: number[]) => (s.length > 1 ? `${s[0]}–${s[s.length - 1]}` : `${s[0]}`)

export default function Metodo({ onVolver }: { onVolver: () => void }) {
  const [v, setV] = useState<Validacion | null>(null)

  useEffect(() => {
    let vivo = true
    let t: ReturnType<typeof setTimeout>
    const cargar = () =>
      obtener<Validacion>('api/validacion')
        .then(d => {
          if (!vivo) return
          setV(d)
          if (d.estado === 'calculando' || d.estado === 'pendiente') t = setTimeout(cargar, 4000)
        })
        .catch(() => vivo && setV({ estado: 'error', resultado: null }))
    cargar()
    return () => { vivo = false; clearTimeout(t) }
  }, [])

  const r = v?.resultado

  return (
    <div className="space-y-5">
      <button onClick={onVolver} className="rounded border-2 border-gray-300 px-3 py-2 font-semibold">← Volver</button>
      <h2 className="text-2xl font-bold">Cómo funciona y qué tan confiable es</h2>

      <section className="space-y-2">
        <h3 className="font-bold">El método</h3>
        <ul className="list-disc pl-5 space-y-1 text-gray-700">
          <li>Todo sale de los datos del NFL Big Data Bowl (jugadas de pase, semanas 1–8 de 2021). No usamos fuentes externas.</li>
          <li>Son tablas de frecuencias, no una caja negra. Si un equipo tiene pocas jugadas en una situación, su estimación se acerca al promedio de la liga.</li>
          <li><b>Éxito</b>: ganar al menos el 40% de la distancia en 1.er down, 60% en 2.º y 100% en 3.º y 4.º.</li>
          <li>La IA solo redacta con las cifras ya calculadas. No predice ni calcula.</li>
        </ul>
      </section>

      <section className="space-y-3">
        <h3 className="font-bold">Prueba con datos que el modelo no vio</h3>
        {!v || v.estado === 'calculando' || v.estado === 'pendiente' ? (
          <p className="rounded bg-yellow-50 border border-yellow-300 p-3">Calculando la validación (tarda cerca de un minuto la primera vez)…</p>
        ) : v.estado === 'error' || !r ? (
          <p className="rounded bg-red-50 border border-red-300 p-3">No se pudo calcular la validación.</p>
        ) : (
          <>
            <p className="text-gray-700">
              Entrenamos con las semanas {rango(r.entrenamiento.semanas)} ({r.entrenamiento.jugadas} jugadas) y evaluamos en las semanas{' '}
              {rango(r.prueba.semanas)} ({r.prueba.jugadas} jugadas).
            </p>

            <div>
              <h4 className="font-semibold">1. ¿Predecimos mejor la cobertura del rival?</h4>
              <table className="w-full text-sm mt-1 border">
                <thead className="bg-gray-100">
                  <tr><th className="p-2 text-left">Método</th><th className="p-2">Acierta la 1.ª</th><th className="p-2">Está en las 3 primeras</th><th className="p-2">Error (menor es mejor)</th></tr>
                </thead>
                <tbody className="text-center">
                  <tr><td className="p-2 text-left">Frecuencia global</td><td>{pct(r.cobertura.promedio_global.top1)}</td><td>{pct(r.cobertura.promedio_global.top3)}</td><td>{r.cobertura.promedio_global.log_loss}</td></tr>
                  <tr><td className="p-2 text-left">Promedio de la liga en esa situación</td><td>{pct(r.cobertura.liga_por_situacion.top1)}</td><td>{pct(r.cobertura.liga_por_situacion.top3)}</td><td>{r.cobertura.liga_por_situacion.log_loss}</td></tr>
                  <tr className="bg-green-50 font-semibold"><td className="p-2 text-left">Nuestro modelo (historial del rival)</td><td>{pct(r.cobertura.modelo_k20.top1)}</td><td>{pct(r.cobertura.modelo_k20.top3)}</td><td>{r.cobertura.modelo_k20.log_loss}</td></tr>
                </tbody>
              </table>
              <p className="text-sm text-gray-600 mt-1">
                Mejora real pero moderada: sube acertar entre las 3 primeras de {pct(r.cobertura.liga_por_situacion.top3)} a {pct(r.cobertura.modelo_k20.top3)}. Acertar la cobertura exacta es difícil: hay 12 tipos y los equipos las mezclan.
              </p>
            </div>

            <div>
              <h4 className="font-semibold">2. ¿Las jugadas recomendadas funcionan más?</h4>
              <p className="text-gray-700">
                Jugadas que coinciden con nuestro top 3: <b>{pct(r.recomendacion.exito_coinciden)}</b> de éxito ({r.recomendacion.jugadas_que_coinciden} jugadas).
                Las demás: <b>{pct(r.recomendacion.exito_no)}</b> ({r.recomendacion.jugadas_que_no}). Diferencia de{' '}
                <b>{Math.round(r.recomendacion.diferencia * 100)} puntos</b> (intervalo de confianza 95%: {Math.round(r.recomendacion.ic95[0] * 100)} a {Math.round(r.recomendacion.ic95[1] * 100)}).
              </p>
              <p className="text-sm text-gray-600">
                Es una asociación, no una prueba de causa: las jugadas que coinciden pueden darse en situaciones más favorables.
              </p>
            </div>
          </>
        )}
      </section>

      <section className="space-y-1">
        <h3 className="font-bold">Límites que conviene conocer</h3>
        <ul className="list-disc pl-5 space-y-1 text-gray-700">
          <li>Solo jugadas de pase de 8 semanas: no se aconseja pase contra carrera.</li>
          <li>Una situación concreta suele tener pocas jugadas por equipo. Cada recomendación muestra su muestra y su confianza.</li>
          <li>Los datos no miden qué tan bien cubre cada defensor. La sustitución defensiva compara solo presión.</li>
        </ul>
      </section>
    </div>
  )
}
