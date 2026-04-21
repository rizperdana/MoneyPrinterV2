import { useEffect, useState, useCallback } from "react"

export type StepStatus = "pending" | "running" | "done" | "failed"
export type StepStates = Record<string, string>
export type LogLine = { time: string; level: string; text: string }

export function useJobSocket(jobId: string | null) {
  const [stepStates, setStepStates] = useState<StepStates>({})
  const [logLines, setLogLines] = useState<LogLine[]>([])
  const [isDone, setIsDone] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const reset = useCallback(() => {
    setStepStates({})
    setLogLines([])
    setIsDone(false)
    setError(null)
  }, [])

  useEffect(() => {
    if (!jobId) return

    reset()

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
    const host = window.location.host
    const ws = new WebSocket(`${protocol}//${host}/ws/jobs/${jobId}`)

    ws.onmessage = (e) => {
      const event = JSON.parse(e.data)

      if (event.type === "heartbeat") return

      if (event.type === "done") {
        setIsDone(true)
        setLogLines(prev => [
          ...prev,
          {
            time: new Date().toLocaleTimeString(),
            level: "success",
            text: `✅ Done! Output: ${event.path || "unknown"}`,
          },
        ])
        return
      }

      if (event.type === "error") {
        setError(event.error)
        setLogLines(prev => [
          ...prev,
          {
            time: new Date().toLocaleTimeString(),
            level: "error",
            text: `❌ Error: ${event.error}`,
          },
        ])
        return
      }

      if (event.type === "cancelled") {
        setError("Job cancelled")
        return
      }

      if (event.step && event.status) {
        setStepStates(prev => ({
          ...prev,
          [event.step]: event.status,
        }))
        if (event.detail) {
          setStepStates(prev => ({
            ...prev,
            [`${event.step}_detail`]: event.detail,
          }))
        }
        if (event.progress != null) {
          setStepStates(prev => ({
            ...prev,
            [`${event.step}_progress`]: String(event.progress),
          }))
        }

        // Add log line for step transitions
        if (event.status === "running" || event.status === "done") {
          setLogLines(prev => [
            ...prev.slice(-499),
            {
              time: new Date().toLocaleTimeString(),
              level: event.status === "done" ? "success" : "info",
              text: `${event.step}: ${event.status}${event.detail ? ` — ${event.detail}` : ""}`,
            },
          ])
        }
      }
    }

    ws.onerror = () => setError("WebSocket connection failed")

    return () => {
      ws.close()
    }
  }, [jobId, reset])

  return { stepStates, logLines, isDone, error, reset }
}
