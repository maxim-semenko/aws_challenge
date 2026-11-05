import { useMutation } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { endpoints } from '../api/client'

export function ChatPage() {
  const [query, setQuery] = useState('')
  const search = useMutation({ mutationFn: (q: string) => endpoints.search(q) })

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (query.trim()) search.mutate(query.trim())
  }

  return (
    <section>
      <h1>Semantic search</h1>
      <form onSubmit={onSubmit} className="row">
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ask something…" />
        <button type="submit" disabled={search.isPending}>
          {search.isPending ? 'Searching…' : 'Search'}
        </button>
      </form>
      {search.isError && <p className="error">{search.error.message}</p>}
      <ul className="results">
        {search.data?.map((r) => (
          <li key={r.id}>
            <strong>{r.title}</strong> <small>distance {r.distance.toFixed(3)}</small>
            <p>{r.content}</p>
          </li>
        ))}
      </ul>
    </section>
  )
}
