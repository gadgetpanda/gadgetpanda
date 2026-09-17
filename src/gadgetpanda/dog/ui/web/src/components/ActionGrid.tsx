type Props = {
  actions: string[]
  onAction: (name: string) => void
}

function label(name: string) {
  return name.replaceAll('_', ' ')
}

export function ActionGrid({ actions, onAction }: Props) {
  return (
    <section className="panel actions">
      <div className="panel-head">
        <h2>Controls</h2>
        <p>Tap once</p>
      </div>
      <div className="chip-grid">
        {actions.map((name) => (
          <button key={name} type="button" className="chip" onClick={() => onAction(name)}>
            {label(name)}
          </button>
        ))}
        {!actions.length && <p className="empty">Waiting for vehicle…</p>}
      </div>
    </section>
  )
}
