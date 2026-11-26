import { useEffect, useState, type FormEvent } from 'react'
import { ApiError, type ChatResponse } from '../api/client'
import { useChat, useSignOutOnUnauthorized } from '../api/queries'
import { useGroups } from '../auth/session'
import {
  DEBOUNCE_MS,
  MAX_QUERY_LENGTH,
  canSubmit,
  chatErrorMessage,
  chatMode,
  formatCell,
  metaLine,
  shouldAutoSend,
} from '../chat/view'
import { isApiConfigured } from '../config/amplify'
import { ComingLater } from './ComingLater'

/**
 * /chat (spec 13, T05-04): admin-only AI search. Without VITE_API_URL the placeholder stays and no request is made
 * (AC-04.10); the route is wrapped in RequireAuth only when the API is configured (App.tsx). The page is shown only
 * to members of `admin` (token groups, display only — the API enforces the group).
 */
export function ChatPage() {
  if (!isApiConfigured) return <ComingLater title="Chat" />
  return <AdminOnlyChat />
}

function AdminOnlyChat() {
  const groups = useGroups()
  if (groups.isPending) return <p className="status">Loading…</p>
  if (!groups.data?.includes('admin')) {
    return (
      <section className="card card-full">
        <h1>AI search</h1>
        <p className="message message-error">You do not have access to this page.</p>
      </section>
    )
  }
  return <ChatSearch />
}

function ChatSearch() {
  const [text, setText] = useState('')
  /** last sent trimmed text; null = nothing sent yet */
  const [sent, setSent] = useState<string | null>(null)
  const chat = useChat(sent)
  useSignOutOnUnauthorized(chat.error)

  // Debounce (spec 13 Behaviour 2): vector mode only; restarts on every change; Search cancels it by updating `sent`.
  useEffect(() => {
    if (chatMode(text) === 'sql') return undefined
    const timer = window.setTimeout(() => {
      if (shouldAutoSend(text, sent)) setSent(text.trim())
    }, DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [text, sent])

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canSubmit(text)) return
    const trimmed = text.trim()
    if (trimmed !== sent) setSent(trimmed)
    else if (chat.isStale || chat.isError) void chat.refetch()
  }

  const errorStatus = chat.error instanceof ApiError ? chat.error.status : undefined
  const errorMessage = chat.isError && !chat.isFetching ? chatErrorMessage(errorStatus) : null
  const result = chat.isError ? undefined : chat.data

  return (
    <section className="card card-full">
      <h1>AI search</h1>
      <form className="form" onSubmit={onSubmit}>
        <div className="field">
          <label htmlFor="chat-query">Question</label>
          <input
            id="chat-query"
            type="text"
            maxLength={MAX_QUERY_LENGTH}
            autoComplete="off"
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
        </div>
        <p className="muted">
          Find similar users: type a profile, e.g.{' '}
          <em>which users are similar to gender: female; birth year: 1990; country: Poland</em>. Statistics: start
          with <strong>sql</strong>, e.g.{' '}
          <em>sql how many users aged 25 to 35 live in Poland and weigh more than 70 kg</em> — press Search.
        </p>
        <div>
          <button type="submit" className="button-primary">
            Search
          </button>
        </div>
      </form>
      {chat.isFetching && <p className="status">Searching…</p>}
      {errorMessage && (
        <p role="alert" className="message message-error">
          {errorMessage}
        </p>
      )}
      {result && <ChatResult data={result} busy={chat.isFetching} />}
    </section>
  )
}

function ChatResult({ data, busy }: { data: ChatResponse; busy: boolean }) {
  return (
    <div aria-busy={busy}>
      {data.rowCount === 0 && <p className="muted">No matching rows.</p>}
      <p className="muted">{metaLine(data)}</p>
      {data.mode === 'sql' && data.sql && (
        <>
          <p className="muted">Executed SQL</p>
          <pre aria-label="Executed SQL">{data.sql}</pre>
        </>
      )}
      {data.rowCount > 0 && (
        <div className="table-scroll">
          <table className="data-table" aria-busy={busy}>
            <thead>
              <tr>
                {data.columns.map((column, index) => (
                  // SQL-mode labels may repeat (e.g. two count(*)), so the position is part of the key
                  <th key={`${index}-${column}`} scope="col">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.rows.map((row, rowIndex) => (
                // rows have no id in SQL mode; the list is replaced as a whole per response, never reordered
                <tr key={rowIndex}>
                  {row.map((cell, index) => (
                    <td key={`${index}-${data.columns[index]}`}>{formatCell(cell, data.columns[index] ?? '')}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
