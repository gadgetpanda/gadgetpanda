import { useState } from 'react'
import './ProgramQueue.css'

type Props = {
  picks: string[]
  onRun: (verbs: string[]) => void
  onClearDevice: () => void
}

function label(name: string) {
  return name.replaceAll('_', ' ')
}

export function ProgramQueue({ picks, onRun, onClearDevice }: Props) {
  const [queue, setQueue] = useState<string[]>([])

  return (
    <section className="panel program">
      <div className="panel-head">
        <h2>Autopilot queue</h2>
        <p>Build then run</p>
      </div>
      <div className="chip-grid">
        {picks.map((name) => (
          <button
            key={name}
            type="button"
            className="chip"
            onClick={() => setQueue((q) => [...q, name])}
          >
            + {label(name)}
          </button>
        ))}
      </div>
      <ol className="queue">
        {queue.map((name, idx) => (
          <li key={`${name}-${idx}`}>
            <button
              type="button"
              className="queue-item"
              title="Remove"
              onClick={() => setQueue((q) => q.filter((_, i) => i !== idx))}
            >
              {idx + 1}. {label(name)}
            </button>
          </li>
        ))}
        {!queue.length && <li className="queue-empty">No steps</li>}
      </ol>
      <div className="row">
        <button
          type="button"
          className="btn"
          onClick={() => {
            setQueue([])
            onClearDevice()
          }}
        >
          Clear
        </button>
        <button
          type="button"
          className="btn primary"
          onClick={() => {
            if (!queue.length) return
            onRun([...queue])
          }}
        >
          Run
        </button>
      </div>
    </section>
  )
}
