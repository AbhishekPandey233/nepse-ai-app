import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Bar, Line } from "react-chartjs-2";

import { getDetailedFactors, getExplanation, getHistory, getPrediction } from "../api/client.js";
import ChatWidget from "../components/ChatWidget.jsx";
import ErrorRetry from "../components/ErrorRetry.jsx";
import ExplainabilityChart from "../components/ExplainabilityChart.jsx";
import LoadingSkeleton from "../components/LoadingSkeleton.jsx";
import { TICKERS } from "../constants/tickers.js";
import { useTickerData } from "../hooks/useTickerData.js";
import { themeColor } from "../theme.js";
import { buildPriceHistoryChartData, buildTrendSummary } from "../utils/historyNarrative.js";

// hard-coded since the feature set is fixed (data_loader.py's engineered + raw columns)
const FEATURE_GLOSSARY = {
  s_no: "Row order from the daily exchange listing (not a market signal).",
  conf: "Confidence/certainty score reported for that day's trade.",
  open: "The stock's opening price for the day.",
  high: "The highest price reached during the day.",
  low: "The lowest price reached during the day.",
  vwap: "The volume-weighted average price for the day.",
  vol: "Number of shares traded that day.",
  prev_close: "The previous trading day's closing price.",
  turnover: "Total value (NPR) of shares traded that day.",
  trans: "Number of individual trades executed that day.",
  diff: "Change in price from the previous close.",
  range: "Difference between the day's high and low price.",
  diff_pct: "Percentage change in price from the previous close.",
  range_pct: "Day's trading range as a percentage of price.",
  vwap_pct: "How far the closing price sits from the volume-weighted average price.",
  "120_days": "120-day rolling average price -- a medium-term price trend.",
  "180_days": "180-day rolling average price -- a longer-term price trend.",
  "52_weeks_high": "The highest price over the past 52 weeks.",
  "52_weeks_low": "The lowest price over the past 52 weeks.",
  ltp: "The last traded price for the day.",
  close_ltp: "Difference between the closing price and the last traded price.",
  close_ltp_pct: "Percentage difference between closing price and last traded price.",
  log_return: "That day's price return -- how much the price moved.",
  ma_5: "5-day average price trend.",
  ma_10: "10-day average price trend.",
  ma_20: "20-day average price trend.",
  rsi_14: "Momentum indicator: whether the stock looks overbought or oversold (14-day).",
  volatility_20: "Recent price swing size over the last 20 days.",
  lag_return_1: "The return from 1 trading day ago.",
  lag_return_2: "The return from 2 trading days ago.",
  lag_return_3: "The return from 3 trading days ago.",
};

const FALLBACK_GLOSSARY_ENTRY = "A statistical trading feature used by the prediction model.";

export default function ExplainabilityPage() {
  const [searchParams] = useSearchParams();
  const [ticker, setTicker] = useState(searchParams.get("ticker") || TICKERS[0]);
  const predictResult = useTickerData(getPrediction, ticker); // only used to label the most recent date
  const { data, loading, error, retry } = useTickerData(getExplanation, ticker);
  const historyResult = useTickerData(getHistory, ticker);
  const [narrative, setNarrative] = useState({ loading: false, error: "", answer: "" });
  const [expanded, setExpanded] = useState(false);

  async function handleExplain() {
    setNarrative({ loading: true, error: "", answer: "" });
    setExpanded(false);
    try {
      const result = await getDetailedFactors(ticker);
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

  let topEntries = [];
  let waterfallData = null;
  let mostRecentDate = "the most recent available prediction";

  if (data) {
    const lastRowShap = data.per_row_shap[data.per_row_shap.length - 1];
    topEntries = Object.entries(lastRowShap)
      .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
      .slice(0, 10);

    const goodColor = themeColor("--chart-good");
    const criticalColor = themeColor("--chart-critical");

    waterfallData = {
      labels: topEntries.map(([name]) => name),
      datasets: [
        {
          label: "SHAP contribution",
          data: topEntries.map(([, value]) => value),
          backgroundColor: topEntries.map(([, value]) => (value >= 0 ? goodColor : criticalColor)),
        },
      ],
    };

    const predictDates = predictResult.data?.dates;
    if (predictDates?.length) {
      mostRecentDate = predictDates[predictDates.length - 1];
    }
  }

  let priceHistoryChartData = null;
  let trendSummary = null;

  if (historyResult.data) {
    const { dates, close, summary } = historyResult.data;
    priceHistoryChartData = buildPriceHistoryChartData(
      { dates, close },
      summary,
      {
        cyan: themeColor("--chart-cyan"),
        good: themeColor("--chart-good"),
        critical: themeColor("--chart-critical"),
      }
    );
    trendSummary = buildTrendSummary(ticker, summary);
  }

  const priceHistoryOptions = { responsive: true, animation: false };

  const waterfallOptions = {
    indexAxis: "y",
    responsive: true,
    plugins: { legend: { display: false } },
  };

  return (
    <div className="explainability-page">
      <Link to="/dashboard" className="toggle-link">
        &larr; Back to dashboard
      </Link>
      <h1>Model Explainability</h1>

      <div className="explorer-controls">
        <select value={ticker} onChange={handleTickerChange}>
          {TICKERS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      {historyResult.loading && (
        <div className="card">
          <LoadingSkeleton />
        </div>
      )}

      {historyResult.error && (
        <div className="card">
          <ErrorRetry message={historyResult.error} onRetry={historyResult.retry} />
        </div>
      )}

      {!historyResult.loading && !historyResult.error && priceHistoryChartData && trendSummary && (
        <div className="card summary-panel chart-fade-in">
          <h2>Historical trend &amp; outliers</h2>
          <p className="hint">
            Price history with the highest/lowest closes and largest single-day moves highlighted (green = high/gain,
            red = low/loss). Hover a point for the exact date and price.
          </p>
          <Line data={priceHistoryChartData} options={priceHistoryOptions} />
          <ul className="summary-bullets">
            {trendSummary.bullets.map((bullet, i) => (
              <li key={i}>{bullet}</li>
            ))}
          </ul>
          <div className="summary-narrative">
            {trendSummary.paragraphs.map((paragraph, i) => (
              <p key={i}>{paragraph}</p>
            ))}
          </div>
        </div>
      )}

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
          <ExplainabilityChart ticker={ticker} />

          <div className="card chart-fade-in">
            <h2>Why the latest prediction ({mostRecentDate})</h2>
            <p className="hint">
              How each feature pushed this specific prediction up (green) or down (red) from the model's baseline.
            </p>
            <Bar data={waterfallData} options={waterfallOptions} />
          </div>

          <div className="card">
            <h2>Feature glossary</h2>
            <dl className="glossary">
              {topEntries.map(([name]) => (
                <div className="glossary-entry" key={name}>
                  <dt>{name}</dt>
                  <dd>{FEATURE_GLOSSARY[name] || FALLBACK_GLOSSARY_ENTRY}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div className="card summary-panel narrative-panel">
            <h2>Detailed explanation</h2>
            <p className="hint">
              A full, plain-language walkthrough of the top factors behind the latest prediction, with real numbers
              for {ticker} and real-world analogies -- generated by the local AI model.
            </p>
            <button type="button" className="btn-primary" onClick={handleExplain} disabled={narrative.loading}>
              {narrative.loading ? "Thinking... (this can take up to a minute)" : "Explain in detail"}
            </button>
            {narrative.error && <p className="error">{narrative.error}</p>}
            {narrative.answer &&
              (() => {
                const paragraphs = narrative.answer.split("\n\n");
                const previewCount = Math.min(3, paragraphs.length);
                const preview = paragraphs.slice(0, previewCount);
                const rest = paragraphs.slice(previewCount);
                return (
                  <div className="summary-narrative">
                    {preview.map((paragraph, i) => <p key={i}>{paragraph}</p>)}
                    {expanded && rest.map((paragraph, i) => <p key={i}>{paragraph}</p>)}
                    {rest.length > 0 && (
                      <button type="button" onClick={() => setExpanded((v) => !v)}>
                        {expanded ? "Show less" : "More information"}
                      </button>
                    )}
                  </div>
                );
              })()}
          </div>
        </>
      )}

      <ChatWidget ticker={ticker} />
    </div>
  );
}
