import { useState } from "react"
import { Check, Copy } from "lucide-react"
import { cn } from "@/lib/utils"
import { truncateId } from "@/lib/utils"

/** Renders a technical identifier in monospace with optional copy + truncation. */
export function MonoId({
  value,
  truncate = true,
  head = 10,
  tail = 6,
  copyable = true,
  className,
}: {
  value: string
  truncate?: boolean
  head?: number
  tail?: number
  copyable?: boolean
  className?: string
}) {
  const [copied, setCopied] = useState(false)
  const display = truncate ? truncateId(value, head, tail) : value

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      setTimeout(() => setCopied(false), 1200)
    } catch {
      /* clipboard unavailable */
    }
  }

  return (
    <span className={cn("inline-flex items-center gap-1.5", className)}>
      <span className="font-mono-id text-fg-muted" title={value}>
        {display}
      </span>
      {copyable ? (
        <button
          type="button"
          onClick={handleCopy}
          className="text-fg-subtle transition-colors hover:text-accent"
          aria-label="Copy to clipboard"
        >
          {copied ? (
            <Check className="size-3.5 text-risk-low" />
          ) : (
            <Copy className="size-3.5" />
          )}
        </button>
      ) : null}
    </span>
  )
}
