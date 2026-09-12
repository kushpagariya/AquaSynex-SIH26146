import { NavLink } from "react-router-dom"
import {
  LayoutDashboard,
  Database,
  Bell,
  Fingerprint,
  ShieldAlert,
} from "lucide-react"
import { cn } from "@/lib/utils"

const nav = [
  { to: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { to: "/dataset", label: "Dataset", icon: Database },
  { to: "/alerts", label: "Alerts", icon: Bell },
  { to: "/investigation", label: "Investigate", icon: Fingerprint },
]

export function Sidebar() {
  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-line bg-panel">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <span className="grid size-8 place-items-center rounded-md border border-accent/30 bg-accent-soft text-accent">
          <ShieldAlert className="size-4.5" />
        </span>
        <div className="leading-tight">
          <p className="text-sm font-semibold tracking-tight text-fg">
            BTC INVESTIGATOR
          </p>
          <p className="text-[10px] uppercase tracking-widest text-fg-subtle">
            Forensics Terminal
          </p>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1 px-3 py-2">
        {nav.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                "group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-accent-soft text-accent"
                  : "text-fg-muted hover:bg-panel-2 hover:text-fg",
              )
            }
          >
            {({ isActive }) => (
              <>
                <Icon
                  className={cn(
                    "size-4.5",
                    isActive ? "text-accent" : "text-fg-subtle group-hover:text-fg",
                  )}
                />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="mx-3 mb-4 mt-2 border-t border-line pt-4">
        <div className="flex items-center gap-2 rounded-md bg-panel-2 px-3 py-2">
          <span className="relative flex size-2">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-risk-low/60" />
            <span className="relative inline-flex size-2 rounded-full bg-risk-low" />
          </span>
          <span className="text-xs text-fg-muted">
            System: <span className="font-medium text-fg">Offline</span>
          </span>
        </div>
      </div>
    </aside>
  )
}
