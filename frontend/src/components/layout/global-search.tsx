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
    <div ref={containerRef} className="relative w-full max-w-xl">
      <div className="flex items-center gap-2.5 rounded-md border border-line bg-panel-2 px-3 py-2 focus-within:border-accent/50">
        <Search className="size-4 shrink-0 text-fg-subtle" />
        <input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          placeholder="Search address, TXID, or IP / network entity…"
          className="w-full bg-transparent font-mono-id text-sm text-fg placeholder:font-sans placeholder:text-fg-subtle focus:outline-none"
          aria-label="Global search"
        />
        <kbd className="hidden items-center gap-1 rounded border border-line px-1.5 py-0.5 text-[10px] text-fg-subtle sm:flex">
          <CornerDownLeft className="size-3" /> to open
        </kbd>
      </div>

      {open && query.trim() ? (
        <div className="absolute z-30 mt-2 w-full overflow-hidden rounded-md border border-line bg-panel shadow-xl shadow-black/40">
          {results.length === 0 ? (
            <p className="px-3 py-4 text-sm text-fg-subtle">
              No matches for{" "}
              <span className="font-mono-id text-fg-muted">{query}</span>
            </p>
          ) : (
            <ul>
              {results.map((r, i) => (
                <li key={`${r.kind}-${r.id}`}>
                  <button
                    type="button"
                    onMouseEnter={() => setActive(i)}
                    onClick={() => go(r)}
                    className={cn(
                      "flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left",
                      i === active ? "bg-accent-soft" : "hover:bg-panel-2",
                    )}
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm text-fg">{r.label}</p>
                      <p className="truncate font-mono-id text-xs text-fg-subtle">
                        {r.sublabel}
                      </p>
                    </div>
                    <span className="shrink-0 rounded border border-line bg-panel-2 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-fg-subtle">
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
