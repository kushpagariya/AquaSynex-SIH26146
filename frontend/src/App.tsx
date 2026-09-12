import { Navigate, Route, Routes } from "react-router-dom"
import { DashboardPage } from "@/pages/dashboard"
import { DatasetPage } from "@/pages/dataset"
import { AlertsPage } from "@/pages/alerts"
import { InvestigationPage } from "@/pages/investigation"
import { TransactionPage } from "@/pages/transaction"

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/dataset" element={<DatasetPage />} />
      <Route path="/alerts" element={<AlertsPage />} />
      <Route path="/investigation" element={<InvestigationPage />} />
      <Route path="/investigation/:entityId" element={<InvestigationPage />} />
      <Route path="/transaction/:txid" element={<TransactionPage />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
