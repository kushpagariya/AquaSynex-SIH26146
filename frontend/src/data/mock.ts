import type {
  Alert,
  AnomalyBucket,
  DashboardStats,
  DatasetInfo,
  Entity,
  EvidenceItem,
  GraphData,
  Severity,
  TimelineEvent,
  Transaction,
} from "./types"

const BASE_DAY = "2026-09-11"

function ts(time: string): string {
  return new Date(`${BASE_DAY}T${time}+00:00`).toISOString()
}

function severityForScore(score: number): Severity {
  if (score >= 90) return "critical"
  if (score >= 70) return "high"
  if (score >= 40) return "medium"
  return "low"
}

/* ------------------------------------------------------------------ */
/* Entities                                                            */
/* ------------------------------------------------------------------ */

export const entities: Entity[] = [
  {
    id: "e-001",
    type: "wallet",
    label: "Wallet A",
    address: "bc1q8c3f9x2v7k4p0n5m6q8r2t4y6u8i0o2a4s6d8f",
    risk: {
      score: 94,
      severity: "critical",
      summary:
        "Coordinated fan-out to newly created counterparties following a rapid inbound burst, consistent with layering behavior.",
      factors: [
        { id: "f1", label: "High fan-out", weight: 0.34, description: "Sent to 41 distinct outputs within a 9-minute window." },
        { id: "f2", label: "Transaction burst", weight: 0.27, description: "63 transactions in 14 minutes vs. baseline of 3/hour." },
        { id: "f3", label: "Unusual counterparties", weight: 0.22, description: "78% of counterparties first seen in the last 24h." },
        { id: "f4", label: "Unusual network behavior", weight: 0.17, description: "Traffic routed through an ASN flagged in prior cases." },
      ],
    },
    firstSeen: ts("08:02:11"),
    lastSeen: ts("10:42:55"),
    totalTransactions: 412,
    totalReceived: 184.5521,
    totalSent: 183.9982,
    balance: 0.5539,
    tags: ["fan-out", "layering", "watchlist"],
    network: {
      ip: "185.220.101.47",
      port: 8333,
      asn: "AS200651",
      asnOrg: "FlokiNET",
      country: "Romania",
      countryCode: "RO",
      firstSeen: ts("08:02:11"),
      lastSeen: ts("10:42:55"),
    },
    connectedEntityIds: ["e-002", "e-003", "e-004", "e-006", "e-007"],
  },
  {
    id: "e-002",
    type: "wallet",
    label: "Wallet B",
    address: "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    risk: {
      score: 87,
      severity: "high",
      summary: "Repeated burst activity and reuse of counterparties linked to Wallet A.",
      factors: [
        { id: "f1", label: "Burst activity", weight: 0.4, description: "Multiple bursts over 3 hours." },
        { id: "f2", label: "Shared counterparties", weight: 0.35, description: "Overlaps 60% with Wallet A." },
        { id: "f3", label: "Unusual timing", weight: 0.25, description: "Activity concentrated outside baseline windows." },
      ],
    },
    firstSeen: ts("08:31:00"),
    lastSeen: ts("10:31:20"),
    totalTransactions: 233,
    totalReceived: 92.11,
    totalSent: 90.4,
    balance: 1.71,
    tags: ["burst", "watchlist"],
    network: {
      ip: "45.134.22.18",
      port: 8333,
      asn: "AS49505",
      asnOrg: "Selectel",
      country: "Netherlands",
      countryCode: "NL",
      firstSeen: ts("08:31:00"),
      lastSeen: ts("10:31:20"),
    },
    connectedEntityIds: ["e-001", "e-005", "e-008"],
  },
  {
    id: "e-003",
    type: "mixer",
    label: "Mixer Service",
    address: "bc1qmixer0x9a8b7c6d5e4f3g2h1i0j9k8l7m6n5o4p",
    risk: {
      score: 91,
      severity: "critical",
      summary: "Known mixing pattern with equal-value outputs and high counterparty churn.",
      factors: [
        { id: "f1", label: "Equal-value outputs", weight: 0.38, description: "Outputs normalized to uniform denominations." },
        { id: "f2", label: "High counterparty churn", weight: 0.34, description: "Counterparties rarely reused." },
        { id: "f3", label: "Peeling chain", weight: 0.28, description: "Sequential peel pattern detected." },
      ],
    },
    firstSeen: ts("07:12:00"),
    lastSeen: ts("10:40:00"),
    totalTransactions: 1894,
    totalReceived: 4102.22,
    totalSent: 4098.9,
    balance: 3.32,
    tags: ["mixer", "layering", "high-volume"],
    connectedEntityIds: ["e-001", "e-004", "e-007"],
  },
  {
    id: "e-004",
    type: "wallet",
    label: "Wallet C",
    address: "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy",
    risk: {
      score: 68,
      severity: "medium",
      summary: "Elevated activity with partial overlap into flagged clusters.",
      factors: [
        { id: "f1", label: "Cluster overlap", weight: 0.5, description: "Connected to two critical entities." },
        { id: "f2", label: "Moderate fan-in", weight: 0.5, description: "Received from 18 sources in short window." },
      ],
    },
    firstSeen: ts("09:01:00"),
    lastSeen: ts("10:20:00"),
    totalTransactions: 88,
    totalReceived: 22.5,
    totalSent: 20.1,
    balance: 2.4,
    tags: ["fan-in"],
    connectedEntityIds: ["e-001", "e-003"],
  },
  {
    id: "e-005",
    type: "wallet",
    label: "Wallet D",
    address: "bc1qd4t4y6u8i0o2a4s6d8f0g2h4j6k8l0m2n4p6q8",
    risk: {
      score: 33,
      severity: "low",
      summary: "Within baseline behavior; monitored due to counterparty proximity.",
      factors: [
        { id: "f1", label: "Counterparty proximity", weight: 1, description: "One hop from Wallet B." },
      ],
    },
    firstSeen: ts("09:40:00"),
    lastSeen: ts("10:15:00"),
    totalTransactions: 14,
    totalReceived: 3.2,
    totalSent: 1.0,
    balance: 2.2,
    tags: ["monitored"],
    connectedEntityIds: ["e-002"],
  },
  {
    id: "e-006",
    type: "ip",
    label: "185.220.101.47",
    risk: {
      score: 82,
      severity: "high",
      summary: "Exit-node style traffic correlated with multiple flagged wallets.",
      factors: [
        { id: "f1", label: "Shared across entities", weight: 0.6, description: "Associated with 5 flagged wallets." },
        { id: "f2", label: "Flagged ASN", weight: 0.4, description: "ASN appears in prior investigations." },
      ],
    },
    firstSeen: ts("08:02:00"),
    lastSeen: ts("10:42:00"),
    totalTransactions: 0,
    totalReceived: 0,
    totalSent: 0,
    balance: 0,
    tags: ["network", "shared-ip"],
    network: {
      ip: "185.220.101.47",
      port: 8333,
      asn: "AS200651",
      asnOrg: "FlokiNET",
      country: "Romania",
      countryCode: "RO",
      firstSeen: ts("08:02:00"),
      lastSeen: ts("10:42:00"),
    },
    connectedEntityIds: ["e-001", "e-007"],
  },
  {
    id: "e-007",
    type: "wallet",
    label: "Wallet E",
    address: "bc1q7fan0ut9s8d7f6g5h4j3k2l1m0n9o8p7q6r5s4",
    risk: {
      score: 76,
      severity: "high",
      summary: "Downstream recipient in the fan-out pattern originating from Wallet A.",
      factors: [
        { id: "f1", label: "Fan-out recipient", weight: 0.55, description: "Primary recipient of layered outputs." },
        { id: "f2", label: "Rapid forwarding", weight: 0.45, description: "Forwarded 92% of received value within minutes." },
      ],
    },
    firstSeen: ts("10:33:00"),
    lastSeen: ts("10:41:00"),
    totalTransactions: 27,
    totalReceived: 41.2,
    totalSent: 40.9,
    balance: 0.3,
    tags: ["fan-out", "forwarding"],
    connectedEntityIds: ["e-001", "e-003", "e-006"],
  },
  {
    id: "e-008",
    type: "exchange",
    label: "Exchange Deposit",
    address: "bc1qexch4ng3d3p0s1t2a3d4d5r6e7s8s9a0b1c2d3e",
    risk: {
      score: 21,
      severity: "low",
      summary: "Known exchange deposit address; low intrinsic risk, tracked as cash-out point.",
      factors: [
        { id: "f1", label: "Cash-out endpoint", weight: 1, description: "Terminal node for flagged flows." },
      ],
    },
    firstSeen: ts("08:00:00"),
    lastSeen: ts("10:38:00"),
    totalTransactions: 5230,
    totalReceived: 91200.5,
    totalSent: 91180.2,
    balance: 20.3,
    tags: ["exchange", "cash-out"],
    connectedEntityIds: ["e-002"],
  },
]

export function entityById(id: string): Entity | undefined {
  return entities.find((e) => e.id === id)
}

/* ------------------------------------------------------------------ */
/* Alerts                                                              */
/* ------------------------------------------------------------------ */

export const alerts: Alert[] = [
  { id: "a-1001", entityId: "e-001", entityLabel: "Wallet A", entityType: "wallet", riskScore: 94, severity: "critical", reason: "High fan-out to new counterparties", timestamp: ts("10:42:55"), status: "new" },
  { id: "a-1002", entityId: "e-003", entityLabel: "Mixer Service", entityType: "mixer", riskScore: 91, severity: "critical", reason: "Mixing pattern with equal-value outputs", timestamp: ts("10:40:02"), status: "reviewing" },
  { id: "a-1003", entityId: "e-002", entityLabel: "Wallet B", entityType: "wallet", riskScore: 87, severity: "high", reason: "Sustained burst activity", timestamp: ts("10:31:20"), status: "reviewing" },
  { id: "a-1004", entityId: "e-006", entityLabel: "185.220.101.47", entityType: "ip", riskScore: 82, severity: "high", reason: "Shared IP across flagged wallets", timestamp: ts("10:28:10"), status: "new" },
  { id: "a-1005", entityId: "e-007", entityLabel: "Wallet E", entityType: "wallet", riskScore: 76, severity: "high", reason: "Rapid forwarding of layered funds", timestamp: ts("10:22:44"), status: "escalated" },
  { id: "a-1006", entityId: "e-004", entityLabel: "Wallet C", entityType: "wallet", riskScore: 68, severity: "medium", reason: "Cluster overlap with critical entities", timestamp: ts("10:12:00"), status: "new" },
  { id: "a-1007", entityId: "e-005", entityLabel: "Wallet D", entityType: "wallet", riskScore: 33, severity: "low", reason: "Counterparty proximity to flagged wallet", timestamp: ts("09:55:31"), status: "dismissed" },
  { id: "a-1008", entityId: "e-008", entityLabel: "Exchange Deposit", entityType: "exchange", riskScore: 21, severity: "low", reason: "Cash-out endpoint for flagged flow", timestamp: ts("09:38:00"), status: "resolved" },
]

/* ------------------------------------------------------------------ */
/* Transactions                                                        */
/* ------------------------------------------------------------------ */

const sharedNetwork = {
  ip: "185.220.101.47",
  port: 8333,
  asn: "AS200651",
  asnOrg: "FlokiNET",
  country: "Romania",
  countryCode: "RO",
  firstSeen: ts("08:02:00"),
  lastSeen: ts("10:42:00"),
}

export const transactions: Transaction[] = [
  {
    txid: "9f2c1b7e4a6d8c0f2e1a3b5c7d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e",
    timestamp: ts("10:42:55"),
    amount: 12.482,
    fee: 0.00042,
    confirmations: 3,
    block: 872_115,
    inputs: [{ entityId: "e-001", address: "bc1q8c3f9x2v7k4p0n5m6q8r2t4y6u8i0o2a4s6d8f", amount: 12.4824 }],
    outputs: [
      { entityId: "e-007", address: "bc1q7fan0ut9s8d7f6g5h4j3k2l1m0n9o8p7q6r5s4", amount: 6.2 },
      { entityId: "e-003", address: "bc1qmixer0x9a8b7c6d5e4f3g2h1i0j9k8l7m6n5o4p", amount: 6.28 },
    ],
    network: sharedNetwork,
    relatedEntityIds: ["e-001", "e-007", "e-003"],
    riskScore: 94,
    severity: "critical",
  },
  {
    txid: "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b",
    timestamp: ts("10:31:20"),
    amount: 4.01,
    fee: 0.00031,
    confirmations: 5,
    block: 872_113,
    inputs: [{ entityId: "e-002", address: "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", amount: 4.0103 }],
    outputs: [
      { entityId: "e-005", address: "bc1qd4t4y6u8i0o2a4s6d8f0g2h4j6k8l0m2n4p6q8", amount: 2.0 },
      { entityId: "e-008", address: "bc1qexch4ng3d3p0s1t2a3d4d5r6e7s8s9a0b1c2d3e", amount: 2.01 },
    ],
    network: { ...sharedNetwork, ip: "45.134.22.18", asn: "AS49505", asnOrg: "Selectel", country: "Netherlands", countryCode: "NL" },
    relatedEntityIds: ["e-002", "e-005", "e-008"],
    riskScore: 87,
    severity: "high",
  },
  {
    txid: "5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d",
    timestamp: ts("10:24:09"),
    amount: 1.75,
    fee: 0.00018,
    confirmations: 8,
    block: 872_110,
    inputs: [{ entityId: "e-003", address: "bc1qmixer0x9a8b7c6d5e4f3g2h1i0j9k8l7m6n5o4p", amount: 1.7502 }],
    outputs: [{ entityId: "e-004", address: "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy", amount: 1.75 }],
    network: sharedNetwork,
    relatedEntityIds: ["e-003", "e-004"],
    riskScore: 68,
    severity: "medium",
  },
  {
    txid: "2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c",
    timestamp: ts("10:21:00"),
    amount: 0.42,
    fee: 0.00012,
    confirmations: 11,
    block: 872_108,
    inputs: [{ entityId: "e-001", address: "bc1q8c3f9x2v7k4p0n5m6q8r2t4y6u8i0o2a4s6d8f", amount: 0.4202 }],
    outputs: [{ entityId: "e-004", address: "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy", amount: 0.42 }],
    network: sharedNetwork,
    relatedEntityIds: ["e-001", "e-004"],
    riskScore: 55,
    severity: "medium",
  },
]

export function transactionByTxid(txid: string): Transaction | undefined {
  return transactions.find((t) => t.txid === txid)
}

/* ------------------------------------------------------------------ */
/* Per-entity investigation extras                                     */
/* ------------------------------------------------------------------ */

export const timelines: Record<string, TimelineEvent[]> = {
  "e-001": [
    { id: "t1", timestamp: ts("10:21:00"), kind: "transaction", title: "Transaction", detail: "Outbound 0.42 BTC to Wallet C", txid: "2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c" },
    { id: "t2", timestamp: ts("10:24:09"), kind: "counterparty", title: "New counterparty", detail: "First interaction with Wallet E", severity: "medium" },
    { id: "t3", timestamp: ts("10:31:00"), kind: "burst", title: "Transaction burst", detail: "63 transactions in 14 minutes", severity: "high" },
    { id: "t4", timestamp: ts("10:37:00"), kind: "network", title: "Network event", detail: "Traffic shifted to flagged ASN AS200651", severity: "high" },
    { id: "t5", timestamp: ts("10:42:55"), kind: "high-risk", title: "High-risk transaction", detail: "12.48 BTC fan-out split across mixer + Wallet E", severity: "critical", txid: "9f2c1b7e4a6d8c0f2e1a3b5c7d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e" },
  ],
}

export const evidence: Record<string, EvidenceItem[]> = {
  "e-001": [
    { id: "ev1", category: "behavioral", title: "Transaction burst", detail: "63 transactions within a 14-minute window against a baseline of ~3/hour.", severity: "high", timestamp: ts("10:31:00") },
    { id: "ev2", category: "behavioral", title: "Rapid fan-out", detail: "Value split across 41 distinct outputs in under 9 minutes.", severity: "critical", timestamp: ts("10:42:55") },
    { id: "ev3", category: "transaction", title: "Layering into mixer", detail: "6.28 BTC routed into a known mixing service in the terminal transaction.", severity: "critical", timestamp: ts("10:42:55") },
    { id: "ev4", category: "network", title: "Flagged ASN", detail: "Node traffic observed on AS200651 (FlokiNET), present in prior cases.", severity: "high", timestamp: ts("10:37:00") },
    { id: "ev5", category: "connections", title: "Critical-entity adjacency", detail: "Directly connected to Mixer Service (91) and Wallet E (76).", severity: "high" },
    { id: "ev6", category: "model", title: "Model contributing factors", detail: "High fan-out (0.34), transaction burst (0.27), unusual counterparties (0.22), unusual network behavior (0.17).", severity: "critical" },
  ],
}

export const graphs: Record<string, GraphData> = {
  "e-001": {
    nodes: [
      { id: "e-001", label: "Wallet A", type: "wallet", severity: "critical", isFocus: true },
      { id: "e-002", label: "Wallet B", type: "wallet", severity: "high" },
      { id: "e-003", label: "Mixer", type: "mixer", severity: "critical" },
      { id: "e-004", label: "Wallet C", type: "wallet", severity: "medium" },
      { id: "e-006", label: "185.220.101.47", type: "ip", severity: "high" },
      { id: "e-007", label: "Wallet E", type: "wallet", severity: "high" },
      { id: "tx-1", label: "TX 9f2c…d7e", type: "transaction", severity: "critical" },
      { id: "tx-2", label: "TX 2b3c…b3c", type: "transaction", severity: "medium" },
    ],
    edges: [
      { id: "g1", source: "e-006", target: "e-001", label: "network", suspicious: true },
      { id: "g2", source: "e-001", target: "tx-1", amount: 12.48, suspicious: true },
      { id: "g3", source: "tx-1", target: "e-007", amount: 6.2, suspicious: true },
      { id: "g4", source: "tx-1", target: "e-003", amount: 6.28, suspicious: true },
      { id: "g5", source: "e-001", target: "tx-2", amount: 0.42 },
      { id: "g6", source: "tx-2", target: "e-004", amount: 0.42 },
      { id: "g7", source: "e-002", target: "e-001", label: "shared counterparties" },
      { id: "g8", source: "e-003", target: "e-007", label: "peel", suspicious: true },
    ],
  },
}

/* ------------------------------------------------------------------ */
/* Dashboard + dataset                                                 */
/* ------------------------------------------------------------------ */

const anomalySeries: AnomalyBucket[] = [
  { label: "07:00", transactions: 210, anomalies: 4 },
  { label: "08:00", transactions: 380, anomalies: 11 },
  { label: "09:00", transactions: 520, anomalies: 22 },
  { label: "10:00", transactions: 910, anomalies: 63 },
  { label: "11:00", transactions: 640, anomalies: 38 },
  { label: "12:00", transactions: 300, anomalies: 9 },
]

export const dashboardStats: DashboardStats = {
  totalTransactions: 128_442,
  totalEntities: 9_318,
  suspiciousEntities: 412,
  highRiskEntities: 128,
  activeAlerts: 24,
  anomaliesDetected: 147,
  deltas: { transactions: 3.2, entities: 1.8, alerts: 12.4, highRisk: 12.4 },
  anomalySeries,
}

export const datasetInfo: DatasetInfo = {
  id: "ds-2026-0911",
  name: "mainnet-blocks-872000-872120.csv",
  sizeBytes: 486_223_104,
  format: "CSV / network-enriched",
  uploadedAt: ts("07:05:00"),
  stage: "completed",
  progress: 100,
  stats: {
    transactions: 128_442,
    entities: 9_318,
    addresses: 14_207,
    blocks: 120,
    dateRange: { from: ts("07:00:00"), to: ts("12:00:00") },
    flagged: 412,
  },
}

export { severityForScore }
