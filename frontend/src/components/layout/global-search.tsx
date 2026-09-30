import { useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Search, CornerDownLeft } from "lucide-react"
import { search, type SearchResult } from "@/data/service"
import { cn } from "@/lib/utils"

export function GlobalSearch() {
  const navigate = useNavigate()
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<SearchResult[]>([])
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let cancelled = false
    if (!query.trim()) {
      setResults([])
      return
    }
    const timer = setTimeout(() => {
      search(query).then((r) => {
        if (!cancelled) {
          setResults(r)
          setActive(0)
        }
      })
    }, 300)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [query])

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (!containerRef.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", onClick)
    return () => document.removeEventListener("mousedown", onClick)
  }, [])

  function go(result: SearchResult) {
    navigate(result.route)
    setQuery("")
    setOpen(false)
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.nativeEvent.isComposing || e.keyCode === 229) return
    if (!open || results.length === 0) return
    if (e.key === "ArrowDown") {
      e.preventDefault()
      setActive((a) => (a + 1) % results.length)
    } else if (e.key === "ArrowUp") {
      e.preventDefault()
      setActive((a) => (a - 1 + results.length) % results.length)
    } else if (e.key === "Enter") {
      e.preventDefault()
      go(results[active])
    } else if (e.key === "Escape") {
      setOpen(false)
    }
  }

  return (
    <div ref={containerRef} className="relative w-full max-w-sm">
      <div className="flex items-center gap-2 rounded border border-[#2A2A2A] bg-[#161616] px-2.5 py-1 focus-within:border-[#444] focus-within:bg-[#1A1A1A] transition-colors">
        <Search className="size-3.5 shrink-0 text-neutral-400" />
        <input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          placeholder="Search address, TXID, IP..."
          className="w-full bg-transparent text-xs text-neutral-200 placeholder:text-neutral-400 focus:outline-none font-sans"
          aria-label="Global search"
        />
        <kbd className="hidden items-center gap-0.5 rounded border border-[#2E2E2E] bg-[#222] px-1 py-0.5 text-[9px] text-neutral-400 sm:flex font-mono">
          <CornerDownLeft className="size-2.5" />
        </kbd>
      </div>

      {open && query.trim() ? (
        <div className="absolute z-30 mt-1 w-full overflow-hidden rounded border border-line bg-panel shadow-lg shadow-black/5">
          {results.length === 0 ? (
            <p className="px-3 py-3 text-xs text-fg-subtle">
              No matches found for{" "}
              <span className="font-mono text-fg-muted font-medium">{query}</span>
            </p>
          ) : (
            <ul className="divide-y divide-line-soft">
              {results.map((r, i) => (
                <li key={`${r.kind}-${r.id}`}>
                  <button
                    type="button"
                    onMouseEnter={() => setActive(i)}
                    onClick={() => go(r)}
                    className={cn(
                      "flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-xs transition-colors",
                      i === active ? "bg-accent-soft text-accent" : "hover:bg-panel-2 text-fg",
                    )}
                  >
                    <div className="min-w-0">
                      <p className="truncate font-mono">{r.label}</p>
                      <p className="truncate text-[10px] text-fg-subtle">{r.sublabel}</p>
                    </div>
                    <span className="shrink-0 rounded border border-line bg-panel px-1.5 py-0.5 text-[9px] uppercase tracking-wider text-fg-subtle">
                      {r.kind}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  )
}
