import { useState, type FormEvent } from 'react'
import type { LogItem } from '../types'
import './LogPanel.css'

type Props = {
  logs: LogItem[]
  onRaw: (hex: string) => void
}

export function LogPanel({ logs, onRaw }: Props) {
  const [hex, setHex] = useState('')

  const submit = (e: FormEvent) => {
    e.preventDefault()
    const value = hex.trim()
    if (!value) return
    onRaw(value)
    setHex('')
  }

  return (
    <section className="panel log">
      <div className="panel-head">
        <h2>Telemetry</h2>
        <p>TX / RX</p>
      </div>
      <div className="log-box">
        {logs.map((item) => (
          <div key={item.id} className={`line ${item.cls}`}>
            {item.text}
          </div>
        ))}
        {!logs.length && <div className="line info">No events</div>}
      </div>
      <form className="raw" onSubmit={submit}>
        <input
          value={hex}
          onChange={(e) => setHex(e.target.value)}
          placeholder="raw hex  b10100"
          spellCheck={false}
          autoComplete="off"
        />
        <button type="submit" className="btn">
          Send
        </button>
      </form>
    </section>
  )
}
