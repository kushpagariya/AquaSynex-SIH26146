import type { ReactNode } from "react"
import { Sidebar } from "./sidebar"
import { Header } from "./header"

export function AppLayout({
  title,
  children,
}: {
  title: string
  children: ReactNode
}) {
  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-bg text-fg select-none">
      {/* 1. Full-Width Black Top Chrome (h-11 = 44px) */}
      <Header title={title} />

      {/* 2. Body Container: Dark Sidebar on Left, Off-White Workspace on Right */}
      <div className="flex min-h-0 flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto bg-bg select-text">
          <div className="mx-auto max-w-[1440px] px-8 py-7">{children}</div>
        </main>
      </div>
    </div>
  )
}
