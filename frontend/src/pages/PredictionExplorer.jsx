import { useEffect, useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router-dom";
import { Line } from "react-chartjs-2";

import { explainChat, getPrediction } from "../api/client.js";
import ErrorRetry from "../components/ErrorRetry.jsx";
import LoadingSkeleton from "../components/LoadingSkeleton.jsx";
import { TICKERS } from "../constants/tickers.js";
import { useTickerData } from "../hooks/useTickerData.js";
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

export default function PredictionExplorer() {
  const [searchParams] = useSearchParams();
  const [ticker, setTicker] = useState(searchParams.get("ticker") || TICKERS[0]);
  const { data, loading, error, retry } = useTickerData(getPrediction, ticker);
  const [model, setModel] = useState("xgboost");
  const [selectedDate, setSelectedDate] = useState("");
  const [narrative, setNarrative] = useState({ loading: false, error: "", answer: "" });

  const { xgboost, lstm, hasBoth } = data ? resolveModels(data) : {};
  const active = model === "lstm" && lstm ? lstm : xgboost;
  const dates = active?.dates ?? [];

  useEffect(() => {
    if (dates.length > 0) {
      setSelectedDate(dates[dates.length - 1]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  useEffect(() => {
    setNarrative({ loading: false, error: "", answer: "" });
  }, [ticker, selectedDate]);

  // hooks must run unconditionally above this line -- only the JSX return is conditional
  if (!localStorage.getItem("token")) {
    return <Navigate to="/login" replace />;
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
        borderColor: "#16a34a",
        pointRadius: dates.map((_, i) => (i === selectedIndex ? 6 : 0)),
        pointBackgroundColor: "#16a34a",
      },
      {
        label: "Predicted",
        data: active.predictions,
        borderColor: "#dc2626",
        pointRadius: dates.map((_, i) => (i === selectedIndex ? 6 : 0)),
        pointBackgroundColor: "#dc2626",
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

          <div className="card">
            <Line data={chartData} options={chartOptions} />
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

          <div className="card narrative-panel">
            <h2>Why did the model predict this?</h2>
            <button type="button" onClick={handleExplain} disabled={narrative.loading || !selectedDate}>
              {narrative.loading ? "Thinking..." : `Explain the prediction for ${selectedDate}`}
            </button>
            {narrative.error && <p className="error">{narrative.error}</p>}
            {narrative.answer && <p className="narrative-answer">{narrative.answer}</p>}
          </div>
        </>
      )}
    </div>
  );
}
