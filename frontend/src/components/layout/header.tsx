import { GlobalSearch } from "./global-search"

export function Header({ title }: { title: string }) {
  return (
    <header className="flex items-center gap-6 border-b border-line bg-bg/80 px-6 py-3 backdrop-blur">
      <h1 className="shrink-0 text-sm font-semibold uppercase tracking-widest text-fg-subtle">
        {title}
      </h1>
      <div className="flex flex-1 justify-end">
        <GlobalSearch />
      </div>
    </header>
  )
}
