import { NavLink } from "react-router-dom"
import { LayoutDashboard, Video, Users, Settings, FolderOpen } from "lucide-react"
import { cn } from "@/lib/utils"

const nav = [
  { label: "Dashboard", path: "/", icon: LayoutDashboard },
  { label: "Generate", path: "/generate", icon: Video },
  { label: "Videos", path: "/videos", icon: FolderOpen },
  { label: "Accounts", path: "/accounts", icon: Users },
  { label: "Settings", path: "/settings", icon: Settings },
]

export function Sidebar() {
  return (
    <aside className="w-52 bg-card border-r border-border flex flex-col shrink-0">
      {/* Logo */}
      <div className="h-14 flex items-center px-4 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
            <span className="text-white text-xs font-bold">M</span>
          </div>
          <span className="font-semibold text-sm tracking-tight">MoneyPrinter</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 px-2 space-y-0.5">
        {nav.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
              )
            }
          >
            <item.icon className="w-4 h-4 shrink-0" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-border">
        <p className="text-[10px] text-muted-foreground text-center">v2.0 • FastAPI + React</p>
      </div>
    </aside>
  )
}
