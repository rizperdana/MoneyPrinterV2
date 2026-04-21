const BASE = "/api"

export interface GenerateRequest {
  account: string
  niche: string
  language: string
  for_kids: boolean
  auto_upload: boolean
}

export interface JobSummary {
  id: string
  status: string
  account: string
  niche: string
  step: string
  step_index: number
  created_at: string
  output_path: string | null
  error: string | null
}

export interface AccountData {
  id: string
  platform: string
  username: string
  nickname: string | null
  topic: string | null
  oauth_token: string | null
  oauth_status: string | null
  created_at: string
}

export interface OAuthCredential {
  oauth_id: number
  account_name: string
  platform: string
  updated_at: string
  has_token: boolean
  linked_account_ids: number[]
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status}: ${text}`)
  }
  return res.json()
}

export interface ModelJobConfig {
  display_name: string
  available_models: string[]
  fallback_chain: string[]
  primary_model: string
}

export const api = {
  generate: (body: GenerateRequest) =>
    fetch(`${BASE}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(r => json<{ job_id: string; status: string }>(r)),

  jobs: {
    list: () => fetch(`${BASE}/jobs`).then(r => json<JobSummary[]>(r)),
    get: (id: string) => fetch(`${BASE}/jobs/${id}`).then(r => json<JobSummary>(r)),
    cancel: (id: string) =>
      fetch(`${BASE}/jobs/${id}`, { method: "DELETE" }).then(r => json<{ status: string }>(r)),
  },

  topics: () => fetch(`${BASE}/topics`).then(r => json<{ topics: { topic: string; niche: string; used_at: string }[] }>(r)),
  
  videos: () => fetch(`${BASE}/videos`).then(r => json<{ videos: { id: number; topic: string; title: string; platform: string; file_path: string; created_at: string }[] }>(r)),

  getVideo: (id: number) => fetch(`${BASE}/videos/${id}`).then(r => json<any>(r)),

  accounts: {
    list: () => fetch(`${BASE}/accounts`).then(r => json<AccountData[]>(r)),
    getLastTopic: (username: string) =>
      fetch(`${BASE}/accounts/${username}/last-topic`).then(r => json<{ topic: string | null; niche: string | null }>(r)),
    create: (body: { platform: string; username: string; nickname?: string; topic?: string }) =>
      fetch(`${BASE}/accounts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
}).then(r => json<{ id: string; status: string }>(r)),
    update: (id: string, body: Record<string, string>) =>
      fetch(`${BASE}/accounts/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }).then(r => json<{ status: string }>(r)),
    delete: (id: string) =>
      fetch(`${BASE}/accounts/${id}`, { method: "DELETE" }).then(r => json<{ status: string }>(r)),
    oauthStart: (accountId: string) =>
      fetch(`${BASE}/accounts/${accountId}/oauth/start`).then(r => json<{ account_id: string; auth_url: string; instruction: string }>(r)),
    oauthCallback: (accountId: string, code: string) =>
      fetch(`${BASE}/accounts/${accountId}/oauth/callback?code=${encodeURIComponent(code)}`).then(r => json<{ account_id: string; status: string; has_refresh_token: boolean }>(r)),
    oauthStatus: (accountId: string) =>
      fetch(`${BASE}/accounts/${accountId}/oauth/status`).then(r => json<{ account_id: string; authenticated: boolean; has_refresh_token: boolean }>(r)),
  },

  settings: {
    get: () => fetch(`${BASE}/settings`).then(r => json<Record<string, unknown>>(r)),
    put: (body: Record<string, unknown>) =>
      fetch(`${BASE}/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }).then(r => json<{ status: string; fields: string[] }>(r)),
    getModels: () => fetch(`${BASE}/settings/models`).then(r => json<Record<string, ModelJobConfig>>(r)),
},

  upload: (jobId: string, platform: string = "youtube") =>
    fetch(`${BASE}/upload/${jobId}?platform=${platform}`, { method: "POST" }).then(r =>
      json<{ status: string; job_id: string }>(r)
    ),

  uploadByVideoId: (videoId: number, platform: string = "youtube", accountId?: string) => {
    const params = new URLSearchParams({ platform })
    if (accountId) params.set('account_name', accountId)
    return fetch(`${BASE}/videos/${videoId}/upload?${params}`, { method: "POST" }).then(r =>
      json<{ status: string; video_id: number; platform: string; account: string; job_id: string }>(r)
    )
  },
}

export async function fetchOAuthCredentials(platform: string = "youtube"): Promise<OAuthCredential[]> {
  const res = await fetch(`${BASE}/oauth/credentials?platform=${platform}`)
  if (!res.ok) throw new Error("Failed to fetch OAuth credentials")
  return res.json()
}

export async function deleteOAuthCredential(oauthId: number): Promise<void> {
  const res = await fetch(`/auth/credentials/${oauthId}`, { method: "DELETE" })
  if (!res.ok) throw new Error("Failed to delete OAuth credential")
}
