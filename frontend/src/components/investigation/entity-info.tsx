import type { Entity } from "@/data/types"
import { MonoId } from "@/components/ui/mono-id"
import { formatBtc, formatDateTime, formatNumber } from "@/lib/utils"

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 py-2">
      <dt className="text-xs text-fg-subtle">{label}</dt>
      <dd className="text-right text-sm text-fg">{children}</dd>
    </div>
  )
}

export function EntityInfo({ entity }: { entity: Entity }) {
  return (
    <dl className="divide-y divide-line-soft">
      {entity.address ? (
        <Row label="Address">
          <MonoId value={entity.address} head={8} tail={6} />
        </Row>
      ) : null}
      <Row label="First seen">{formatDateTime(entity.firstSeen)}</Row>
      <Row label="Last seen">{formatDateTime(entity.lastSeen)}</Row>
      <Row label="Transactions">
        <span className="font-mono-id tabular-nums">
          {formatNumber(entity.totalTransactions)}
        </span>
      </Row>
      <Row label="Total received">
        <span className="font-mono-id tabular-nums">
          {formatBtc(entity.totalReceived)}
        </span>
      </Row>
      <Row label="Total sent">
        <span className="font-mono-id tabular-nums">
          {formatBtc(entity.totalSent)}
        </span>
      </Row>
      <Row label="Balance">
        <span className="font-mono-id tabular-nums text-accent">
          {formatBtc(entity.balance)}
        </span>
      </Row>
      {entity.tags.length ? (
        <Row label="Tags">
          <div className="flex flex-wrap justify-end gap-1">
            {entity.tags.map((t) => (
              <span
                key={t}
                className="rounded border border-line bg-panel-2 px-1.5 py-0.5 text-[10px] text-fg-muted"
              >
                {t}
              </span>
            ))}
          </div>
        </Row>
      ) : null}
    </dl>
  )
}

export function NetworkInfoPanel({ entity }: { entity: Entity }) {
  const net = entity.network
  if (!net) {
    return (
      <p className="text-sm text-fg-subtle">
        No network metadata associated with this entity.
      </p>
    )
  }
  return (
    <dl className="divide-y divide-line-soft">
      <Row label="IP address">
        <MonoId value={net.ip} truncate={false} />
      </Row>
      <Row label="Port">
        <span className="font-mono-id tabular-nums">{net.port}</span>
      </Row>
      <Row label="ASN">
        <span className="font-mono-id">{net.asn}</span>
      </Row>
      <Row label="Organization">{net.asnOrg}</Row>
      <Row label="Country">
        {net.country} ({net.countryCode})
      </Row>
      <Row label="First seen">{formatDateTime(net.firstSeen)}</Row>
      <Row label="Last seen">{formatDateTime(net.lastSeen)}</Row>
    </dl>
  )
}
