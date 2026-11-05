import { useQuery } from '@tanstack/react-query'
import { endpoints } from '../api/client'

export function HomePage() {
  const health = useQuery({ queryKey: ['health'], queryFn: endpoints.health })
  const me = useQuery({ queryKey: ['me'], queryFn: endpoints.me })

  return (
    <section>
      <h1>AWS Challenge</h1>
      <p>
        API: <strong>{health.isPending ? '…' : health.isError ? 'unreachable' : health.data.status}</strong>
      </p>
      <h2>Who am I (claims from the JWT)</h2>
      {me.isPending && <p>Loading…</p>}
      {me.isError && <p className="error">{me.error.message}</p>}
      {me.data && <pre>{JSON.stringify(me.data, null, 2)}</pre>}
    </section>
  )
}
