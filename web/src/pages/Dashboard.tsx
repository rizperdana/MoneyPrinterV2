import { useEffect, useState, useRef } from "react"
import { api, type JobSummary } from "@/lib/api"
import { StatCard } from "@/components/StatCard"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Play, Upload, List, X, Video, Calendar, Users } from "lucide-react"

function StatusBadge({ status }: { status: string }) {
  const variant =
    status === "done"
      ? "default"
      : status === "running"
        ? "secondary"
        : status === "failed"
          ? "destructive"
          : "outline"

  return <Badge variant={variant}>{status}</Badge>
}

export default function Dashboard() {
  const [jobs, setJobs] = useState<JobSummary[]>([])
  const [videos, setVideos] = useState<any[]>([])
  const [playingVideo, setPlayingVideo] = useState<string | null>(null)
  const [uploadMenuJob, setUploadMenuJob] = useState<string | null>(null)
  const [uploadConfig, setUploadConfig] = useState<{ job: JobSummary; platform: string } | null>(null)
  const [showVideosList, setShowVideosList] = useState(false)
  const uploadMenuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const load = () => api.jobs.list().then(setJobs).catch(() => {})
    load()
    const interval = setInterval(load, 5000)
    return () => clearInterval(interval)
  }, [])

  // Close upload menu on click outside
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (uploadMenuRef.current && !uploadMenuRef.current.contains(e.target as Node)) {
        setUploadMenuJob(null)
      }
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [])

  // Load videos list
  const loadVideos = () => api.videos().then(d => setVideos(d.videos || [])).catch(() => {})

  const handlePlay = (outputPath: string | null) => {
    if (outputPath) {
      // Convert full path to URL path
      const fileName = outputPath.split("/").pop()
      if (fileName) {
        setPlayingVideo(`/.mp/${fileName}`)
      }
    }
  }

  const handleUploadClick = (job: JobSummary, platform: string) => {
    setUploadMenuJob(null)
    setUploadConfig({ job, platform })
  }

  const handleUploadConfirm = async () => {
    if (!uploadConfig) return
    try {
      await api.upload(uploadConfig.job.id, uploadConfig.platform)
      setUploadConfig(null)
      alert(`Upload to ${uploadConfig.platform} started!`)
    } catch (err) {
      alert("Upload failed: " + err)
    }
  }

  const handleShowVideos = () => {
    loadVideos()
    setShowVideosList(true)
  }

  const todayCount = jobs.filter((j) => {
    const d = new Date(j.created_at)
    const now = new Date()
    return d.toDateString() === now.toDateString() && j.status === "done"
  }).length

  const runningCount = jobs.filter((j) => j.status === "running").length

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Dashboard</h1>

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard label="Videos Today" value={todayCount} icon={Video} />
        <StatCard
          label="Total Jobs"
          value={jobs.length}
          icon={Calendar}
        />
        <StatCard
          label="Running Now"
          value={runningCount}
          icon={Users}
          trend={runningCount > 0 ? "Active pipeline" : "Idle"}
        />
      </div>

      {/* Activity table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Recent Activity</CardTitle>
          <Button variant="outline" size="sm" onClick={handleShowVideos}>
            <List className="w-4 h-4 mr-2" />
            Videos List
          </Button>
        </CardHeader>
        <CardContent>
          {jobs.length === 0 ? (
            <p className="text-muted-foreground text-sm py-4 text-center">
              No jobs yet. Go to{" "}
              <a href="/generate" className="text-primary underline">
                Generate
              </a>{" "}
              to create your first video.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Status</TableHead>
                  <TableHead>Time</TableHead>
                  <TableHead>Niche</TableHead>
                  <TableHead>Step</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {jobs.slice(0, 20).map((j) => (
                  <TableRow key={j.id}>
                    <TableCell>
                      <StatusBadge status={j.status} />
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {new Date(j.created_at).toLocaleTimeString()}
                    </TableCell>
                    <TableCell className="max-w-48 truncate">
                      {j.niche}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {j.step || "—"}
                    </TableCell>
                    <TableCell className="text-xs">
                      <div className="flex gap-1 relative">
                        {j.output_path && j.status === "done" && (
                          <>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handlePlay(j.output_path)}
                              title="Play video"
                            >
                              <Play className="w-3 h-3" />
                            </Button>
                            <div className="relative" ref={uploadMenuRef}>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setUploadMenuJob(uploadMenuJob === j.id ? null : j.id)}
                                title="Upload to platform"
                              >
                                <Upload className="w-3 h-3" />
                              </Button>
                              {uploadMenuJob === j.id && (
                                <div className="absolute right-0 top-6 z-50 bg-background border rounded-md shadow-lg py-1 min-w-32">
                                  <button
                                    className="w-full px-3 py-1.5 text-left text-sm hover:bg-accent"
                                    onClick={() => handleUploadClick(j, "youtube")}
                                  >
                                    YouTube
                                  </button>
                                  <button
                                    className="w-full px-3 py-1.5 text-left text-sm hover:bg-accent"
                                    onClick={() => handleUploadClick(j, "twitter")}
                                  >
                                    Twitter
                                  </button>
                                </div>
                              )}
                            </div>
                          </>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Video playback dialog */}
      <Dialog open={!!playingVideo} onOpenChange={() => setPlayingVideo(null)}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              Video Preview
              <Button variant="ghost" size="sm" onClick={() => setPlayingVideo(null)}>
                <X className="w-4 h-4" />
              </Button>
            </DialogTitle>
          </DialogHeader>
          {playingVideo && (
            <video
              controls
              autoPlay
              className="w-full aspect-video"
              src={playingVideo}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Upload config dialog */}
      <Dialog open={!!uploadConfig} onOpenChange={() => setUploadConfig(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Confirm Upload to {uploadConfig?.platform}</DialogTitle>
          </DialogHeader>
          {uploadConfig && (
            <div className="space-y-4">
              <div className="bg-muted p-3 rounded-md space-y-2">
                <p className="font-medium">Video Details:</p>
                <p className="text-sm"><span className="text-muted-foreground">Niche:</span> {uploadConfig.job.niche}</p>
                <p className="text-sm"><span className="text-muted-foreground">File:</span> {uploadConfig.job.output_path?.split("/").pop()}</p>
              </div>
              <div className="flex gap-2">
                <Button onClick={handleUploadConfirm} className="flex-1">
                  <Upload className="w-4 h-4 mr-2" />
                  Confirm Upload
                </Button>
                <Button variant="outline" onClick={() => setUploadConfig(null)}>
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Videos list dialog */}
      <Dialog open={showVideosList} onOpenChange={() => setShowVideosList(false)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>All Generated Videos</DialogTitle>
          </DialogHeader>
          {videos.length === 0 ? (
            <p className="text-muted-foreground py-4 text-center">No videos yet</p>
          ) : (
            <div className="space-y-3">
              {videos.map((v) => (
                <div key={v.id} className="border rounded-md p-3">
                  <p className="font-medium">{v.title}</p>
                  <p className="text-sm text-muted-foreground">Niche: {v.niche}</p>
                  <p className="text-sm text-muted-foreground">Platform: {v.platform}</p>
                  {v.tags && <p className="text-sm text-muted-foreground">Tags: {v.tags}</p>}
                  {v.description && <p className="text-sm mt-2">{v.description?.slice(0, 200)}...</p>}
                  <p className="text-xs text-muted-foreground mt-2">Created: {new Date(v.created_at).toLocaleString()}</p>
                </div>
              ))}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
