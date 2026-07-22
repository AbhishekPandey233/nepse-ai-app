import { useState } from "react";
import { Link } from "react-router-dom";

import ChatWidget from "../components/ChatWidget.jsx";
import EfficiencyCard from "../components/EfficiencyCard.jsx";
import ExplainabilityChart from "../components/ExplainabilityChart.jsx";
import PredictionChart from "../components/PredictionChart.jsx";
import VolatilityChart from "../components/VolatilityChart.jsx";
import { TICKERS } from "../constants/tickers.js";

const FACTORS = [
  { key: "efficiency", label: "Market Efficiency", Component: EfficiencyCard },
  { key: "volatility", label: "Volatility & Risk", Component: VolatilityChart },
  { key: "prediction", label: "Prediction", Component: PredictionChart },
  { key: "explainability", label: "Explainability", Component: ExplainabilityChart },
];

const ALL_SELECTED = Object.fromEntries(FACTORS.map((f) => [f.key, true]));

export default function Dashboard() {
  const [ticker, setTicker] = useState(TICKERS[0]);
  const [selected, setSelected] = useState(ALL_SELECTED);
  const [activeTicker, setActiveTicker] = useState("");
  const [activeFactors, setActiveFactors] = useState(ALL_SELECTED);

  const anySelected = Object.values(selected).some(Boolean);

  function toggleFactor(key) {
    setSelected((s) => ({ ...s, [key]: !s[key] }));
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (!anySelected) return;
    setActiveTicker(ticker);
    setActiveFactors(selected);
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

        <fieldset className="factor-select">
          <legend>Select factors to analyse</legend>
          <div className="factor-options">
            {FACTORS.map((f) => (
              <label key={f.key} className="factor-option">
                <input type="checkbox" checked={selected[f.key]} onChange={() => toggleFactor(f.key)} />
                {f.label}
              </label>
            ))}
          </div>
        </fieldset>

        <button type="submit" className="btn-primary" disabled={!anySelected}>
          Run analysis
        </button>
        {!anySelected && <p className="hint">Select at least one factor to run.</p>}
      </form>

      {activeTicker && (
        <>
          <p>
            <Link to={`/prediction?ticker=${activeTicker}`}>View detailed prediction explorer &rarr;</Link>
            {" · "}
            <Link to={`/volatility?ticker=${activeTicker}`}>View volatility &amp; risk &rarr;</Link>
            {" · "}
            <Link to={`/explainability?ticker=${activeTicker}`}>View model explainability &rarr;</Link>
          </p>
          <div className="chart-grid">
            {FACTORS.filter((f) => activeFactors[f.key]).map(({ key, Component }) => (
              <Component key={key} ticker={activeTicker} />
            ))}
          </div>
        </>
      )}

      <ChatWidget ticker={activeTicker} />
    </div>
  );
}
