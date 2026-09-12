/**
 * Data service — the single integration seam.
 *
 * Every page calls these typed async functions. Today they resolve mock data;
 * to wire the real offline backend / ML pipeline, replace the bodies here with
 * fetch/IPC calls that return the same shapes. No page component changes.
 */

import {
  alerts,
  dashboardStats,
  datasetInfo,
  entities,
  entityById,
  evidence,
  graphs,
  timelines,
  transactionByTxid,
  transactions,
} from "./mock"
import type {
  Alert,
  DashboardStats,
  DatasetInfo,
  Entity,
  Investigation,
  Transaction,
} from "./types"

const LATENCY = 260

function delay<T>(value: T, ms = LATENCY): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms))
}

export function getDashboardStats(): Promise<DashboardStats> {
  return delay(dashboardStats)
}

export function getAlerts(): Promise<Alert[]> {
  return delay(alerts)
}

export function getEntities(): Promise<Entity[]> {
  return delay(entities)
}

export function getTransactions(): Promise<Transaction[]> {
  return delay(transactions)
}

export function getDatasetInfo(): Promise<DatasetInfo> {
  return delay(datasetInfo)
}

export function getTransaction(txid: string): Promise<Transaction | null> {
  return delay(transactionByTxid(txid) ?? null)
}

export function getInvestigation(entityId: string): Promise<Investigation | null> {
  const entity = entityById(entityId)
  if (!entity) return delay(null)

  const connectedEntities = entity.connectedEntityIds
    .map((id) => entityById(id))
    .filter((e): e is Entity => Boolean(e))

  const relatedTransactions = transactions.filter((t) =>
    t.relatedEntityIds.includes(entityId),
  )

  const investigation: Investigation = {
    entity,
    transactions: relatedTransactions,
    connectedEntities,
    timeline: timelines[entityId] ?? [],
    evidence: evidence[entityId] ?? [],
    graph: graphs[entityId] ?? { nodes: [{ id: entity.id, label: entity.label, type: entity.type, severity: entity.risk.severity, isFocus: true }], edges: [] },
  }
  return delay(investigation)
}

export interface SearchResult {
  id: string
  kind: "entity" | "transaction"
  label: string
  sublabel: string
  route: string
}

export function search(query: string): Promise<SearchResult[]> {
  const q = query.trim().toLowerCase()
  if (!q) return delay([], 80)

  const entityResults: SearchResult[] = entities
    .filter(
      (e) =>
        e.id.toLowerCase().includes(q) ||
        e.label.toLowerCase().includes(q) ||
        e.address?.toLowerCase().includes(q) ||
        e.network?.ip.toLowerCase().includes(q),
    )
    .map((e) => ({
      id: e.id,
      kind: "entity",
      label: e.label,
      sublabel: e.address ?? e.network?.ip ?? e.type,
      route: `/investigation/${e.id}`,
    }))

  const txResults: SearchResult[] = transactions
    .filter((t) => t.txid.toLowerCase().includes(q))
    .map((t) => ({
      id: t.txid,
      kind: "transaction",
      label: `TX ${t.txid.slice(0, 12)}…`,
      sublabel: `${t.amount} BTC`,
      route: `/transaction/${t.txid}`,
    }))

  return delay([...entityResults, ...txResults].slice(0, 8), 120)
}
