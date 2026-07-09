import { Bar } from "react-chartjs-2";

import { getExplanation } from "../api/client.js";
import { useTickerData } from "../hooks/useTickerData.js";
import ErrorRetry from "./ErrorRetry.jsx";
import LoadingSkeleton from "./LoadingSkeleton.jsx";

export default function ExplainabilityChart({ ticker }) {
  const { data, loading, error, retry } = useTickerData(getExplanation, ticker);

  if (loading) {
    return (
      <div className="card">
        <h2>Top Feature Importance (SHAP)</h2>
        <LoadingSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <h2>Top Feature Importance (SHAP)</h2>
        <ErrorRetry message={error} onRetry={retry} />
      </div>
    );
  }

  if (!data) return null;

  const top10 = [...data.feature_importance].sort((a, b) => b.mean_abs_shap - a.mean_abs_shap).slice(0, 10);

  const chartData = {
    labels: top10.map((f) => f.feature),
    datasets: [
      {
        label: "Mean |SHAP value|",
        data: top10.map((f) => f.mean_abs_shap),
        backgroundColor: "#2563eb",
      },
    ],
  };

  return (
    <div className="card">
      <h2>Top Feature Importance (SHAP)</h2>
      <Bar data={chartData} options={{ indexAxis: "y", responsive: true, plugins: { legend: { display: false } } }} />
    </div>
  );
}
