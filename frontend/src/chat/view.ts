import type { ChatCell, ChatResponse } from '../api/client'
import { MISSING } from '../profile/format'

/** Rules of the /chat page (spec 13 §Inputs, §Outputs). */
export const MAX_QUERY_LENGTH = 500
export const DEBOUNCE_MS = 800
export const MIN_AUTO_LENGTH = 3

export type ChatMode = 'sql' | 'vector'

const SQL_KEYWORD = /\bsql\b/i

/** `sql` when the trimmed text contains the whole word "sql" (any case), otherwise `vector` (same rule as spec 12). */
export function chatMode(text: string): ChatMode {
  return SQL_KEYWORD.test(text.trim()) ? 'sql' : 'vector'
}

/** Automatic (debounced) request: vector mode, ≥ 3 trimmed characters, not the last sent text. */
export function shouldAutoSend(text: string, lastSent: string | null): boolean {
  const trimmed = text.trim()
  return (
    trimmed.length >= MIN_AUTO_LENGTH &&
    trimmed.length <= MAX_QUERY_LENGTH &&
    chatMode(trimmed) === 'vector' &&
    trimmed !== lastSent
  )
}

/** Search / Enter: any trimmed text of 1…500 characters, both modes. */
export function canSubmit(text: string): boolean {
  const length = text.trim().length
  return length >= 1 && length <= MAX_QUERY_LENGTH
}

/** Error text by HTTP status (undefined = network error); 401 → null, the user is being signed out. */
export function chatErrorMessage(status: number | undefined): string | null {
  switch (status) {
    case 400:
      return 'The question could not be answered. Rephrase it.'
    case 401:
      return null
    case 403:
      return 'You do not have access to this page.'
    case 429:
      return 'The AI service is busy. Try again shortly.'
    case 502:
      return 'AI service not available — it is switched on only during working sessions.'
    default:
      return 'The search failed.'
  }
}

/** Cell text: null → "—", `distance` with 4 decimals, other numbers/booleans/strings as returned. */
export function formatCell(value: ChatCell, column: string): string {
  if (value === null || value === undefined) return MISSING
  if (typeof value === 'number') return column === 'distance' ? value.toFixed(4) : String(value)
  return String(value)
}

/** `<mode> · <rowCount> rows · <totalMs> ms`, plus "(first 100 rows)" when truncated. */
export function metaLine(response: ChatResponse): string {
  const line = `${response.mode} · ${response.rowCount} rows · ${response.timings.totalMs} ms`
  return response.truncated ? `${line} (first 100 rows)` : line
}
