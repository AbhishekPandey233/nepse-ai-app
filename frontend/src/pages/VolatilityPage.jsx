import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Line } from "react-chartjs-2";

import { explainChat, getVolatility } from "../api/client.js";
import ErrorRetry from "../components/ErrorRetry.jsx";
import LoadingSkeleton from "../components/LoadingSkeleton.jsx";
import { TICKERS } from "../constants/tickers.js";
import { useTickerData } from "../hooks/useTickerData.js";
import { themeColor } from "../theme.js";
import { percentileRank, quantile } from "../utils/stats.js";

const HIGH_VOL_QUANTILE = 0.8;

export default function VolatilityPage() {
  const [searchParams] = useSearchParams();
  const [ticker, setTicker] = useState(searchParams.get("ticker") || TICKERS[0]);
  const { data, loading, error, retry } = useTickerData(getVolatility, ticker);
  const [narrative, setNarrative] = useState({ loading: false, error: "", answer: "" });

  async function handleExplain() {
    setNarrative({ loading: true, error: "", answer: "" });
    try {
      const question = `Explain what the current volatility level means for an investor holding ${ticker}, in practical terms`;
      const result = await explainChat(ticker, question);
      setNarrative({ loading: false, error: "", answer: result.answer });
    } catch (err) {
      const message =
        err.response?.status === 404
          ? "Run an analysis for this ticker first."
          : err.response?.data?.detail || "Something went wrong. Please try again.";
      setNarrative({ loading: false, error: message, answer: "" });
    }
  }

  function handleTickerChange(e) {
    setTicker(e.target.value);
    setNarrative({ loading: false, error: "", answer: "" });
  }

  let chartData = null;
  let chartOptions = null;
  let currentValue = null;
  let topPercent = null;
  let threshold = null;

  if (data) {
    const history = data.conditional_volatility;
    const sorted = [...history].sort((a, b) => a - b);
    threshold = quantile(sorted, HIGH_VOL_QUANTILE);
    currentValue = history[history.length - 1];
    topPercent = Math.round(100 - percentileRank(currentValue, history));

    const forecastLabels = data.forecast.map((_, i) => `+${i + 1}d`);
    const labels = [...data.dates, ...forecastLabels];

    const historicalPoints = [...history, ...new Array(data.forecast.length).fill(null)];
    const forecastLine = [
      ...new Array(history.length - 1).fill(null),
      history[history.length - 1],
      ...data.forecast,
    ];

    const chartCyan = themeColor("--chart-cyan");
    const chartCritical = themeColor("--chart-critical");
    const chartViolet = themeColor("--chart-violet");
    const chartNeutral = themeColor("--chart-neutral");

    // highlight points above the 80th-percentile threshold via per-point color/size,
    // instead of pulling in an annotation plugin just to shade a region
    const pointColors = history.map((v) => (v > threshold ? chartCritical : chartCyan));
    const pointRadii = history.map((v) => (v > threshold ? 3 : 0));

    chartData = {
      labels,
      datasets: [
        {
          label: "Conditional volatility",
          data: historicalPoints,
          borderColor: chartCyan,
          pointBackgroundColor: [...pointColors, ...new Array(data.forecast.length).fill("transparent")],
          pointRadius: [...pointRadii, ...new Array(data.forecast.length).fill(0)],
        },
        {
          label: "Forecast",
          data: forecastLine,
          borderColor: chartViolet,
          borderDash: [6, 6],
          pointRadius: 0,
        },
        {
          label: `${Math.round(HIGH_VOL_QUANTILE * 100)}th percentile threshold`,
          data: new Array(labels.length).fill(threshold),
          borderColor: chartNeutral,
          borderDash: [2, 3],
          borderWidth: 1,
          pointRadius: 0,
        },
      ],
    };

    chartOptions = { responsive: true, animation: false };
  }

  return (
    <div className="volatility-page">
      <Link to="/dashboard" className="toggle-link">
        &larr; Back to dashboard
      </Link>
      <h1>Volatility &amp; Risk</h1>

      <div className="explorer-controls">
        <select value={ticker} onChange={handleTickerChange}>
          {TICKERS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      {loading && (
        <div className="card">
          <LoadingSkeleton />
        </div>
      )}

      {error && (
        <div className="card">
          <ErrorRetry message={error} onRetry={retry} />
        </div>
      )}

      {!loading && !error && data && (
        <>
          <div className="card risk-indicator">
            <span className="stat-label">Current risk level</span>
            <p className="stat-value">
              {topPercent <= 0 ? "Highest" : `Top ${topPercent}%`} of historical volatility for {ticker}
            </p>
            <p className="hint">
              Current conditional volatility ({currentValue.toFixed(5)}) compared against this stock's own full
              history. Points above the dashed {Math.round(HIGH_VOL_QUANTILE * 100)}th-percentile line
              ({threshold.toFixed(5)}) are highlighted in red, showing where volatility clustering has occurred.
            </p>
          </div>

          <div className="card chart-fade-in">
            <Line data={chartData} options={chartOptions} />
          </div>

          <div className="card narrative-panel">
            <h2>What does this mean for me?</h2>
            <button type="button" className="btn-primary" onClick={handleExplain} disabled={narrative.loading}>
              {narrative.loading ? "Thinking..." : "Explain current risk level"}
            </button>
            {narrative.error && <p className="error">{narrative.error}</p>}
            {narrative.answer && <p className="narrative-answer">{narrative.answer}</p>}
          </div>
        </>
      )}
    </div>
  );
}
