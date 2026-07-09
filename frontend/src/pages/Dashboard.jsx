import { useState } from "react";
import { Navigate } from "react-router-dom";

import EfficiencyCard from "../components/EfficiencyCard.jsx";
import ExplainabilityChart from "../components/ExplainabilityChart.jsx";
import PredictionChart from "../components/PredictionChart.jsx";
import VolatilityChart from "../components/VolatilityChart.jsx";

const TICKERS = ["NABIL", "ADBL", "AHPC", "API", "AKPL"];

export default function Dashboard() {
  const [ticker, setTicker] = useState(TICKERS[0]);
  const [activeTicker, setActiveTicker] = useState("");

  if (!localStorage.getItem("token")) {
    return <Navigate to="/login" replace />;
  }

  function handleSubmit(e) {
    e.preventDefault();
    setActiveTicker(ticker);
  }

  return (
    <div className="dashboard">
      <h1>Dashboard</h1>
      <form onSubmit={handleSubmit}>
        <select value={ticker} onChange={(e) => setTicker(e.target.value)}>
          {TICKERS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <button type="submit">Run analysis</button>
      </form>

      {activeTicker && (
        <div className="chart-grid">
          <EfficiencyCard ticker={activeTicker} />
          <VolatilityChart ticker={activeTicker} />
          <PredictionChart ticker={activeTicker} />
          <ExplainabilityChart ticker={activeTicker} />
        </div>
      )}
    </div>
  );
}
