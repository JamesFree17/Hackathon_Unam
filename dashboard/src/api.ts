// Todas las rutas son relativas y sin diagonal inicial: la app se publica en una subruta.
async function leer<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(`Error ${r.status}`)
  return r.json() as Promise<T>
}

export function obtener<T>(ruta: string, signal?: AbortSignal): Promise<T> {
  return fetch(ruta, { signal }).then(r => leer<T>(r))
}

export function enviar<T>(ruta: string, cuerpo: unknown, signal?: AbortSignal): Promise<T> {
  return fetch(ruta, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cuerpo),
    signal,
  }).then(r => leer<T>(r))
}

export const pct = (x: number | null | undefined) => (x == null ? '—' : `${Math.round(x * 100)}%`)
