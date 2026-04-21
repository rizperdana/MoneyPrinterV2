import { useEffect, useState } from "react"
import { api, fetchOAuthCredentials, deleteOAuthCredential, type AccountData, type OAuthCredential } from "@/lib/api"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { MoreHorizontal, Plus, Users, Key, Trash } from "lucide-react"

export default function Accounts() {
  const [accounts, setAccounts] = useState<AccountData[]>([])
  const [linkedOauthMap, setLinkedOauthMap] = useState<Record<string, number[]>>({});
  const [refresh, setRefresh] = useState(0);
  const [dialogOpen, setDialogOpen] = useState(false)
  const [oauthMessage, setOauthMessage] = useState<string | null>(null)
  const [form, setForm] = useState({
    platform: "youtube",
    username: "",
    nickname: "",
    topic: "",
  })
  const [editAccount, setEditAccount] = useState<AccountData | null>(null)
  const [editTopic, setEditTopic] = useState("")

  const [oauthCredsList, setOauthCredsList] = useState<OAuthCredential[]>([])

  const load = () => api.accounts.list().then(setAccounts).catch(() => {})

  const loadOauthCreds = () => fetchOAuthCredentials('youtube').then(setOauthCredsList).catch(() => {})

  useEffect(() => {
    load()
    loadOauthCreds()

    // Fetch linked status for all accounts
    api.accounts.list().then(accounts => {
      Promise.all(accounts.map((a: AccountData) => 
        fetch(`/api/accounts/${a.id}/oauth-links`).then(r => r.json()).catch(() => [])
      )).then((results: any[]) => {
        const map: Record<string, number[]> = {}
        results.forEach((links, idx) => {
          if (accounts[idx]) {
            map[accounts[idx].id] = links.map((l: any) => l.oauth_id)
          }
        })
        setLinkedOauthMap(map)
      })
    })
  }, [refresh])

  // Handle OAuth redirect params
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const oauthStatus = params.get('oauth')
    if (oauthStatus === 'success') {
      setOauthMessage('OAuth credential saved successfully!')
      window.history.replaceState({}, '', '/accounts')
    } else if (oauthStatus === 'error') {
      setOauthMessage('Failed to save OAuth credential. Please try again.')
      window.history.replaceState({}, '', '/accounts')
    }
    // Auto-dismiss after 5 seconds
    if (oauthStatus) {
      setTimeout(() => setOauthMessage(null), 5000)
    }
  }, [])

  const handleAdd = async () => {
    try {
      await api.accounts.create(form)
      setDialogOpen(false)
      setForm({ platform: "youtube", username: "", nickname: "", topic: "" })
      load()
    } catch (err) {
      console.error("Failed to add account:", err)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this account?")) return
    try {
      await api.accounts.delete(id)
      load()
    } catch (err) {
      console.error("Failed to delete:", err)
    }
  }

  const handleDeleteOAuth = async (oauthId: number) => {
    if (!confirm("Delete this OAuth credential?")) return
    try {
      await deleteOAuthCredential(oauthId)
      loadOauthCreds()
      load()
    } catch (err) {
      console.error("Failed to delete OAuth credential:", err)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
            <Users className="w-4 h-4 text-white" />
          </div>
          <h1 className="text-xl font-semibold">Accounts</h1>
        </div>
        <div className="flex gap-2">
          <Button onClick={async () => {
              const res = await fetch('/auth/google/url')
              const data = await res.json()
              window.open(data.url, '_blank')
            }}>
            OAuth
          </Button>
          <Button onClick={() => setDialogOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Add
          </Button>
        </div>
      </div>

      {oauthMessage && (
        <div className={`p-3 rounded-lg text-sm ${
          oauthMessage.includes('success') 
            ? 'bg-green-100 text-green-800 border border-green-300' 
            : 'bg-red-100 text-red-800 border border-red-300'
        }`}>
          {oauthMessage}
        </div>
      )}

      <Card>
        {accounts.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground text-sm">
            No accounts configured. Click "Add Account" to get started.
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Platform</TableHead>
                <TableHead>Username</TableHead>
                <TableHead>Nickname</TableHead>
                <TableHead>Topic</TableHead>
                <TableHead>OAuth</TableHead>
                <TableHead>Added</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {accounts.map((a) => (
                <TableRow key={a.id}>
                  <TableCell className="capitalize">{a.platform}</TableCell>
                  <TableCell className="font-mono text-sm">{a.username}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {a.nickname || "—"}
                  </TableCell>
                  <TableCell className="px-4 py-2 text-sm">{(a as any).topic || "—"}</TableCell>
                  <TableCell>
                    <select
                      className="h-6 text-xs px-1 rounded border"
                      value={linkedOauthMap[a.id]?.[0] || ""}
                      onChange={async (e) => {
                        const oauthId = parseInt(e.target.value)
                        const currentLinked = linkedOauthMap[a.id] || []
                        
                        if (!oauthId) {
                          // "No OAuth" selected - unlink any currently linked
                          for (const linkedId of currentLinked) {
                            await fetch(`/api/accounts/${a.id}/unlink-oauth/${linkedId}`, {
                              method: 'DELETE'
                            })
                          }
                          setRefresh(r => r + 1)
                          return
                        }
                        
                        if (currentLinked.includes(oauthId)) {
                          // Already linked - unlink it
                          await fetch(`/api/accounts/${a.id}/unlink-oauth/${oauthId}`, {
                            method: 'DELETE'
                          })
                          setRefresh(r => r + 1)
                          return
                        }
                        
                        // Not linked - link it
                        await fetch(`/api/accounts/${a.id}/link-oauth`, {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ oauth_id: oauthId })
                        })
                        setRefresh(r => r + 1)
                      }}
                    >
                      <option value="">No OAuth</option>
                      {oauthCredsList
                        .filter(c => c.platform === 'youtube')
                        .map(cred => (
                          <option key={cred.oauth_id} value={cred.oauth_id}>
                            {cred.account_name} {linkedOauthMap[a.id]?.includes(cred.oauth_id) ? '(linked)' : ''}
                          </option>
                        ))}
                    </select>
                  </TableCell>
                  <TableCell className="text-muted-foreground text-xs">
                    {a.created_at?.split(' ')[0] || "—"}
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <MoreHorizontal className="w-4 h-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent>
                        <DropdownMenuItem onClick={() => {
  setEditAccount(a)
  setEditTopic((a as any).topic || "")
}}>
  Edit
</DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          className="text-destructive"
                          onClick={() => handleDelete(a.id)}
                        >
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>

      {/* OAuth Credentials Section */}
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
            <Key className="w-4 h-4 text-white" />
          </div>
          <h2 className="text-lg font-semibold">OAuth Credentials</h2>
        </div>
        
        <Card>
          {oauthCredsList.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground text-sm">
              No OAuth credentials stored. Click "OAuth" above to connect Google account.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Account Name</TableHead>
                  <TableHead>Platform</TableHead>
                  <TableHead>Updated</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Linked Accounts</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {oauthCredsList.map((cred) => (
                  <TableRow key={cred.oauth_id}>
                    <TableCell className="font-mono text-sm">{cred.account_name}</TableCell>
                    <TableCell className="capitalize">{cred.platform}</TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {new Date(cred.updated_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      {cred.has_token ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          Connected
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                          No Token
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {cred.linked_account_ids.length > 0 ? (
                        <span>{cred.linked_account_ids.length} linked</span>
                      ) : (
                        "None"
                      )}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive hover:text-destructive"
                        onClick={() => handleDeleteOAuth(cred.oauth_id)}
                      >
                        <Trash className="w-4 h-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Card>
      </div>

      {/* Edit Account Dialog */}
      <Dialog open={!!editAccount} onOpenChange={() => setEditAccount(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Account</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Topic</label>
              <Input
                value={editTopic}
                onChange={e => setEditTopic(e.target.value)}
                placeholder="e.g. cool animals and plant facts"
              />
            </div>
          </div>
          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setEditAccount(null)}>Cancel</Button>
            <Button onClick={async () => {
              if (!editAccount) return
              await api.accounts.update(editAccount.id, {
                topic: editTopic,
              })
              setEditAccount(null)
              load()
            }}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Account Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Account</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Platform</Label>
              <Input
                value={form.platform}
                onChange={(e) => setForm({ ...form, platform: e.target.value })}
                placeholder="youtube"
              />
            </div>
            <div className="space-y-2">
              <Label>Username</Label>
              <Input
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
                placeholder="channel_name"
              />
            </div>
            <div className="space-y-2">
              <Label>Nickname (optional)</Label>
              <Input
                value={form.nickname}
                onChange={(e) => setForm({ ...form, nickname: e.target.value })}
                placeholder="My Channel"
              />
            </div>
            <div className="space-y-2">
              <Label>Topic (short, e.g. "Dark psychology tips")</Label>
              <Input
                value={form.topic}
                onChange={(e) => setForm({ ...form, topic: e.target.value })}
                placeholder="One main topic for this account"
              />
            </div>

          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleAdd} disabled={!form.username.trim()}>
              Add
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
