import { useCallback, useEffect, useRef, useState } from 'react'
import type { CatalogMsg, ClientMsg, ConnState, LogItem, ServerMsg, StatusMsg } from './types'

let logSeq = 0

const STATUS_LABEL: Record<ConnState, string> = {
  idle: 'รอเชื่อมต่อ',
  connecting: 'กำลังเชื่อมต่อ…',
  connected: 'เชื่อมต่อแล้ว',
  disconnected: 'ตัดแล้ว',
  error: 'ผิดพลาด',
}

export function useDogSocket() {
  const socketRef = useRef<WebSocket | null>(null)
  const [status, setStatus] = useState<StatusMsg>({ type: 'status', state: 'idle' })
  const [catalog, setCatalog] = useState<CatalogMsg | null>(null)
  const [logs, setLogs] = useState<LogItem[]>([])
  const [wsReady, setWsReady] = useState(false)

  const pushLog = useCallback((text: string, cls: LogItem['cls']) => {
    setLogs((prev) => [{ id: ++logSeq, text, cls }, ...prev].slice(0, 80))
  }, [])

  const send = useCallback((msg: ClientMsg) => {
    const socket = socketRef.current
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      pushLog('ws not ready', 'err')
      return
    }
    socket.send(JSON.stringify(msg))
  }, [pushLog])

  useEffect(() => {
    let cancelled = false
    let retry: number | undefined

    const connect = () => {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      const socket = new WebSocket(`${proto}://${location.host}/ws`)
      socketRef.current = socket

      socket.addEventListener('open', () => {
        if (cancelled) return
        setWsReady(true)
        pushLog('ws open', 'info')
      })

      socket.addEventListener('close', () => {
        if (cancelled) return
        setWsReady(false)
        pushLog('ws closed — reconnect…', 'err')
        retry = window.setTimeout(connect, 1200)
      })

      socket.addEventListener('message', (ev) => {
        let msg: ServerMsg
        try {
          msg = JSON.parse(ev.data) as ServerMsg
        } catch {
          return
        }
        if (msg.type === 'status') {
          setStatus(msg)
          if (msg.error) pushLog(`error ${msg.error}`, 'err')
        } else if (msg.type === 'catalog') {
          setCatalog(msg)
        } else if (msg.type === 'tx') {
          const detail = msg.hex || msg.name || (msg.verbs || []).join(',') || msg.kind
          pushLog(`tx ${msg.kind || ''} ${detail}`.trim(), 'tx')
        } else if (msg.type === 'rx') {
          pushLog(`rx ${msg.hex}`, 'rx')
        } else if (msg.type === 'error') {
          pushLog(msg.error || 'error', 'err')
        }
      })
    }

    connect()
    return () => {
      cancelled = true
      if (retry) window.clearTimeout(retry)
      socketRef.current?.close()
    }
  }, [pushLog])

  return {
    status,
    catalog,
    logs,
    wsReady,
    send,
    statusLabel: STATUS_LABEL[status.state] || status.state,
  }
}
