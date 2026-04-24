import { useEffect, useState, useRef } from "react"
import { api, type AccountData } from "@/lib/api"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Play, Upload, X, FileText, Loader2, Check } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Progress } from "@/components/ui/progress"

interface UploadProgress {
  step: string
  status: string
  progress: number
}

const STEP_LABELS: Record<string, string> = {
  navigating: "Navigating to YouTube Studio",
  selecting_file: "Selecting video file",
  uploading: "Uploading video to YouTube",
  metadata: "Setting title and description",
  visibility: "Setting visibility to Public",
  publishing: "Publishing video",
  complete: "Upload complete!",
}

export default function Videos() {
  const [videos, setVideos] = useState<any[]>([])
  const [accounts, setAccounts] = useState<AccountData[]>([])
  const [selectedAccountId, setSelectedAccountId] = useState<string>("")
  const [playingVideo, setPlayingVideo] = useState<string | null>(null)
  const [detailVideo, setDetailVideo] = useState<any | null>(null)
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null)
  const [uploadResult, setUploadResult] = useState<{success: boolean; url?: string; error?: string} | null>(null)
  const [pendingUpload, setPendingUpload] = useState<any | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const uploadJobIdRef = useRef<string | null>(null)
  const videosRef = useRef<() => void>(() => api.videos().then(d => setVideos(d.videos || [])).catch(() => {}))

  useEffect(() => {
    api.videos().then(d => setVideos(d.videos || [])).catch(() => {})
    api.accounts.list().then(d => setAccounts(d)).catch(() => {})
  }, [])

  const handlePlay = (filePath: string | null) => {
    if (filePath) {
      const fileName = filePath.split("/").pop()
      if (fileName) {
        setPlayingVideo(`/.mp/${fileName}`)
      }
    }
  }

  const handleUpload = (video: any) => {
    // Show account selection first
    setSelectedAccountId("")
    setPendingUpload(video)
  }

  const handleConfirmUpload = async () => {
    if (!pendingUpload) return

    const video = pendingUpload
    // Clear pending upload and close selection
    setPendingUpload(null)
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    // Reset state
    setUploadProgress(null)
    setUploadResult(null)

    try {
      // Get job ID from response - pass account_id if selected
      const response = await api.uploadByVideoId(video.id, video.platform || "youtube", selectedAccountId || undefined)
      const jobId = response.job_id

      if (jobId) {
        uploadJobIdRef.current = jobId

        // Connect to WebSocket for progress
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
        const wsUrl = `${protocol}//${window.location.host}/ws/jobs/${jobId}`

        const ws = new WebSocket(wsUrl)
        wsRef.current = ws

        ws.onopen = () => {
          console.log("Connected to job WebSocket")
        }

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)

            if (data.type === "upload_progress") {
              setUploadProgress({
                step: data.step,
                status: data.status,
                progress: data.progress || 0,
              })
            } else if (data.type === "upload_complete") {
              setUploadResult({ success: true, url: data.url })
              setUploadProgress({ step: "complete", status: "Upload complete!", progress: 100 })
              videosRef.current()
              ws.close()
            } else if (data.type === "upload_error") {
              setUploadResult({ success: false, error: data.error })
              ws.close()
            }
          } catch (e) {
            console.error("Failed to parse WebSocket message:", e)
          }
        }

        ws.onerror = (error) => {
          console.error("WebSocket error:", error)
        }

        ws.onclose = () => {
          wsRef.current = null
        }
      }
    } catch (err) {
      alert("Upload failed: " + err)
    }
  }

  const handleCloseUploadDialog = () => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setUploadProgress(null)
    setUploadResult(null)
    uploadJobIdRef.current = null
  }

  const handleShowDetail = async (video: any) => {
    try {
      const fullVideo = await api.getVideo(video.id)
      setDetailVideo(fullVideo)
    } catch (err) {
      console.error("Failed to fetch video details:", err)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-semibold">Videos Library</h1>
        <span className="text-muted-foreground">({videos.length} videos)</span>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All Generated Videos</CardTitle>
        </CardHeader>
        <CardContent>
          {videos.length === 0 ? (
            <p className="text-muted-foreground py-4 text-center">
              No videos yet. Go to{" "}
              <a href="/generate" className="text-primary underline">
                Generate
              </a>{" "}
              to create your first video.
            </p>
          ) : (
            <div className="grid gap-4">
              {videos.map((video) => (
                <div key={video.id} className="border rounded-lg p-4 space-y-2">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="font-medium">{video.title}</h3>
                        <p className="text-sm text-muted-foreground">
                         Niche: {video.niche || "?"} | Platform: {video.platform} | Locale: {video.locale || "?"}
                       </p>
                      {video.tags && (
                        <p className="text-sm text-muted-foreground mt-1">
                          Tags: {video.tags}
                        </p>
                      )}
                      {video.description && (
                        <p className="text-sm mt-2 line-clamp-2">{video.description}</p>
                      )}
                      <p className="text-xs text-muted-foreground mt-2">
                        Created: {new Date(video.created_at).toLocaleString()}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleShowDetail(video)}
                      >
                        <FileText className="w-4 h-4 mr-1" />
                        Detail
                      </Button>
                      {video.file_path && (
                        <>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handlePlay(video.file_path)}
                          >
                            <Play className="w-4 h-4 mr-1" />
                            Play
                          </Button>
                      {video.youtube_url ? (
                        <a
                          href={video.youtube_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 px-3 py-1.5 text-sm border border-green-500 text-green-600 rounded hover:bg-green-50"
                        >
                          <Check className="w-4 h-4" /> Uploaded
                        </a>
                      ) : (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleUpload(video)}
                        >
                          <Upload className="w-4 h-4 mr-1" />
                          Upload
                        </Button>
                      )}
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Video player dialog */}
      <Dialog open={!!playingVideo} onOpenChange={() => setPlayingVideo(null)}>
        <DialogContent className="max-w-[90vw] max-h-[90vh] w-[90vw] h-[90vh]">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              Video Preview
              <Button variant="ghost" size="sm" onClick={() => setPlayingVideo(null)}>
                <X className="w-4 h-4" />
              </Button>
            </DialogTitle>
          </DialogHeader>
          {playingVideo && (
            <video controls autoPlay className="w-full h-full object-contain" src={playingVideo} />
          )}
        </DialogContent>
      </Dialog>

      {/* Video detail dialog */}
      <Dialog open={!!detailVideo} onOpenChange={() => setDetailVideo(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between pr-8">
              Video Details
              <Button variant="ghost" size="sm" onClick={() => setDetailVideo(null)}>
                <X className="w-4 h-4" />
              </Button>
            </DialogTitle>
          </DialogHeader>
          {detailVideo && (
            <div className="space-y-4 text-sm">
              <div>
                <h3 className="font-semibold text-base">{detailVideo.title}</h3>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-muted-foreground">Topic/Niche: </span>
                  <span>{detailVideo.niche || "?"}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Platform: </span>
                  <span>{detailVideo.platform}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Locale: </span>
                  <span>{detailVideo.locale || "?"}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Created: </span>
                  <span>{new Date(detailVideo.created_at).toLocaleString()}</span>
                </div>
              </div>

              <div>
                <h4 className="font-medium text-muted-foreground mb-1">Description</h4>
                <p className="bg-muted p-3 rounded-md">{detailVideo.description || "N/A"}</p>
              </div>

              <div>
                <h4 className="font-medium text-muted-foreground mb-1">Script</h4>
                <pre className="bg-muted p-3 rounded-md whitespace-pre-wrap text-xs max-h-64 overflow-y-auto">
{detailVideo.script || "N/A"}
                </pre>
              </div>

              <div>
                <h4 className="font-medium text-muted-foreground mb-1">Tags</h4>
                <p className="bg-muted p-3 rounded-md">{detailVideo.tags || "N/A"}</p>
              </div>

              <div>
                <h4 className="font-medium text-muted-foreground mb-1">File Path</h4>
                <p className="bg-muted p-3 rounded-md text-xs break-all">{detailVideo.file_path || "N/A"}</p>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Upload account selection dialog */}
      <Dialog open={!!pendingUpload} onOpenChange={(open) => !open && setPendingUpload(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Select Account</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Uploading: <span className="font-medium">{pendingUpload?.title}</span>
            </p>
            <Select value={selectedAccountId} onValueChange={setSelectedAccountId}>
              <SelectTrigger>
                <SelectValue placeholder="Select an account" />
              </SelectTrigger>
              <SelectContent>
                {accounts.map((account) => (
                  <SelectItem key={account.id} value={String(account.id)}>
                    {account.nickname || account.username} ({account.platform})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button 
              onClick={handleConfirmUpload} 
              className="w-full"
              disabled={!selectedAccountId}
            >
              Upload
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Upload progress dialog */}
      <Dialog open={!!uploadProgress || !!uploadResult} onOpenChange={handleCloseUploadDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>
              {uploadResult ? (uploadResult.success ? "Upload Complete" : "Upload Failed") : "Uploading to YouTube..."}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {uploadResult?.success ? (
              <div className="text-center space-y-4">
                <div className="text-green-600 text-lg font-medium">Video uploaded successfully!</div>
                <a
                  href={uploadResult.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 underline break-all"
                >
                  {uploadResult.url}
                </a>
                <Button onClick={handleCloseUploadDialog} className="w-full">
                  Done
                </Button>
              </div>
            ) : uploadResult?.error ? (
              <div className="text-center space-y-4">
                <div className="text-red-600">{uploadResult.error}</div>
                <Button onClick={handleCloseUploadDialog} className="w-full">
                  Close
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>{uploadProgress?.status || "Starting upload..."}</span>
                </div>
                <Progress value={uploadProgress?.progress || 0} />
                <p className="text-sm text-muted-foreground text-center">
                  {STEP_LABELS[uploadProgress?.step || ""] || "Processing..."}
                </p>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}