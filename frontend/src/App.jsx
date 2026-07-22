import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import Layout from "./components/Layout.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import ExplainabilityPage from "./pages/ExplainabilityPage.jsx";
import Login from "./pages/Login.jsx";
import MarketOverview from "./pages/MarketOverview.jsx";
import PortfolioPage from "./pages/PortfolioPage.jsx";
import PredictionExplorer from "./pages/PredictionExplorer.jsx";
import ProfilePage from "./pages/ProfilePage.jsx";
import VolatilityPage from "./pages/VolatilityPage.jsx";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/market" element={<MarketOverview />} />
          <Route path="/prediction" element={<PredictionExplorer />} />
          <Route path="/volatility" element={<VolatilityPage />} />
          <Route path="/explainability" element={<ExplainabilityPage />} />
          <Route path="/portfolio" element={<PortfolioPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Route>
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
