import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import HomePage from "@/pages/HomePage"
import RequestPage from "@/pages/RequestPage"
import TrackPage from "@/pages/TrackPage"
import VerifyPage from "@/pages/VerifyPage"

export default function App() {
  return (
    <BrowserRouter basename="/BIS">
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/request" element={<RequestPage />} />
        <Route path="/track" element={<TrackPage />} />
        <Route path="/track/:ref/:key" element={<TrackPage />} />
        <Route path="/verify/:serial" element={<VerifyPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
