import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { endpoints } from '../api/client'

const PAGE_SIZE = 20

export function AdminPage() {
  const [page, setPage] = useState(0)
  const users = useQuery({
    queryKey: ['admin-users', page],
    queryFn: () => endpoints.users(page, PAGE_SIZE),
    placeholderData: keepPreviousData,
  })
  const totalPages = users.data ? Math.max(1, Math.ceil(users.data.total / PAGE_SIZE)) : 1

  return (
    <section>
      <h1>Users</h1>
      {users.isError && <p className="error">{users.error.message}</p>}
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Email</th>
            <th>Username</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {users.data?.items.map((u) => (
            <tr key={u.id}>
              <td>{u.id}</td>
              <td>{u.email}</td>
              <td>{u.username ?? '—'}</td>
              <td>{new Date(u.createdAt).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="row">
        <button disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
          Prev
        </button>
        <span>
          {page + 1} / {totalPages}
        </span>
        <button disabled={page + 1 >= totalPages} onClick={() => setPage((p) => p + 1)}>
          Next
        </button>
      </div>
    </section>
  )
}
