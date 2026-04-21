import { useEffect, useState } from "react"
import { api, type JobSummary } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import { Loader2, CheckCircle, XCircle, Clock } from "lucide-react"

function StatusIcon({ status }: { status: string }) {
  if (status === "running")
    return <Loader2 className="w-3 h-3 animate-spin text-blue-500" />
  if (status === "done")
    return <CheckCircle className="w-3 h-3 text-green-500" />
  if (status === "failed")
    return <XCircle className="w-3 h-3 text-red-500" />
  return <Clock className="w-3 h-3 text-muted-foreground" />
}

export function JobTicker() {
  const [jobs, setJobs] = useState<JobSummary[]>([])

  useEffect(() => {
    const load = () => api.jobs.list().then(setJobs).catch(() => {})
    load()
    const interval = setInterval(load, 5000)
    return () => clearInterval(interval)
  }, [])

  const activeJobs = jobs.filter(j => j.status === "running" || j.status === "queued")
  const recentDone = jobs
    .filter(j => j.status === "done" || j.status === "failed")
    .slice(0, 3)

  return (
    <div className="h-10 border-t border-border bg-card/80 backdrop-blur-sm flex items-center px-4 gap-4 text-xs shrink-0">
      <span className="text-muted-foreground font-medium">Jobs:</span>

      {activeJobs.length === 0 && recentDone.length === 0 && (
        <span className="text-muted-foreground italic">No active jobs</span>
      )}

      {activeJobs.map(j => (
        <div key={j.id} className="flex items-center gap-1.5">
          <StatusIcon status={j.status} />
          <span className="truncate max-w-32">{j.niche}</span>
          {j.step && (
            <Badge variant="secondary" className="text-[10px] py-0 px-1.5">
              {j.step}
            </Badge>
          )}
        </div>
      ))}

      {recentDone.map(j => (
        <div key={j.id} className="flex items-center gap-1.5 opacity-60">
          <StatusIcon status={j.status} />
          <span className="truncate max-w-32">{j.niche}</span>
        </div>
      ))}
    </div>
  )
}
