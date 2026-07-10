import { useState } from "react";
import { Line } from "react-chartjs-2";

import { getPrediction } from "../api/client.js";
import { useTickerData } from "../hooks/useTickerData.js";
import { resolveModels } from "../utils/predictionModels.js";
import ErrorRetry from "./ErrorRetry.jsx";
import LoadingSkeleton from "./LoadingSkeleton.jsx";

export default function PredictionChart({ ticker }) {
  const { data, loading, error, retry } = useTickerData(getPrediction, ticker);
  const [model, setModel] = useState("xgboost");

  if (loading) {
    return (
      <div className="card">
        <h2>Next-Day Return Prediction</h2>
        <LoadingSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <h2>Next-Day Return Prediction</h2>
        <ErrorRetry message={error} onRetry={retry} />
      </div>
    );
  }

  if (!data) return null;

  const { xgboost, lstm, hasBoth } = resolveModels(data);
  const active = model === "lstm" && lstm ? lstm : xgboost;

  if (!active) {
    return (
      <div className="card">
        <h2>Next-Day Return Prediction</h2>
        <p className="error">No prediction data available.</p>
      </div>
    );
  }

  const chartData = {
    labels: active.dates,
    datasets: [
      { label: "Actual", data: active.actual, borderColor: "#16a34a", pointRadius: 0 },
      { label: "Predicted", data: active.predictions, borderColor: "#dc2626", pointRadius: 0 },
    ],
  };

  return (
    <div className="card">
      <h2>Next-Day Return Prediction</h2>
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
      <Line data={chartData} options={{ responsive: true, animation: false }} />
      <p>
        RMSE: {active.metrics.rmse.toFixed(5)} · MAE: {active.metrics.mae.toFixed(5)} · Directional accuracy:{" "}
        {active.metrics.directional_accuracy.toFixed(1)}%
      </p>
    </div>
  );
}
