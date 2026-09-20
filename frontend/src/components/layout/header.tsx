import { useEffect, useState } from "react"
import { Shield } from "lucide-react"
import { GlobalSearch } from "./global-search"
import { getHealth } from "@/api"

export function Header({ title }: { title: string }) {
  const [online, setOnline] = useState(true)

  useEffect(() => {
    let mounted = true
    getHealth()
      .then((res) => {
        if (mounted) setOnline(res.status === "healthy")
      })
      .catch(() => {
        if (mounted) setOnline(false)
      })
    return () => {
      mounted = false
    }
  }, [])

  return (
    <header className="flex h-11 w-full shrink-0 items-center justify-between border-b border-[#262626] bg-[#0D0D0D] px-4 text-white select-none z-40">
      {/* Left: Brand Identity */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="grid size-5 place-items-center rounded bg-[#173B63] text-white">
            <Shield className="size-3" />
          </span>
          <span className="font-sans text-xs font-bold uppercase tracking-wider text-neutral-200">
            TraceGrid
          </span>
        </div>
        <span className="text-neutral-700">/</span>
        <span className="font-sans text-[11px] font-medium tracking-wide text-neutral-400">
          BTC Investigator
        </span>
      </div>

      {/* Center: Minimal Global Search */}
      <div className="flex flex-1 justify-center px-4 max-w-md">
        <GlobalSearch />
      </div>

      {/* Right: System Status Only */}
      <div className="flex items-center gap-2 text-[11px] font-sans">
        <span
          className={`size-1.5 rounded-full ${
            online ? "bg-[#2F6B4F]" : "bg-[#A63D3D]"
          }`}
        />
        <span className="text-neutral-400 font-medium">
          {online ? "System Online" : "Disconnected"}
        </span>
      </div>
    </header>
  )
}
