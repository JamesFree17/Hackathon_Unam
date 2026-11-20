export type Lado = 'ataque' | 'defensa'
export type Distancia = 'corta' | 'media' | 'larga'
export type Zona = 'propia' | 'medio' | 'ofensiva' | 'roja'
export type Confianza = 'alta' | 'media' | 'baja'

export interface Jugador {
  nflId: number
  nombre: string
  grupo: string
  posicion: string | null
  jugadas: number
  titular_sugerido: boolean
  // ataque
  targets?: number
  exito?: number | null
  yardas_por_target?: number | null
  tds?: number | null
  // defensa
  snaps_rush?: number
  presiones?: number
  sacks?: number
  tasa_presion?: number | null
}

export interface Alineacion {
  titulares: number[]
  banca: number[]
}

export interface Situacion {
  down: number
  distancia: Distancia
  zona: Zona
}

export interface Prob { nombre: string; prob: number }
export interface ZonaPreferida { profundidad: string; lado: string; muestra: number; exito: number }
export interface Persona { nflId: number; nombre: string; grupo: string; posicion: string | null }

export interface Sustitucion {
  grupo: string
  entra: Persona
  sale: Persona
  mejora: number
}

export interface JugadaOpcion {
  formacion: string
  play_action: boolean
  exito: number
  yardas: number
  riesgo_sack: number
  riesgo_int: number
  muestra: number
  puntuacion: number
}

export interface Objetivo extends Persona {
  targets: number
  exito: number
  yardas_por_target: number
  tds: number
  ints?: number
  puntuacion?: number
  zona_preferida: ZonaPreferida | null
  confianza: Confianza
  porcentaje_targets?: number
}

export interface RecAtaque {
  lado: 'ataque'
  cobertura_esperada: { coberturas: Prob[]; tipos: Prob[]; muestra: number; confianza: Confianza }
  jugadas: JugadaOpcion[]
  objetivos: Objetivo[]
  sustituciones: Sustitucion[]
  presion_rival: { tasa_presion: number; tasa_sack: number; muestra: number; confianza: Confianza }
  aviso: string | null
}

export interface CoberturaOpcion {
  cobertura: string
  exito_permitido: number
  yardas_permitidas: number
  presion: number
  sacks: number
  intercepciones: number
  muestra: number
  usos_propios: number
}

export interface RecDefensa {
  lado: 'defensa'
  formacion_esperada: { formaciones: Prob[]; muestra: number; confianza: Confianza }
  coberturas: CoberturaOpcion[]
  zonas_rival: { zonas: Prob[]; muestra: number; confianza: Confianza }
  cubrir: Objetivo[]
  presionadores: (Persona & { tasa_presion: number; sacks: number; snaps: number })[]
  sustituciones: Sustitucion[]
  aviso: string | null
}

export type Recomendacion = RecAtaque | RecDefensa

export interface TextoIA { fuente: 'ia' | 'plantilla'; texto: string }
