import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { explainChat, getBacktest, getModelComparison, getPrediction } from "../api/client.js";
import ChatWidget from "../components/ChatWidget.jsx";
import ErrorRetry from "../components/ErrorRetry.jsx";
import LoadingSkeleton from "../components/LoadingSkeleton.jsx";
import SectionedExplanation from "../components/SectionedExplanation.jsx";
import ZoomableLine from "../components/ZoomableLine.jsx";
import { TICKERS } from "../constants/tickers.js";
import { useTickerData } from "../hooks/useTickerData.js";
import { themeColor } from "../theme.js";
import { resolveModels } from "../utils/predictionModels.js";

function findNearestDate(dates, target) {
  if (dates.includes(target)) return target;
  const targetTime = new Date(target).getTime();
  return dates.reduce((closest, d) =>
    Math.abs(new Date(d).getTime() - targetTime) < Math.abs(new Date(closest).getTime() - targetTime) ? d : closest
  );
}

const METRIC_INFO = [
  {
    key: "rmse",
    label: "RMSE",
    format: (v) => v.toFixed(5),
    explain: "Root Mean Squared Error: the typical size of the model's prediction error, weighted so bigger misses count more.",
  },
  {
    key: "mae",
    label: "MAE",
    format: (v) => v.toFixed(5),
    explain: "Mean Absolute Error: the average size of the model's prediction error, treating all misses equally.",
  },
  {
    key: "directional_accuracy",
    label: "Directional accuracy",
    format: (v) => `${v.toFixed(1)}%`,
    explain: "How often the model correctly predicted whether the return would go up or down, regardless of size.",
  },
];

const MODEL_ORDER = ["naive", "arima", "xgboost", "lstm"];
const MODEL_LABELS = {
  naive: "Naive (traditional)",
  arima: "ARIMA (traditional)",
  xgboost: "XGBoost (AI)",
  lstm: "LSTM (AI)",
};
const COMPARE_METRICS = [
  { key: "rmse", label: "RMSE", lowerBetter: true, format: (v) => v.toFixed(5) },
  { key: "mae", label: "MAE", lowerBetter: true, format: (v) => v.toFixed(5) },
  { key: "directional_accuracy", label: "Directional acc.", lowerBetter: false, format: (v) => `${v.toFixed(1)}%` },
];

function bestModelPerMetric(models) {
  const best = {};
  for (const { key, lowerBetter } of COMPARE_METRICS) {
    let winner = null;
    for (const name of MODEL_ORDER) {
      const v = models[name]?.metrics?.[key];
      if (typeof v !== "number") continue;
      if (winner === null || (lowerBetter ? v < best[key].value : v > best[key].value)) {
        winner = name;
        best[key] = { value: v, name };
      }
    }
  }
  return best;
}

export default function PredictionExplorer() {
  const [searchParams] = useSearchParams();
  const [ticker, setTicker] = useState(searchParams.get("ticker") || TICKERS[0]);
  const { data, loading, error, retry } = useTickerData(getPrediction, ticker);
  const [model, setModel] = useState("xgboost");
  const [selectedDate, setSelectedDate] = useState("");
  const [narrative, setNarrative] = useState({ loading: false, error: "", answer: "" });
  const [compare, setCompare] = useState({ loading: false, error: "", data: null });
  const [txCost, setTxCost] = useState(0.5);
  const [backtest, setBacktest] = useState({ loading: false, error: "", data: null });

  const { xgboost, lstm, hasBoth } = data ? resolveModels(data) : {};
  const active = model === "lstm" && lstm ? lstm : xgboost;
  const dates = active?.dates ?? [];

  useEffect(() => {
    if (dates.length > 0) {
      setSelectedDate(dates[dates.length - 1]);
    }
  }, [active]);

  useEffect(() => {
    setNarrative({ loading: false, error: "", answer: "" });
  }, [ticker, selectedDate]);

  useEffect(() => {
    setCompare({ loading: false, error: "", data: null });
    setBacktest({ loading: false, error: "", data: null });
  }, [ticker]);

  async function handleBacktest() {
    setBacktest({ loading: true, error: "", data: null });
    try {
      const result = await getBacktest(ticker, txCost);
      setBacktest({ loading: false, error: "", data: result });
    } catch (err) {
      const message =
        err.response?.status === 404
          ? "No data for this ticker yet."
          : err.response?.data?.detail || "Something went wrong. Please try again.";
      setBacktest({ loading: false, error: message, data: null });
    }
  }

  async function handleCompareModels() {
    setCompare({ loading: true, error: "", data: null });
    try {
      const result = await getModelComparison(ticker);
      setCompare({ loading: false, error: "", data: result });
    } catch (err) {
      const message =
        err.response?.status === 404
          ? "No data for this ticker yet."
          : err.response?.data?.detail || "Something went wrong. Please try again.";
      setCompare({ loading: false, error: message, data: null });
    }
  }

  function handleDateChange(e) {
    if (dates.length === 0) return;
    setSelectedDate(findNearestDate(dates, e.target.value));
  }

  async function handleExplain() {
    setNarrative({ loading: true, error: "", answer: "" });
    try {
      const question = `Explain this prediction for ${ticker} on ${selectedDate}, including which factors most influenced it`;
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

  const selectedIndex = dates.indexOf(selectedDate);

  const chartData = active && {
    labels: dates,
    datasets: [
      {
        label: "Actual",
        data: active.actual,
        borderColor: themeColor("--chart-cyan"),
        pointRadius: dates.map((_, i) => (i === selectedIndex ? 6 : 0)),
        pointBackgroundColor: themeColor("--chart-cyan"),
      },
      {
        label: "Predicted",
        data: active.predictions,
        borderColor: themeColor("--chart-violet"),
        pointRadius: dates.map((_, i) => (i === selectedIndex ? 6 : 0)),
        pointBackgroundColor: themeColor("--chart-violet"),
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    animation: false,
    plugins: {
      zoom: {
        pan: { enabled: true, mode: "x" },
        zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: "x" },
      },
    },
  };

  const forecast = data?.next_day_forecast;
  const forecastPct = forecast ? (Math.exp(forecast.predicted_return) - 1) * 100 : null;

  const backtestChartData = backtest.data && {
    labels: backtest.data.dates,
    datasets: [
      {
        label: "AI-signal strategy",
        data: backtest.data.strategy_cumulative.map((v) => v * 100),
        borderColor: themeColor("--chart-violet"),
        pointRadius: 0,
      },
      {
        label: "Buy & hold",
        data: backtest.data.buy_hold_cumulative.map((v) => v * 100),
        borderColor: themeColor("--chart-cyan"),
        pointRadius: 0,
      },
    ],
  };
  const backtestChartOptions = {
    responsive: true,
    animation: false,
    scales: { y: { title: { display: true, text: "Cumulative return (%)" } } },
  };

  return (
    <div className="prediction-explorer">
      <Link to="/dashboard" className="toggle-link">
        &larr; Back to dashboard
      </Link>
      <h1>Prediction Explorer</h1>

      <div className="explorer-controls">
        <select value={ticker} onChange={(e) => setTicker(e.target.value)}>
          {TICKERS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>

        {dates.length > 0 && (
          <input
            type="date"
            min={dates[0]}
            max={dates[dates.length - 1]}
            value={selectedDate}
            onChange={handleDateChange}
          />
        )}
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

      {!loading && !error && active && (
        <>
          <p className="hint">
            Predictions are available for the model's held-out test period: {dates[0]} to {dates[dates.length - 1]}.
            Scroll/pinch to zoom, drag to pan.
          </p>

          {hasBoth && (
            <div className="button-group">
              <button type="button" onClick={() => setModel("xgboost")} disabled={model === "xgboost"}>
                XGBoost
              </button>
              <button type="button" onClick={() => setModel("lstm")} disabled={model === "lstm"}>
                LSTM
              </button>
            </div>
          )}

          <div className="card chart-fade-in">
            <ZoomableLine data={chartData} options={chartOptions} />
          </div>

          <div className="stat-cards">
            {METRIC_INFO.map(({ key, label, format, explain }) => (
              <div className="stat-card" key={key}>
                <span className="stat-label">{label}</span>
                <span className="stat-value">{format(active.metrics[key])}</span>
                <p className="stat-explain">{explain}</p>
              </div>
            ))}
          </div>

          {forecast && (
            <div className="card forecast-card">
              <h2>Next trading day forecast</h2>
              <p className={`forecast-value ${forecastPct >= 0 ? "forecast-up" : "forecast-down"}`}>
                {forecastPct >= 0 ? "+" : ""}
                {forecastPct.toFixed(2)}%
              </p>
              <p className="hint">
                Predicted return for the next trading day after {forecast.as_of_date}, based on that day's data.
                This is a genuine forward forecast, not a historical test-period value.
              </p>
            </div>
          )}

          <div className="card summary-panel">
            <h2>AI vs. traditional models</h2>
            <p className="hint">
              How the AI models (XGBoost, LSTM) compare against traditional baselines (a naive random-walk and ARIMA)
              on the exact same held-out test period for {ticker}. Lower RMSE/MAE is better; higher directional
              accuracy is better. The best value in each row is highlighted.
            </p>
            <button
              type="button"
              className="btn-primary"
              onClick={handleCompareModels}
              disabled={compare.loading}
            >
              {compare.loading ? "Running all four models..." : "Compare all models"}
            </button>
            {compare.error && <p className="error">{compare.error}</p>}

            {compare.data &&
              (() => {
                const { models } = compare.data;
                const best = bestModelPerMetric(models);
                const shown = MODEL_ORDER.filter((name) => models[name]);
                return (
                  <div className="table-scroll">
                    <table className="comparison-table comparison-table-vertical">
                      <thead>
                        <tr>
                          <th>Metric</th>
                          {shown.map((name) => (
                            <th key={name}>
                              {MODEL_LABELS[name]}
                              {name === "naive" && models[name].variant ? ` (${models[name].variant})` : ""}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {COMPARE_METRICS.map(({ key, label, format }) => (
                          <tr key={key}>
                            <td>{label}</td>
                            {shown.map((name) => {
                              const m = models[name].metrics;
                              if (!m) return <td key={name}>--</td>;
                              const isBest = best[key]?.name === name;
                              return (
                                <td key={name} className={isBest ? "diff-down" : ""}>
                                  {format(m[key])}
                                  {isBest ? " ✓" : ""}
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {models.lstm?.error && (
                      <p className="hint">LSTM unavailable ({models.lstm.error}); comparison shown without it.</p>
                    )}
                  </div>
                );
              })()}
          </div>

          <div className="card summary-panel">
            <h2>Backtest: does the AI signal beat buy-and-hold?</h2>
            <p className="hint">
              A simple long/flat strategy -- go long when the model predicts a positive next-day return, otherwise
              hold cash -- over the held-out test period for {ticker}, charged a transaction cost on each position
              change. If it beats buy-and-hold net of costs, that's evidence of exploitable inefficiency; if not,
              that's consistent with an efficient market.
            </p>
            <div className="explorer-controls">
              <label className="hint">
                Transaction cost %:{" "}
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="5"
                  value={txCost}
                  onChange={(e) => setTxCost(Number(e.target.value))}
                  style={{ width: "5rem" }}
                />
              </label>
              <button type="button" className="btn-primary" onClick={handleBacktest} disabled={backtest.loading}>
                {backtest.loading ? "Running backtest..." : "Run backtest"}
              </button>
            </div>
            {backtest.error && <p className="error">{backtest.error}</p>}
            {backtest.data && (
              <>
                <ZoomableLine data={backtestChartData} options={backtestChartOptions} />
                <p className={backtest.data.outperformed ? "forecast-up" : "forecast-down"}>
                  {backtest.data.verdict}
                </p>
              </>
            )}
          </div>

          <div className="card narrative-panel">
            <h2>Why did the model predict this?</h2>
            <button type="button" className="btn-primary" onClick={handleExplain} disabled={narrative.loading || !selectedDate}>
              {narrative.loading ? "Thinking..." : `Explain the prediction for ${selectedDate}`}
            </button>
            {narrative.error && <p className="error">{narrative.error}</p>}
            {narrative.answer && <p className="narrative-answer">{narrative.answer}</p>}
          </div>

          <SectionedExplanation ticker={ticker} />
        </>
      )}

      <ChatWidget ticker={ticker} />
    </div>
  );
}
