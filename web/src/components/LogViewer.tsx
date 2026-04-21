import { useRef, useEffect } from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import type { LogLine } from "@/hooks/useJobSocket"

function logColor(level: string) {
  return (
    {
      success: "text-green-500",
      warn: "text-yellow-500",
      error: "text-red-500",
      info: "text-muted-foreground",
    }[level] ?? "text-foreground"
  )
}

interface LogViewerProps {
  lines: LogLine[]
}

export function LogViewer({ lines }: LogViewerProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [lines])

  return (
    <Card>
      <CardHeader className="py-2 px-4">
        <CardTitle className="text-sm font-medium">Log</CardTitle>
      </CardHeader>
      <ScrollArea className="h-64">
        <CardContent className="p-4 space-y-0.5 font-mono text-xs">
          {lines.length === 0 && (
            <p className="text-muted-foreground italic">
              Waiting for pipeline events...
            </p>
          )}
          {lines.map((line, i) => (
            <div key={i} className={logColor(line.level)}>
              <span className="text-muted-foreground mr-2">{line.time}</span>
              {line.text}
            </div>
          ))}
          <div ref={bottomRef} />
        </CardContent>
      </ScrollArea>
    </Card>
  )
}
