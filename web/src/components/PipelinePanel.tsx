import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { CheckCircle, Loader2, XCircle, Circle } from "lucide-react"
import type { StepStates } from "@/hooks/useJobSocket"

const STEPS = [
  "topic",
  "script",
  "metadata",
  "image_prompts",
  "images",
  "tts",
  "combine",
]

const STEP_LABELS: Record<string, string> = {
  topic: "Topic Research",
  script: "Script Writing",
  metadata: "Metadata & SEO",
  image_prompts: "Image Prompts",
  images: "Image Generation",
  tts: "Text-to-Speech",
  combine: "Video Assembly",
}

function StepIcon({ state }: { state: string }) {
  if (state === "done")
    return <CheckCircle className="w-4 h-4 text-green-500 shrink-0" />
  if (state === "running")
    return <Loader2 className="w-4 h-4 text-blue-500 animate-spin shrink-0" />
  if (state === "failed")
    return <XCircle className="w-4 h-4 text-red-500 shrink-0" />
  return <Circle className="w-4 h-4 text-muted-foreground shrink-0" />
}

interface PipelinePanelProps {
  stepStates: StepStates
}

export function PipelinePanel({ stepStates }: PipelinePanelProps) {
  return (
    <Card>
      <CardHeader className="py-3 px-4">
        <CardTitle className="text-sm font-medium">Pipeline</CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4 space-y-2">
        {STEPS.map((step, i) => {
          const state = stepStates[step] ?? "pending"
          const detail = stepStates[`${step}_detail`]
          const progress = stepStates[`${step}_progress`]

          return (
            <div key={step} className="flex items-center gap-3 text-sm">
              <StepIcon state={state} />
              <span
                className={
                  state === "pending" ? "text-muted-foreground" : "text-foreground"
                }
              >
                {i + 1}. {STEP_LABELS[step] || step}
              </span>
              {detail && (
                <span className="text-muted-foreground ml-auto truncate max-w-48 text-xs">
                  {detail}
                </span>
              )}
              {state === "running" && progress != null && (
                <Progress
                  value={parseFloat(progress) * 100}
                  className="w-24 h-1.5 ml-auto"
                />
              )}
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
