import { useEffect, useState } from 'react'
import { fetchOAuthCredentials, deleteOAuthCredential, type OAuthCredential } from '../lib/api'

export default function OAuthCredentials() {
  const [credentials, setCredentials] = useState<OAuthCredential[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadCredentials()
  }, [])

  async function loadCredentials() {
    try {
      setLoading(true)
      const data = await fetchOAuthCredentials('youtube')
      setCredentials(data)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(oauthId: number) {
    if (!confirm('Delete this OAuth credential?')) return
    try {
      await deleteOAuthCredential(oauthId)
      await loadCredentials()
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Delete failed')
    }
  }

  if (loading) return <div className="p-4">Loading...</div>
  if (error) return <div className="p-4 text-red-500">{error}</div>

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">OAuth Credentials</h1>
      
      {credentials.length === 0 ? (
        <p className="text-gray-500">No OAuth credentials stored.</p>
      ) : (
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-2">Account Name</th>
              <th className="text-left py-2">Platform</th>
              <th className="text-left py-2">Updated</th>
              <th className="text-left py-2">Status</th>
              <th className="text-left py-2">Linked Accounts</th>
              <th className="text-left py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {credentials.map((cred) => (
              <tr key={cred.oauth_id} className="border-b border-gray-100">
                <td className="py-3">{cred.account_name}</td>
                <td className="py-3">{cred.platform}</td>
                <td className="py-3">{new Date(cred.updated_at).toLocaleDateString()}</td>
                <td className="py-3">
                  {cred.has_token ? (
                    <span className="text-green-600">Connected</span>
                  ) : (
                    <span className="text-gray-400">No Token</span>
                  )}
                </td>
                <td className="py-3">
                  {cred.linked_account_ids.length > 0 ? (
                    <span>{cred.linked_account_ids.length} linked</span>
                  ) : (
                    <span className="text-gray-400">None</span>
                  )}
                </td>
                <td className="py-3">
                  <button
                    onClick={() => handleDelete(cred.oauth_id)}
                    className="text-red-600 hover:text-red-800 text-sm"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}