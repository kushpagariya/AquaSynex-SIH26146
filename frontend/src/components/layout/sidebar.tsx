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
  Shield,
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
    title: "ALERTS",
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
  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-[#262626] bg-[#171717] select-none text-neutral-200 font-sans">
      {/* Navigation Sections */}
      <nav className="flex flex-1 flex-col gap-5 overflow-y-auto px-2.5 py-4">
        {navSections.map((section) => (
          <div key={section.title} className="space-y-0.5">
            <p className="px-3 text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">
              {section.title}
            </p>
            <div className="flex flex-col gap-0.5">
              {section.items.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    cn(
                      "group flex items-center gap-2.5 rounded px-3 py-1.5 text-xs font-medium transition-colors",
                      isActive
                        ? "bg-[#252525] text-white font-semibold border-l-2 border-[#1E4D7B]"
                        : "text-neutral-400 hover:bg-[#202020] hover:text-neutral-200",
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      <Icon
                        className={cn(
                          "size-3.5 shrink-0",
                          isActive ? "text-[#5A87B8]" : "text-neutral-400 group-hover:text-neutral-200",
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

      {/* Quiet Session Footer */}
      <div className="border-t border-[#242424] px-4 py-3 text-[10px] text-neutral-400">
        <p className="font-mono uppercase tracking-wider">OFFLINE ENGINE</p>
        <p className="text-neutral-400 mt-0.5 font-sans">DuckDB • XGBoost • TreeSHAP</p>
      </div>
    </aside>
  )
}
