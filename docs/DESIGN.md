# DESIGN.md — MoneyPrinterV2

> **For the LLM:** Read this fully before writing anything. The existing pipeline code (`classes/YouTube.py`, `status.py`, `db.py`, etc.) must not be restructured. You are building two surfaces on top of it: a CLI and a web UI backed by FastAPI.

---

## 0. What We're Building

Two interfaces, one backend:

| Interface | Use case |
|-----------|----------|
| **CLI** | Scripted runs, cron jobs, `run_24_7`, batch. Direct terminal invocation. |
| **Web UI** | Interactive control — generate, monitor, manage accounts, configure. Opened in browser. |

The existing `classes/`, `db.py`, `config.py`, `llm_generate.py`, `research.py` are untouched. FastAPI wraps them. The web UI talks to FastAPI. The CLI calls the same service layer directly.

---

## 1. Architecture

```
┌─────────────────────────────────┐     ┌──────────────────────────────┐
│           Web UI                │     │            CLI               │
│  React + shadcn/ui + Tailwind   │     │  cli.py (Click)              │
│  Vite dev server / static build │     │  python cli.py generate ...  │
└────────────┬────────────────────┘     └──────────┬───────────────────┘
             │ HTTP + WebSocket                     │ direct import
             ▼                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI (api/)                               │
│  /api/generate   /api/upload   /api/accounts   /api/settings        │
│  /ws/jobs/{id}  ← WebSocket stream for real-time progress           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                     Existing Service Layer                          │
│  classes/YouTube.py  │  db.py  │  config.py  │  llm_generate.py    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Project Structure

```
project/
│
├── api/                          # FastAPI backend
│   ├── main.py                   # App factory, router registration, CORS, static mount
│   ├── routers/
│   │   ├── generate.py           # POST /api/generate, GET /api/jobs
│   │   ├── upload.py             # POST /api/upload/{job_id}
│   │   ├── accounts.py           # CRUD /api/accounts
│   │   └── settings.py           # GET/PUT /api/settings
│   ├── ws.py                     # WebSocket /ws/jobs/{job_id}
│   ├── jobs.py                   # In-memory job registry (JobManager)
│   ├── pipeline_worker.py        # Runs YouTube pipeline in threadpool, emits events
│   └── models.py                 # Pydantic request/response models
│
├── web/                          # React frontend
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Generate.tsx      # PRIORITY
│   │   │   ├── Accounts.tsx
│   │   │   └── Settings.tsx
│   │   ├── components/
│   │   │   ├── PipelinePanel.tsx
│   │   │   ├── LogViewer.tsx
│   │   │   ├── JobTicker.tsx
│   │   │   └── StatCard.tsx
│   │   ├── hooks/
│   │   │   └── useJobSocket.ts   # WebSocket hook
│   │   └── lib/
│   │       └── api.ts            # Typed fetch wrappers
│   ├── components.json           # shadcn config
│   ├── tailwind.config.ts
│   └── vite.config.ts
│
├── cli.py                        # Click CLI entry point
├── classes/                      # EXISTING — do not modify
├── db.py                         # EXISTING — do not modify
├── config.py                     # EXISTING — do not modify
├── status.py                     # EXISTING — do not modify
└── requirements.txt
```

---

## 3. CLI

Simple, flat, no interactive prompts. Every option is a flag.

### Commands

```bash
# Generate a video
python cli.py generate --account "channel123" --niche "space mysteries" --language en

# Generate + upload in one shot
python cli.py generate --account "channel123" --niche "space mysteries" --upload

# Upload an existing video
python cli.py upload --account "channel123" --file ./output/video_047.mp4

# Run 24/7 mode
python cli.py run247 --account "channel123" --niche "space mysteries" --interval 3600

# Batch run
python cli.py batch --account "channel123" --niches-file niches.txt --count 5

# List accounts
python cli.py accounts list

# Start web UI
python cli.py serve [--port 8000] [--host 0.0.0.0] [--open]
```

### Implementation

```python
# cli.py
import click
from classes.YouTube import YouTube

@click.group()
def cli(): pass

@cli.command()
@click.option("--account", required=True)
@click.option("--niche", required=True)
@click.option("--language", default="en")
@click.option("--upload", is_flag=True, default=False)
def generate(account, niche, language, upload):
    """Generate a video from a niche prompt."""
    yt = YouTube(account)
    result = yt.generate_video(niche, language)
    if result and upload:
        yt.upload_video(result["path"])

@cli.command()
@click.option("--port", default=8000)
@click.option("--host", default="127.0.0.1")
@click.option("--open", "open_browser", is_flag=True, default=False)
def serve(port, host, open_browser):
    """Start the web UI."""
    import uvicorn, webbrowser, threading
    if open_browser:
        threading.Timer(1.2, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    uvicorn.run("api.main:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    cli()
```

**Rules:**
- No `input()` calls anywhere in the CLI. All inputs are flags.
- Output is plain text to stdout. Errors to stderr with non-zero exit code.
- `python cli.py serve --open` is the one command users run to start the web UI.

---

## 4. FastAPI Backend

### 4.1 Entry Point (`api/main.py`)

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from api.routers import generate, upload, accounts, settings
from api.ws import router as ws_router

app = FastAPI(title="MoneyPrinterV2")

app.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generate.router,  prefix="/api")
app.include_router(upload.router,    prefix="/api")
app.include_router(accounts.router,  prefix="/api")
app.include_router(settings.router,  prefix="/api")
app.include_router(ws_router)

# Serve built frontend in production
app.mount("/", StaticFiles(directory="web/dist", html=True), name="static")
```

### 4.2 Job Manager (`api/jobs.py`)

All pipeline runs are tracked as jobs. Jobs live in memory; metadata persists to `db.py`.

```python
import uuid
from dataclasses import dataclass, field
from enum import Enum
from asyncio import Queue

class JobStatus(str, Enum):
    queued   = "queued"
    running  = "running"
    done     = "done"
    failed   = "failed"
    cancelled = "cancelled"

@dataclass
class Job:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.queued
    account: str = ""
    niche: str = ""
    current_step: str = ""
    step_index: int = 0
    step_progress: float | None = None   # 0.0-1.0 or None
    output_path: str | None = None
    upload_url: str | None = None
    error: str | None = None
    events: Queue = field(default_factory=Queue)  # for WebSocket streaming

class JobManager:
    def __init__(self):
        self._jobs: dict[str, Job] = {}

    def create(self, account: str, niche: str) -> Job:
        job = Job(account=account, niche=niche)
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        return list(self._jobs.values())

job_manager = JobManager()  # singleton
```

### 4.3 Pipeline Worker (`api/pipeline_worker.py`)

```python
import asyncio
from classes.YouTube import YouTube
from api.jobs import job_manager, JobStatus

STEPS = ["topic", "script", "image_prompts", "images", "tts", "combine", "upload"]

async def run_job(job_id: str, language: str, for_kids: bool):
    job = job_manager.get(job_id)
    job.status = JobStatus.running

    def on_progress(step, status, progress=None, detail=""):
        job.current_step = step
        job.step_index = STEPS.index(step) if step in STEPS else 0
        job.step_progress = progress
        event = {"step": step, "status": status, "progress": progress, "detail": detail}
        # Put event into the job's queue — WebSocket handler drains it
        asyncio.get_event_loop().call_soon_threadsafe(job.events.put_nowait, event)

    def _run_sync():
        yt = YouTube(job.account)
        yt.set_progress_callback(on_progress)
        try:
            return yt.generate_video(job.niche, language, for_kids)
        finally:
            if hasattr(yt, "browser") and yt.browser:
                yt.browser.quit()

    try:
        result = await asyncio.to_thread(_run_sync)
        job.status = JobStatus.done
        job.output_path = result.get("path")
        job.upload_url = result.get("url")
        await job.events.put({"type": "done", "path": job.output_path, "url": job.upload_url})
    except Exception as e:
        job.status = JobStatus.failed
        job.error = str(e)
        await job.events.put({"type": "error", "error": str(e)})
```

### 4.4 WebSocket (`api/ws.py`)

```python
import asyncio, json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from api.jobs import job_manager

router = APIRouter()

@router.websocket("/ws/jobs/{job_id}")
async def job_stream(websocket: WebSocket, job_id: str):
    await websocket.accept()
    job = job_manager.get(job_id)
    if not job:
        await websocket.close(code=4004)
        return

    try:
        while True:
            event = await asyncio.wait_for(job.events.get(), timeout=30)
            await websocket.send_text(json.dumps(event))
            if event.get("type") in ("done", "error"):
                break
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    finally:
        await websocket.close()
```

### 4.5 Routers

**`api/routers/generate.py`**
```python
from fastapi import APIRouter, BackgroundTasks
from api.jobs import job_manager
from api.pipeline_worker import run_job
from api.models import GenerateRequest, JobResponse

router = APIRouter()

@router.post("/generate", response_model=JobResponse)
async def start_generation(req: GenerateRequest, bg: BackgroundTasks):
    job = job_manager.create(account=req.account, niche=req.niche)
    bg.add_task(run_job, job.id, req.language, req.for_kids)
    return JobResponse(job_id=job.id, status=job.status)

@router.get("/jobs")
async def list_jobs():
    return [{"id": j.id, "status": j.status, "niche": j.niche, "step": j.current_step}
            for j in job_manager.list()]

@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(404)
    return job
```

**`api/routers/accounts.py`**
```python
# GET    /api/accounts        → list all from db.py
# POST   /api/accounts        → add new account
# PUT    /api/accounts/{id}   → update
# DELETE /api/accounts/{id}   → delete
# POST   /api/accounts/{id}/test → test connection (runs sync in threadpool)
```

**`api/routers/settings.py`**
```python
# GET  /api/settings   → return current config (mask API key values)
# PUT  /api/settings   → write to config.json
```

### 4.6 Pydantic Models (`api/models.py`)

```python
from pydantic import BaseModel

class GenerateRequest(BaseModel):
    account: str
    niche: str
    language: str = "en"
    for_kids: bool = False

class JobResponse(BaseModel):
    job_id: str
    status: str

class AccountCreate(BaseModel):
    platform: str
    username: str
    profile_path: str

class SettingsUpdate(BaseModel):
    openai_api_key: str | None = None
    tavily_api_key: str | None = None
    exa_api_key: str | None = None
    pixabay_api_key: str | None = None
    tts_voice: str | None = None
    language: str | None = None
    headless: bool | None = None
    firefox_profile: str | None = None
    output_dir: str | None = None
```

---

## 5. Web UI

### 5.1 Stack

```
React 18 + TypeScript
Vite
Tailwind CSS v3
shadcn/ui          ← component library
lucide-react       ← icons (already included with shadcn)
react-router-dom   ← page routing
```

Install shadcn into the Vite project:
```bash
cd web
npx shadcn@latest init
```

`components.json` config:
```json
{
  "style": "default",
  "rsc": false,
  "tsx": true,
  "tailwind": { "baseColor": "zinc", "cssVariables": true },
  "aliases": { "components": "@/components", "utils": "@/lib/utils" }
}
```

Use **zinc** base color. Dark mode only — set `darkMode: "class"` in `tailwind.config.ts` and add `class="dark"` to `<html>`.

### 5.2 shadcn Components to Install

```bash
npx shadcn@latest add button card badge table input select
npx shadcn@latest add progress separator scroll-area dialog
npx shadcn@latest add toast alert form label switch
```

Use these. Do not install external component libraries. Do not write custom CSS for things shadcn already covers.

### 5.3 Layout (`App.tsx`)

```tsx
<div className="flex h-screen bg-background text-foreground">
  <Sidebar />                          {/* fixed left, w-52 */}
  <div className="flex flex-col flex-1 overflow-hidden">
    <main className="flex-1 overflow-y-auto p-6">
      <Outlet />                       {/* react-router page */}
    </main>
    <JobTicker />                      {/* fixed bottom bar, h-10 */}
  </div>
</div>
```

### 5.4 Sidebar

```tsx
const nav = [
  { label: "Dashboard",  path: "/",          icon: LayoutDashboard },
  { label: "Generate",   path: "/generate",  icon: Video },
  { label: "Accounts",   path: "/accounts",  icon: Users },
  { label: "Settings",   path: "/settings",  icon: Settings },
]
```

- `w-52`, `bg-card`, `border-r`. No collapsing in v1.
- Active link: `bg-accent text-accent-foreground` via shadcn's `cn()` utility.
- Each nav item is an `<a>` with `NavLink` from react-router.

### 5.5 Pages

#### Dashboard (`pages/Dashboard.tsx`)

Three `<Card>` stat cards (shadcn `Card` component), then a recent activity table.

```tsx
// Stat cards
<div className="grid grid-cols-3 gap-4 mb-6">
  <StatCard label="Videos Today"  value={stats.today} />
  <StatCard label="This Week"     value={stats.week} />
  <StatCard label="Active Accounts" value={stats.accounts} />
</div>

// Activity
<Card>
  <CardHeader><CardTitle>Recent Activity</CardTitle></CardHeader>
  <CardContent>
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Status</TableHead>
          <TableHead>Time</TableHead>
          <TableHead>Action</TableHead>
          <TableHead>Detail</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {activity.map(row => (
          <TableRow key={row.id}>
            <TableCell><StatusBadge status={row.status} /></TableCell>
            <TableCell className="text-muted-foreground text-sm">{row.time}</TableCell>
            <TableCell>{row.action}</TableCell>
            <TableCell className="text-muted-foreground">{row.detail}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  </CardContent>
</Card>
```

`StatusBadge` uses shadcn `Badge` with variant:
- `done` → `variant="default"` (green)
- `running` → `variant="secondary"` (blue)
- `failed` → `variant="destructive"` (red)
- `pending` → `variant="outline"` (gray)

---

#### Generate (`pages/Generate.tsx`) — PRIORITY

Two-column layout on wide screens, single column on narrow.

**Left column — form:**

```tsx
<Card>
  <CardHeader><CardTitle>Generate Video</CardTitle></CardHeader>
  <CardContent className="space-y-4">

    <div className="space-y-2">
      <Label>Account</Label>
      <Select onValueChange={setAccount}>
        <SelectTrigger><SelectValue placeholder="Select account" /></SelectTrigger>
        <SelectContent>
          {accounts.map(a => <SelectItem key={a.id} value={a.id}>{a.username}</SelectItem>)}
        </SelectContent>
      </Select>
    </div>

    <div className="space-y-2">
      <Label>Niche / Topic</Label>
      <Input placeholder="e.g. space mysteries for beginners"
             value={niche} onChange={e => setNiche(e.target.value)} />
    </div>

    <div className="space-y-2">
      <Label>Language</Label>
      <Select defaultValue="en" onValueChange={setLanguage}>
        <SelectTrigger><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem value="en">English</SelectItem>
          <SelectItem value="es">Spanish</SelectItem>
          {/* ... */}
        </SelectContent>
      </Select>
    </div>

    <div className="flex items-center gap-2">
      <Switch id="for-kids" checked={forKids} onCheckedChange={setForKids} />
      <Label htmlFor="for-kids">For kids</Label>
    </div>

    <Button className="w-full" onClick={handleGenerate} disabled={isRunning}>
      {isRunning ? "Generating..." : "Generate"}
    </Button>

    {isRunning && (
      <Button variant="destructive" className="w-full" onClick={handleStop}>
        Stop
      </Button>
    )}

  </CardContent>
</Card>
```

**Right column — pipeline + log:**

```tsx
<div className="space-y-4">
  <PipelinePanel steps={STEPS} currentStep={step} stepDetail={stepDetail} />
  <LogViewer lines={logLines} />
</div>
```

---

**`PipelinePanel` component:**

```tsx
const STEPS = [
  "topic", "script", "image prompts", "images", "tts", "combine", "upload"
]

function PipelinePanel({ currentStep, stepStates }) {
  return (
    <Card>
      <CardHeader><CardTitle className="text-sm font-medium">Pipeline</CardTitle></CardHeader>
      <CardContent className="space-y-2">
        {STEPS.map((step, i) => {
          const state = stepStates[step] ?? "pending"
          return (
            <div key={step} className="flex items-center gap-3 text-sm">
              <StepIcon state={state} />
              <span className={state === "pending" ? "text-muted-foreground" : ""}>
                {i + 1}. {step}
              </span>
              {stepStates[`${step}_detail`] && (
                <span className="text-muted-foreground ml-auto truncate max-w-48">
                  {stepStates[`${step}_detail`]}
                </span>
              )}
              {state === "running" && stepStates[`${step}_progress`] != null && (
                <Progress value={stepStates[`${step}_progress`] * 100}
                          className="w-24 h-1.5 ml-auto" />
              )}
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}

function StepIcon({ state }) {
  if (state === "done")    return <CheckCircle className="w-4 h-4 text-green-500 shrink-0" />
  if (state === "running") return <Loader2 className="w-4 h-4 text-blue-500 animate-spin shrink-0" />
  if (state === "failed")  return <XCircle className="w-4 h-4 text-red-500 shrink-0" />
  return <Circle className="w-4 h-4 text-muted-foreground shrink-0" />
}
```

**`LogViewer` component:**

```tsx
function LogViewer({ lines }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight
  }, [lines])

  return (
    <Card>
      <CardHeader className="py-2 px-4">
        <CardTitle className="text-sm font-medium">Log</CardTitle>
      </CardHeader>
      <ScrollArea className="h-64" ref={ref}>
        <CardContent className="p-4 space-y-0.5 font-mono text-xs">
          {lines.map((line, i) => (
            <div key={i} className={logColor(line.level)}>
              <span className="text-muted-foreground mr-2">{line.time}</span>
              {line.text}
            </div>
          ))}
        </CardContent>
      </ScrollArea>
    </Card>
  )
}

function logColor(level: string) {
  return {
    success: "text-green-500",
    warn:    "text-yellow-500",
    error:   "text-red-500",
    info:    "text-muted-foreground",
  }[level] ?? "text-foreground"
}
```

---

#### Accounts (`pages/Accounts.tsx`)

shadcn `Table` with an action column. Detail shown in a shadcn `Dialog` (not inline panel).

```tsx
<div className="flex justify-between items-center mb-4">
  <h1 className="text-xl font-semibold">Accounts</h1>
  <Button onClick={() => setAddOpen(true)}>Add Account</Button>
</div>

<Card>
  <Table>
    <TableHeader>
      <TableRow>
        <TableHead>Platform</TableHead>
        <TableHead>Username</TableHead>
        <TableHead>Status</TableHead>
        <TableHead>Last Run</TableHead>
        <TableHead>Uploads</TableHead>
        <TableHead></TableHead>
      </TableRow>
    </TableHeader>
    <TableBody>
      {accounts.map(a => (
        <TableRow key={a.id}>
          <TableCell>{a.platform}</TableCell>
          <TableCell className="font-mono">{a.username}</TableCell>
          <TableCell><AccountBadge status={a.status} /></TableCell>
          <TableCell className="text-muted-foreground text-sm">{a.last_run}</TableCell>
          <TableCell>{a.upload_count}</TableCell>
          <TableCell>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon"><MoreHorizontal className="w-4 h-4" /></Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem onClick={() => testConnection(a.id)}>Test Connection</DropdownMenuItem>
                <DropdownMenuItem onClick={() => editAccount(a)}>Edit</DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem className="text-destructive" onClick={() => deleteAccount(a.id)}>
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </TableCell>
        </TableRow>
      ))}
    </TableBody>
  </Table>
</Card>
```

Add/edit account via `Dialog` with a `Form` using shadcn's form primitives (react-hook-form + zod).

---

#### Settings (`pages/Settings.tsx`)

Sections separated by `<Separator />`. API key inputs use `type="password"` with a show/hide toggle button (Eye icon from lucide).

```tsx
<div className="space-y-8 max-w-2xl">
  <div>
    <h2 className="text-lg font-semibold mb-4">API Keys</h2>
    <Card>
      <CardContent className="space-y-4 pt-6">
        <ApiKeyField label="OpenAI"   name="openai_api_key"   />
        <ApiKeyField label="Tavily"   name="tavily_api_key"   />
        <ApiKeyField label="Exa"      name="exa_api_key"      />
        <ApiKeyField label="Pixabay"  name="pixabay_api_key"  />
      </CardContent>
    </Card>
  </div>

  <Separator />

  <div>
    <h2 className="text-lg font-semibold mb-4">Generation Defaults</h2>
    <Card>
      <CardContent className="space-y-4 pt-6">
        {/* LLM provider select, TTS voice select, language select */}
        {/* Headless switch */}
      </CardContent>
    </Card>
  </div>

  <Separator />

  <div>
    <h2 className="text-lg font-semibold mb-4">Paths</h2>
    <Card>
      <CardContent className="space-y-4 pt-6">
        {/* Firefox profile, imagemagick, output dir */}
        {/* Input + folder icon button each */}
      </CardContent>
    </Card>
  </div>

  <Button onClick={handleSave}>Save Settings</Button>
</div>
```

---

### 5.6 WebSocket Hook (`hooks/useJobSocket.ts`)

```typescript
import { useEffect, useState, useCallback } from "react"

type StepState = Record<string, "pending" | "running" | "done" | "failed">
type LogLine = { time: string; level: string; text: string }

export function useJobSocket(jobId: string | null) {
  const [stepStates, setStepStates] = useState<StepState>({})
  const [logLines, setLogLines] = useState<LogLine[]>([])
  const [isDone, setIsDone] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!jobId) return
    const ws = new WebSocket(`ws://localhost:8000/ws/jobs/${jobId}`)

    ws.onmessage = (e) => {
      const event = JSON.parse(e.data)

      if (event.type === "done") {
        setIsDone(true)
        return
      }
      if (event.type === "error") {
        setError(event.error)
        return
      }
      if (event.step && event.status) {
        setStepStates(prev => ({ ...prev, [event.step]: event.status }))
        if (event.detail) {
          setStepStates(prev => ({ ...prev, [`${event.step}_detail`]: event.detail }))
        }
        if (event.progress != null) {
          setStepStates(prev => ({ ...prev, [`${event.step}_progress`]: event.progress }))
        }
      }
      if (event.log) {
        setLogLines(prev => [...prev.slice(-499), {
          time: new Date().toLocaleTimeString(),
          level: event.log.level,
          text: event.log.text,
        }])
      }
    }

    ws.onerror = () => setError("WebSocket connection failed")

    return () => ws.close()
  }, [jobId])

  return { stepStates, logLines, isDone, error }
}
```

---

### 5.7 API Client (`lib/api.ts`)

```typescript
const BASE = "http://localhost:8000/api"

export const api = {
  generate: (body: GenerateRequest) =>
    fetch(`${BASE}/generate`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body) }).then(r => r.json()),

  accounts: {
    list:   ()         => fetch(`${BASE}/accounts`).then(r => r.json()),
    create: (body)     => fetch(`${BASE}/accounts`, { method: "POST", ... }).then(r => r.json()),
    delete: (id)       => fetch(`${BASE}/accounts/${id}`, { method: "DELETE" }),
    test:   (id)       => fetch(`${BASE}/accounts/${id}/test`, { method: "POST" }).then(r => r.json()),
  },

  settings: {
    get: ()     => fetch(`${BASE}/settings`).then(r => r.json()),
    put: (body) => fetch(`${BASE}/settings`, { method: "PUT", ... }).then(r => r.json()),
  },
}
```

---

## 6. YouTube.py Modification — Minimal

Add two methods. Touch nothing else.

```python
class YouTube:
    def __init__(self, account):
        # existing code unchanged
        self._progress_callback = None

    def set_progress_callback(self, cb):
        self._progress_callback = cb

    def _progress(self, step: str, status: str, progress: float | None = None, detail: str = ""):
        if self._progress_callback:
            self._progress_callback(step, status, progress, detail)
```

Insert `self._progress(step, "started")` and `self._progress(step, "complete", detail=...)` at the transition of each of the 7 major steps only. The 251 `status.*` calls stay — they are routed to the web log by the pipeline worker intercepting stdout, or left as terminal output in CLI mode.

---

## 7. Development Workflow

```bash
# 1. Install backend deps
pip install fastapi uvicorn[standard] click

# 2. Install frontend deps
cd web && npm install

# 3. Run both in dev mode
# Terminal 1
uvicorn api.main:app --reload --port 8000

# Terminal 2
cd web && npm run dev   # Vite on :5173, proxied to :8000

# 4. Production: build frontend, serve via FastAPI
cd web && npm run build
python cli.py serve --open
```

Vite proxy config in `vite.config.ts`:
```typescript
server: {
  proxy: {
    "/api": "http://localhost:8000",
    "/ws":  { target: "ws://localhost:8000", ws: true },
  }
}
```

---

## 8. Dependencies

```
# requirements.txt additions
fastapi>=0.110
uvicorn[standard]>=0.27
click>=8.1
pydantic>=2.0
```

```
# web/package.json additions (via shadcn init + add)
react, react-dom, react-router-dom
@radix-ui/* (installed by shadcn)
tailwindcss, class-variance-authority, clsx, tailwind-merge
lucide-react
```

---

## 9. Baseline — Fix These First

| # | Problem | Fix |
|---|---|---|
| 1 | Pipeline blocks server | `asyncio.to_thread()` in `run_job()` |
| 2 | No real-time progress | WebSocket queue draining from `on_progress` callback |
| 3 | Browser never closes | `finally: yt.browser.quit()` in `_run_sync` |
| 4 | Cancel does nothing | Add `cancel_event` check in pipeline worker; `DELETE /api/jobs/{id}` |
| 5 | Frontend not served | `StaticFiles` mount in `api/main.py` pointing to `web/dist` |
| 6 | CORS errors in dev | Vite proxy config routes `/api` and `/ws` correctly |
| 7 | Settings expose keys | `GET /api/settings` masks values with `****`, only writes on PUT |

---

## 10. Instructions for the LLM

1. **Read the entire document before writing any code.**
2. **Do not modify any file in `classes/`, `db.py`, `config.py`, `status.py`** beyond the two-method addition to `YouTube.py` in Section 6.
3. **Section 9 is your first task.** Baseline before features.
4. **All shadcn components must be installed via `npx shadcn@latest add <name>`.** Do not copy-paste component code manually.
5. **Dark mode only.** Set `class="dark"` on `<html>` and never write light-mode variants.
6. **The WebSocket is the only real-time channel.** Do not poll `/api/jobs/{id}` in a `setInterval`.
7. **Generate page is priority.** Dashboard, Accounts, Settings can be stubs if needed. Generate must be fully functional.
8. **State what you implemented, what you left as a stub, and what you need from the user** at the end of each session.
9. **If `db.py` schema or `status.py` function signatures are unclear, say so.** Do not guess.
