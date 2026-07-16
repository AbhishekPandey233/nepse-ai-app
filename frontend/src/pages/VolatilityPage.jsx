import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { getVolatility } from "../api/client.js";
import ChatWidget from "../components/ChatWidget.jsx";
import ErrorRetry from "../components/ErrorRetry.jsx";
import LoadingSkeleton from "../components/LoadingSkeleton.jsx";
import SectionedExplanation from "../components/SectionedExplanation.jsx";
import ZoomableLine from "../components/ZoomableLine.jsx";
import { TICKERS } from "../constants/tickers.js";
import { useTickerData } from "../hooks/useTickerData.js";
import { themeColor } from "../theme.js";
import { buildVolatilityExplanation } from "../utils/historyNarrative.js";
import { contiguousRanges, percentileRank, quantile } from "../utils/stats.js";

const HIGH_VOL_QUANTILE = 0.8;

function averageOf(values) {
  return values.reduce((sum, v) => sum + v, 0) / values.length;
}

// builds the same "spike" line chart (conditional volatility with high-vol points highlighted
// in red above the 80th-percentile threshold, plus a dashed forecast tail) for any symbol's
// volatility payload, so the main chart and the comparison mini-charts always agree visually
function buildSpikeChartData(volData) {
  const history = volData.conditional_volatility;
  const sorted = [...history].sort((a, b) => a - b);
  const threshold = quantile(sorted, HIGH_VOL_QUANTILE);
  const currentValue = history[history.length - 1];
  const topPercent = Math.round(100 - percentileRank(currentValue, history));

  const forecastLabels = volData.forecast.map((_, i) => `+${i + 1}d`);
  const labels = [...volData.dates, ...forecastLabels];

  const historicalPoints = [...history, ...new Array(volData.forecast.length).fill(null)];
  const forecastLine = [
    ...new Array(history.length - 1).fill(null),
    history[history.length - 1],
    ...volData.forecast,
  ];

  const chartCyan = themeColor("--chart-cyan");
  const chartCritical = themeColor("--chart-critical");
  const chartViolet = themeColor("--chart-violet");
  const chartNeutral = themeColor("--chart-neutral");

  const pointColors = history.map((v) => (v > threshold ? chartCritical : chartCyan));
  const pointRadii = history.map((v) => (v > threshold ? 3 : 0));

  const chartData = {
    labels,
    datasets: [
      {
        label: "Conditional volatility",
        data: historicalPoints,
        borderColor: chartCyan,
        pointBackgroundColor: [...pointColors, ...new Array(volData.forecast.length).fill("transparent")],
        pointRadius: [...pointRadii, ...new Array(volData.forecast.length).fill(0)],
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

  return { chartData, chartOptions: { responsive: true, animation: false }, currentValue, topPercent, threshold, history };
}

// summarizes a single symbol's GARCH output down to the handful of numbers worth comparing
function volatilityStats(volData) {
  const alpha = volData.params["alpha[1]"] ?? 0;
  const beta = volData.params["beta[1]"] ?? 0;
  return {
    average: averageOf(volData.conditional_volatility),
    persistence: alpha + beta, // how strongly volatility clusters/persists day-to-day
    forecastAvg: averageOf(volData.forecast),
  };
}

export default function VolatilityPage() {
  const [searchParams] = useSearchParams();
  const [ticker, setTicker] = useState(searchParams.get("ticker") || TICKERS[0]);
  const { data, loading, error, retry } = useTickerData(getVolatility, ticker);

  const [compareTicker, setCompareTicker] = useState(TICKERS.find((t) => t !== ticker) || TICKERS[0]);
  const [compareState, setCompareState] = useState({ active: false, loading: false, error: "", data: null });

  function handleTickerChange(e) {
    const newTicker = e.target.value;
    setTicker(newTicker);
    setCompareState((s) => ({ ...s, active: false }));
    // keep the compare dropdown's selection valid -- it excludes whatever ticker is chosen above
    setCompareTicker((prev) => (prev === newTicker ? TICKERS.find((t) => t !== newTicker) || TICKERS[0] : prev));
  }

  function handleCompareTickerChange(e) {
    setCompareTicker(e.target.value);
    setCompareState((s) => ({ ...s, active: false }));
  }

  async function handleCompare() {
    if (compareTicker === ticker) {
      setCompareState({ active: true, loading: false, error: "Pick a different symbol to compare.", data: null });
      return;
    }
    setCompareState({ active: true, loading: true, error: "", data: null });
    try {
      const result = await getVolatility(compareTicker);
      setCompareState({ active: true, loading: false, error: "", data: result });
    } catch (err) {
      setCompareState({
        active: true,
        loading: false,
        error: err.response?.data?.detail || "Failed to load comparison data.",
        data: null,
      });
    }
  }

  let spike = null;
  let explanation = null;

  if (data) {
    spike = buildSpikeChartData(data);

    // same array + same threshold already used for the chart's point highlighting, so the
    // "why" text below always agrees with what's actually drawn
    const highVolMask = spike.history.map((v) => v > spike.threshold);
    const highVolatilityPeriods = contiguousRanges(data.dates, highVolMask);

    explanation = buildVolatilityExplanation(ticker, {
      currentValue: spike.currentValue,
      topPercent: spike.topPercent,
      threshold: spike.threshold,
      params: data.params,
      highVolatilityPeriods,
    });
  }

  const compareSpike = compareState.data ? buildSpikeChartData(compareState.data) : null;

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

      {!loading && !error && data && spike && (
        <>
          <div className="card risk-indicator">
            <span className="stat-label">Current risk level</span>
            <p className="stat-value">
              {spike.topPercent <= 0 ? "Highest" : `Top ${spike.topPercent}%`} of historical volatility for {ticker}
            </p>
            <p className="hint">
              Current conditional volatility ({spike.currentValue.toFixed(5)}) compared against this stock's own full
              history. Points above the dashed {Math.round(HIGH_VOL_QUANTILE * 100)}th-percentile line
              ({spike.threshold.toFixed(5)}) are highlighted in red, showing where volatility clustering has occurred.
            </p>
          </div>

          <div className="card chart-fade-in">
            <ZoomableLine data={spike.chartData} options={spike.chartOptions} />
          </div>

          {explanation && (
            <div className="card summary-panel">
              <h2>Why is {ticker} volatile?</h2>
              <ul className="summary-bullets">
                {explanation.bullets.map((bullet, i) => (
                  <li key={i}>{bullet}</li>
                ))}
              </ul>
              <div className="summary-narrative">
                {explanation.paragraphs.map((paragraph, i) => (
                  <p key={i}>{paragraph}</p>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      <div className="card summary-panel">
        <h2>Compare volatility across symbols</h2>
        <p className="hint">
          Pick another symbol and compare it against {ticker}. "Persistence" (alpha + beta from each symbol's GARCH
          model) shows how strongly volatility clusters day-to-day -- closer to 1 means a volatile day is more likely
          to be followed by another volatile day.
        </p>

        <div className="explorer-controls">
          <select value={compareTicker} onChange={handleCompareTickerChange}>
            {TICKERS.filter((t) => t !== ticker).map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <button type="button" className="btn-primary" onClick={handleCompare} disabled={compareState.loading}>
            {compareState.loading ? "Comparing..." : "Compare"}
          </button>
        </div>

        {compareState.active && compareState.loading && <LoadingSkeleton />}
        {compareState.active && compareState.error && <p className="error">{compareState.error}</p>}

        {compareState.active && !compareState.loading && !compareState.error && compareSpike && spike && (
          <>
            <div className="compare-charts-grid">
              <div>
                <h3>{ticker}</h3>
                <ZoomableLine data={spike.chartData} options={spike.chartOptions} />
              </div>
              <div>
                <h3>{compareTicker}</h3>
                <ZoomableLine data={compareSpike.chartData} options={compareSpike.chartOptions} />
              </div>
            </div>

            {(() => {
              const mainStats = volatilityStats(data);
              const compareStats = volatilityStats(compareState.data);
              const diff = compareSpike.currentValue - spike.currentValue;
              const rows = [
                { label: "Current volatility", main: spike.currentValue.toFixed(5), compare: compareSpike.currentValue.toFixed(5) },
                { label: "Historical average", main: mainStats.average.toFixed(5), compare: compareStats.average.toFixed(5) },
                { label: "Persistence (a+b)", main: mainStats.persistence.toFixed(3), compare: compareStats.persistence.toFixed(3) },
                { label: "10-day forecast avg.", main: mainStats.forecastAvg.toFixed(5), compare: compareStats.forecastAvg.toFixed(5) },
                {
                  label: `Diff. (${compareTicker} vs ${ticker})`,
                  main: "--",
                  compare: `${diff > 0 ? "+" : ""}${diff.toFixed(5)}`,
                  compareClassName: diff > 0 ? "diff-up" : diff < 0 ? "diff-down" : "",
                },
              ];
              return (
                <div className="table-scroll">
                  <table className="comparison-table comparison-table-vertical">
                    <thead>
                      <tr>
                        <th>Factor</th>
                        <th>{ticker}</th>
                        <th>{compareTicker}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row) => (
                        <tr key={row.label}>
                          <td>{row.label}</td>
                          <td>{row.main}</td>
                          <td className={row.compareClassName || ""}>{row.compare}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              );
            })()}
          </>
        )}
      </div>

      <SectionedExplanation ticker={ticker} />

      <ChatWidget ticker={ticker} />
    </div>
  );
}
