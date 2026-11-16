import { useState } from 'react'
import { ADMIN_USERS_PAGE_SIZE, ApiError, type Page, type User } from '../api/client'
import { useAdminUsers, useSignOutOnUnauthorized } from '../api/queries'
import { USER_COLUMNS, paging, selectAdminView, userCells } from '../admin/view'
import { isApiConfigured } from '../config/amplify'
import { ComingLater } from './ComingLater'

/**
 * /admin (spec 09): read-only users table with paging for administrators. Without VITE_API_URL the Week 2
 * placeholder stays and no request is made (AC-04.10); the route is wrapped in RequireAuth only when the API is
 * configured (App.tsx). The API enforces the group; a non-admin gets 403 → no-access text.
 */
export function AdminPage() {
  if (!isApiConfigured) return <ComingLater title="Users" />
  return <AdminUsers />
}

function AdminUsers() {
  const [page, setPage] = useState(0)
  const users = useAdminUsers(page)
  useSignOutOnUnauthorized(users.error)

  const errorStatus = users.error instanceof ApiError ? users.error.status : undefined
  const view = selectAdminView(true, { status: users.status, errorStatus, data: users.data })

  return (
    <section className="card card-full">
      <h1>Users</h1>
      {view === 'loading' && <p className="status">Loading…</p>}
      {view === 'forbidden' && <p className="message message-error">You do not have access to this page.</p>}
      {view === 'error' && (
        <>
          <p role="alert" className="message message-error">
            Users could not be loaded.
          </p>
          <button type="button" onClick={() => void users.refetch()} disabled={users.isFetching}>
            {users.isFetching ? 'Retrying…' : 'Retry'}
          </button>
        </>
      )}
      {view === 'empty' && <p className="muted">No users yet.</p>}
      {view === 'data' && users.data && (
        <UsersTable
          data={users.data}
          busy={users.isPlaceholderData}
          onPage={setPage}
        />
      )}
    </section>
  )
}

interface UsersTableProps {
  data: Page<User>
  /** the previous page is shown while the next one loads */
  busy: boolean
  onPage: (page: number) => void
}

function UsersTable({ data, busy, onPage }: UsersTableProps) {
  const line = paging(data.page, data.total, ADMIN_USERS_PAGE_SIZE)
  return (
    <>
      <div className="table-scroll">
        <table className="data-table" aria-busy={busy}>
          <thead>
            <tr>
              {USER_COLUMNS.map((column) => (
                <th key={column} scope="col">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.items.map((user) => (
              <tr key={user.id}>
                {userCells(user).map((cell, index) => (
                  <td key={USER_COLUMNS[index]}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="paging">
        <button type="button" onClick={() => onPage(data.page - 1)} disabled={busy || !line.hasPrevious}>
          Previous
        </button>
        <span className="muted">{line.text}</span>
        <button type="button" onClick={() => onPage(data.page + 1)} disabled={busy || !line.hasNext}>
          Next
        </button>
      </div>
    </>
  )
}
