export type ConnState = 'idle' | 'connecting' | 'connected' | 'disconnected' | 'error'

export type StatusMsg = {
  type: 'status'
  state: ConnState
  name?: string
  address?: string
  model?: string
  error?: string
}

export type CatalogMsg = {
  type: 'catalog'
  model: string
  display_name: string
  moves: string[]
  actions: string[]
  program: string[]
}

export type TxMsg = {
  type: 'tx'
  kind?: string
  name?: string
  hex?: string
  verbs?: string[]
}

export type RxMsg = { type: 'rx'; hex: string }
export type ErrMsg = { type: 'error'; error: string }
export type ServerMsg = StatusMsg | CatalogMsg | TxMsg | RxMsg | ErrMsg

export type LogItem = { id: number; cls: 'tx' | 'rx' | 'err' | 'info'; text: string }

export type ClientMsg =
  | { type: 'move'; name: string }
  | { type: 'hold_start'; name: string }
  | { type: 'hold_stop' }
  | { type: 'action'; name: string }
  | { type: 'program_run'; verbs: string[] }
  | { type: 'program_clear' }
  | { type: 'raw'; hex: string }
  | { type: 'stop' }
