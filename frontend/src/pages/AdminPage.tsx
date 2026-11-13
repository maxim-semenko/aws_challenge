import { ComingLater } from './ComingLater'

/**
 * /admin: the users list is Week 3 (curriculum); the Week 2 API has only GET /api/me and GET /api/admin/ping
 * (spec 05). No request in Week 2, regardless of VITE_API_URL (owner request 2026-11-13).
 */
export function AdminPage() {
  return <ComingLater title="Users" />
}
