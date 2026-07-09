import { Line } from "react-chartjs-2";

import { getVolatility } from "../api/client.js";
import { useTickerData } from "../hooks/useTickerData.js";
import ErrorRetry from "./ErrorRetry.jsx";
import LoadingSkeleton from "./LoadingSkeleton.jsx";

export default function VolatilityChart({ ticker }) {
  const { data, loading, error, retry } = useTickerData(getVolatility, ticker);

  if (loading) {
    return (
      <div className="card">
        <h2>Volatility (GARCH 1,1)</h2>
        <LoadingSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <h2>Volatility (GARCH 1,1)</h2>
        <ErrorRetry message={error} onRetry={retry} />
      </div>
    );
  }

  if (!data) return null;

  const forecastLabels = data.forecast.map((_, i) => `+${i + 1}d`);
  const labels = [...data.dates, ...forecastLabels];

  const historical = [...data.conditional_volatility, ...new Array(data.forecast.length).fill(null)];
  const forecastLine = [
    ...new Array(data.conditional_volatility.length - 1).fill(null),
    data.conditional_volatility[data.conditional_volatility.length - 1],
    ...data.forecast,
  ];

  const chartData = {
    labels,
    datasets: [
      {
        label: "Conditional volatility",
        data: historical,
        borderColor: "#2563eb",
        pointRadius: 0,
      },
      {
        label: "Forecast",
        data: forecastLine,
        borderColor: "#f59e0b",
        borderDash: [6, 6],
        pointRadius: 0,
      },
    ],
  };

  return (
    <div className="card">
      <h2>Volatility (GARCH 1,1)</h2>
      <Line data={chartData} options={{ responsive: true, animation: false }} />
    </div>
  );
}
