import { Navigate, Route, Routes } from "react-router-dom"
import { DashboardPage } from "@/pages/dashboard"
import { TransactionsPage } from "@/pages/transactions"
import { EntitiesPage } from "@/pages/entities"
import { DatasetPage } from "@/pages/dataset"
import { GraphExplorerPage } from "@/pages/graph-explorer"
import { NetworkPage } from "@/pages/network"
import { BehaviorsPage } from "@/pages/behaviors"
import { AlertsPage } from "@/pages/alerts"
import { ModelPage } from "@/pages/model"
import { InvestigationPage } from "@/pages/investigation"
import { TransactionPage } from "@/pages/transaction"

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/transactions" element={<TransactionsPage />} />
      <Route path="/entities" element={<EntitiesPage />} />
      <Route path="/dataset" element={<DatasetPage />} />
      <Route path="/graph" element={<GraphExplorerPage />} />
      <Route path="/network" element={<NetworkPage />} />
      <Route path="/behaviors" element={<BehaviorsPage />} />
      <Route path="/alerts" element={<AlertsPage />} />
      <Route path="/model" element={<ModelPage />} />
      <Route path="/investigation" element={<InvestigationPage />} />
      <Route path="/investigation/:entityId" element={<InvestigationPage />} />
      <Route path="/transaction/:txid" element={<TransactionPage />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
