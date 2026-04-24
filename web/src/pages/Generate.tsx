import { useState, useCallback, useEffect } from "react"
import { api, type AccountData } from "@/lib/api"
import { useJobSocket } from "@/hooks/useJobSocket"
import { PipelinePanel } from "@/components/PipelinePanel"
import { LogViewer } from "@/components/LogViewer"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Video, Square } from "lucide-react"

const LOCALES = [
  { value: "en-US", label: "English (en-US)" },
  { value: "es-ES", label: "Spanish (es-ES)" },
  { value: "fr-FR", label: "French (fr-FR)" },
  { value: "de-DE", label: "German (de-DE)" },
  { value: "pt-PT", label: "Portuguese (pt-PT)" },
  { value: "id-ID", label: "Indonesian (id-ID)" },
  { value: "ja-JP", label: "Japanese (ja-JP)" },
  { value: "ko-KR", label: "Korean (ko-KR)" },
  { value: "zh-CN", label: "Chinese (zh-CN)" },
  { value: "hi-IN", label: "Hindi (hi-IN)" },
]

export default function Generate() {
  const [accounts, setAccounts] = useState<AccountData[]>([])
  const [account, setAccount] = useState("auto")
  const [niche, setNiche] = useState("")
  const [locale, setLocale] = useState("en-US")
  const [forKids, setForKids] = useState(false)
  const [autoUpload, setAutoUpload] = useState(false)
  const [jobId, setJobId] = useState<string | null>(null)
  const [isRunning, setIsRunning] = useState(false)

  const { stepStates, logLines, isDone, error } = useJobSocket(jobId)

  // Load accounts on mount
  useEffect(() => {
    api.accounts.list().then(setAccounts).catch(() => {})
  }, [])

  // Auto-fill niche when account changes
  useEffect(() => {
    if (account && account !== "auto") {
      const acc = accounts.find((a) => String(a.id) === account)
      if (acc?.topic) {
        setNiche(acc.topic)
      }
    }
  }, [account, accounts])

  const handleGenerate = useCallback(async () => {
    if (!niche.trim()) return
    setIsRunning(true)
    try {
      const res = await api.generate({
        account,
        niche: niche.trim(),
        locale,
        for_kids: forKids,
        auto_upload: autoUpload,
      })
      setJobId(res.job_id)
    } catch (err) {
      console.error("Generate failed:", err)
      setIsRunning(false)
    }
  }, [account, niche, locale, forKids, autoUpload])

  const handleStop = useCallback(async () => {
    if (jobId) {
      try {
        await api.jobs.cancel(jobId)
      } catch (err) {
        console.error("Cancel failed:", err)
      }
    }
    setIsRunning(false)
  }, [jobId])

  // Reset when done/error
  if ((isDone || error) && isRunning) {
    setTimeout(() => setIsRunning(false), 100)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
          <Video className="w-4 h-4 text-white" />
        </div>
        <h1 className="text-xl font-semibold">Generate Video</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left column — Form */}
        <Card>
          <CardHeader>
            <CardTitle>Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Account</Label>
              <Select value={account} onValueChange={setAccount}>
                <SelectTrigger>
                  <SelectValue placeholder="Select account or use auto" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Auto (rotate accounts)</SelectItem>
                  {accounts.map((acc) => (
                    <SelectItem key={acc.id} value={String(acc.id)}>
                      {(acc.nickname || acc.username)} — {acc.topic || acc.platform}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Niche / Topic</Label>
              <Input
                placeholder="e.g. space mysteries for beginners"
                value={niche}
                onChange={(e) => setNiche(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !isRunning && handleGenerate()}
              />
            </div>

            <div className="space-y-2">
              <Label>Language</Label>
              <Select defaultValue="en-US" onValueChange={setLocale}>
              <SelectTrigger>
              <SelectValue />
              </SelectTrigger>
              <SelectContent>
              {LOCALES.map((l) => (
              <SelectItem key={l.value} value={l.value}>
              {l.label}
              </SelectItem>
              ))}
              </SelectContent>
              </Select>
            </div>

            <div className="flex items-center gap-2">
              <Switch
                id="for-kids"
                checked={forKids}
                onCheckedChange={setForKids}
              />
              <Label htmlFor="for-kids">For kids</Label>
            </div>

            <div className="flex items-center gap-2">
              <Switch
                id="auto-upload"
                checked={autoUpload}
                onCheckedChange={setAutoUpload}
              />
              <Label htmlFor="auto-upload">Auto-upload to YouTube</Label>
            </div>

            <Button
              className="w-full"
              onClick={handleGenerate}
              disabled={isRunning || !niche.trim()}
            >
              {isRunning ? (
                <>
                  <span className="animate-pulse mr-2">●</span>
                  Generating...
                </>
              ) : (
                "Generate"
              )}
            </Button>

            {isRunning && (
              <Button
                variant="destructive"
                className="w-full"
                onClick={handleStop}
              >
                <Square className="w-4 h-4 mr-2" />
                Stop
              </Button>
            )}

            {isDone && (
              <div className="p-3 rounded-md bg-green-500/10 border border-green-500/20 text-green-500 text-sm">
                ✅ Video generated successfully!
              </div>
            )}

            {error && !isDone && (
              <div className="p-3 rounded-md bg-red-500/10 border border-red-500/20 text-red-500 text-sm">
                ❌ {error}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Right column — Pipeline + Log */}
        <div className="space-y-4">
          <PipelinePanel stepStates={stepStates} />
          <LogViewer lines={logLines} />
        </div>
      </div>
    </div>
  )
}
