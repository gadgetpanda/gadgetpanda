import { useDogSocket } from './useDogSocket'
import { DrivePad } from './components/DrivePad'
import { ActionGrid } from './components/ActionGrid'
import { ProgramQueue } from './components/ProgramQueue'
import { LogPanel } from './components/LogPanel'
import './App.css'

export default function App() {
  const { status, catalog, logs, send, statusLabel, wsReady } = useDogSocket()

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <img className="logo" src={`${import.meta.env.BASE_URL}logo.jpg`} alt="Gadget Panda" />
          <div className="brand-copy">
            <p className="product">DOG CONTROL</p>
            <h1>Remote</h1>
          </div>
        </div>

        <div className="vehicle">
          <div className={`conn state-${status.state}`}>
            <span className="conn-dot" />
            <span>{statusLabel}</span>
            {!wsReady && <em>link</em>}
          </div>
          <div className="vehicle-meta">
            <strong>{status.name || '—'}</strong>
            <span>{[status.model?.toUpperCase(), status.address].filter(Boolean).join('  ·  ')}</span>
          </div>
        </div>
      </header>

      <main className="cockpit">
        <DrivePad
          onHoldStart={(name) => send({ type: 'hold_start', name })}
          onHoldStop={() => send({ type: 'hold_stop' })}
          onStop={() => send({ type: 'stop' })}
        />

        <div className="side-stack">
          <ActionGrid
            actions={catalog?.actions || []}
            onAction={(name) => send({ type: 'action', name })}
          />
          <ProgramQueue
            picks={catalog?.program || []}
            onRun={(verbs) => send({ type: 'program_run', verbs })}
            onClearDevice={() => send({ type: 'program_clear' })}
          />
        </div>

        <LogPanel logs={logs} onRaw={(hex) => send({ type: 'raw', hex })} />
      </main>
    </div>
  )
}
