import { useEffect, useState } from "react"
import { NavLink } from "react-router-dom"
import {
  LayoutDashboard,
  Database,
  ArrowLeftRight,
  Users,
  Share2,
  Network,
  Bell,
  Activity,
  Fingerprint,
  BrainCircuit,
  ShieldAlert,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { getHealth } from "@/api"

interface NavSection {
  title: string
  items: {
    to: string
    label: string
    icon: React.ComponentType<{ className?: string }>
  }[]
}

const navSections: NavSection[] = [
  {
    title: "OVERVIEW",
    items: [{ to: "/dashboard", label: "Overview", icon: LayoutDashboard }],
  },
  {
    title: "DATA",
    items: [
      { to: "/dataset", label: "Dataset", icon: Database },
      { to: "/transactions", label: "Transactions", icon: ArrowLeftRight },
    ],
  },
  {
    title: "INTELLIGENCE",
    items: [
      { to: "/entities", label: "Entities", icon: Users },
      { to: "/graph", label: "Graph Explorer", icon: Share2 },
      { to: "/network", label: "Network Intelligence", icon: Network },
    ],
  },
  {
    title: "ALERTS & ANALYSIS",
    items: [
      { to: "/alerts", label: "Alerts", icon: Bell },
      { to: "/behaviors", label: "Behavior Analytics", icon: Activity },
    ],
  },
  {
    title: "INVESTIGATION",
    items: [{ to: "/investigation", label: "Investigate", icon: Fingerprint }],
  },
  {
    title: "SYSTEM",
    items: [{ to: "/model", label: "Model Insights", icon: BrainCircuit }],
  },
]

export function Sidebar() {
  const [healthStatus, setHealthStatus] = useState<"online" | "offline" | "checking">("checking")

  useEffect(() => {
    let mounted = true

    function check() {
      getHealth()
        .then((res) => {
          if (!mounted) return
          setHealthStatus(res.status === "healthy" ? "online" : "offline")
        })
        .catch(() => {
          if (!mounted) return
          setHealthStatus("offline")
        })
    }

    check()
    const interval = setInterval(check, 15000)

    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [])

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

      <nav className="flex flex-1 flex-col gap-4 overflow-y-auto px-3 py-2">
        {navSections.map((section) => (
          <div key={section.title} className="space-y-1">
            <p className="px-3 text-[10px] font-bold uppercase tracking-wider text-fg-subtle">
              {section.title}
            </p>
            <div className="flex flex-col gap-0.5">
              {section.items.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    cn(
                      "group flex items-center gap-2.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                      isActive
                        ? "bg-accent-soft text-accent border border-accent/20"
                        : "text-fg-muted hover:bg-panel-2 hover:text-fg",
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      <Icon
                        className={cn(
                          "size-4 shrink-0",
                          isActive ? "text-accent" : "text-fg-subtle group-hover:text-fg",
                        )}
                      />
                      <span className="truncate">{label}</span>
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="mx-3 mb-4 mt-2 border-t border-line pt-4">
        <div className="flex items-center gap-2 rounded-md bg-panel-2 px-3 py-2">
          <span className="relative flex size-2">
            {healthStatus === "online" ? (
              <>
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-risk-low/60" />
                <span className="relative inline-flex size-2 rounded-full bg-risk-low" />
              </>
            ) : healthStatus === "checking" ? (
              <span className="relative inline-flex size-2 rounded-full bg-risk-medium" />
            ) : (
              <span className="relative inline-flex size-2 rounded-full bg-risk-critical" />
            )}
          </span>
          <span className="text-xs text-fg-muted">
            System:{" "}
            <span
              className={cn(
                "font-medium",
                healthStatus === "online"
                  ? "text-risk-low"
                  : healthStatus === "checking"
                    ? "text-risk-medium"
                    : "text-risk-critical",
              )}
            >
              {healthStatus === "online"
                ? "Online"
                : healthStatus === "checking"
                  ? "Checking…"
                  : "Offline"}
            </span>
          </span>
        </div>
      </div>
    </aside>
  )
}
