/** Placeholder for a page whose feature and API arrive in a later curriculum week; makes no request. */
export function ComingLater({ title }: { title: string }) {
  return (
    <section className="card card-centered">
      <h1>{title}</h1>
      <p className="muted">Not available yet — coming in a later week.</p>
    </section>
  )
}
