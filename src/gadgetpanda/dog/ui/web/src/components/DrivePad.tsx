import { useRef } from 'react'
import './DrivePad.css'

type Props = {
  onHoldStart: (name: string) => void
  onHoldStop: () => void
  onStop: () => void
}

const DIRS: { name: string; label: string; area: string }[] = [
  { name: 'forward', label: '▲', area: 'f' },
  { name: 'turn_left', label: '◀', area: 'l' },
  { name: 'turn_right', label: '▶', area: 'r' },
  { name: 'backward', label: '▼', area: 'b' },
]

export function DrivePad({ onHoldStart, onHoldStop, onStop }: Props) {
  const holding = useRef(false)

  const start = (name: string, el: HTMLButtonElement) => {
    if (holding.current) return
    holding.current = true
    el.classList.add('is-down')
    onHoldStart(name)
  }

  const end = (el?: HTMLButtonElement | null) => {
    if (!holding.current) return
    holding.current = false
    el?.classList.remove('is-down')
    document.querySelectorAll('.pad .dir.is-down').forEach((n) => n.classList.remove('is-down'))
    onHoldStop()
  }

  return (
    <section className="panel drive">
      <div className="panel-head">
        <h2>Drive</h2>
        <p>Hold to move</p>
      </div>
      <div className="wheel">
        <div className="pad">
          {DIRS.map((d) => (
            <button
              key={d.name}
              type="button"
              className="dir"
              style={{ gridArea: d.area }}
              onPointerDown={(e) => {
                e.preventDefault()
                e.currentTarget.setPointerCapture(e.pointerId)
                start(d.name, e.currentTarget)
              }}
              onPointerUp={(e) => {
                e.preventDefault()
                end(e.currentTarget)
              }}
              onPointerCancel={(e) => end(e.currentTarget)}
            >
              {d.label}
            </button>
          ))}
          <button
            type="button"
            className="stop"
            style={{ gridArea: 'c' }}
            onClick={() => {
              holding.current = false
              onStop()
            }}
          >
            STOP
          </button>
        </div>
      </div>
    </section>
  )
}
