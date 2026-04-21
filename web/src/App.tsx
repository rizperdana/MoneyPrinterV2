import { BrowserRouter, Routes, Route } from "react-router-dom"
import { Toaster } from "@/components/ui/sonner"
import { Sidebar } from "@/components/Sidebar"
import { JobTicker } from "@/components/JobTicker"
import Dashboard from "@/pages/Dashboard"
import Generate from "@/pages/Generate"
import Accounts from "@/pages/Accounts"
import Settings from "@/pages/Settings"
import Videos from "@/pages/Videos"
import OAuthCredentials from "@/pages/OAuthCredentials"

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-background text-foreground">
        <Sidebar />
        <div className="flex flex-col flex-1 overflow-hidden">
          <main className="flex-1 overflow-y-auto p-6">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/generate" element={<Generate />} />
              <Route path="/accounts" element={<Accounts />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/videos" element={<Videos />} />
              <Route path="/oauth-credentials" element={<OAuthCredentials />} />
            </Routes>
          </main>
          <JobTicker />
        </div>
      </div>
      <Toaster richColors position="bottom-right" />
    </BrowserRouter>
  )
}
