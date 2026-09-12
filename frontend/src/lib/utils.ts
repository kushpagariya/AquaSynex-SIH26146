import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Shorten a long technical identifier (address / txid) for display. */
export function truncateId(id: string, head = 10, tail = 6): string {
  if (!id) return ""
  if (id.length <= head + tail + 1) return id
  return `${id.slice(0, head)}…${id.slice(-tail)}`
}

/** Format an ISO timestamp as HH:MM:SS. */
export function formatTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  })
}

/** Format an ISO timestamp as a compact date-time. */
export function formatDateTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  })
}

/** Format a BTC amount with fixed precision and thin grouping. */
export function formatBtc(amount: number): string {
  return `${amount.toLocaleString("en-US", {
    minimumFractionDigits: 4,
    maximumFractionDigits: 8,
  })} BTC`
}

export function formatNumber(n: number): string {
  return n.toLocaleString("en-US")
}
