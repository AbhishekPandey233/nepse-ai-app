import { getEfficiency } from "../api/client.js";
import { useTickerData } from "../hooks/useTickerData.js";

export default function EfficiencyCard({ ticker }) {
  const { data, loading, error } = useTickerData(getEfficiency, ticker);

  if (loading) {
    return (
      <div className="card">
        <h2>Market Efficiency</h2>
        <p>Loading efficiency analysis...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <h2>Market Efficiency</h2>
        <p className="error">{error}</p>
      </div>
    );
  }

  if (!data) return null;

  const isEfficient = !data.verdict.includes("AGAINST");

  return (
    <div className="card">
      <h2>Market Efficiency</h2>
      <span className={`badge ${isEfficient ? "badge-green" : "badge-amber"}`}>
        {isEfficient ? "Weak-form efficient" : "Evidence of inefficiency"}
      </span>
      <p>{data.verdict}</p>
      <details>
        <summary>Show statistics</summary>
        <ul>
          <li>
            ADF statistic: {data.adf.statistic.toFixed(4)} (p = {data.adf.p_value.toExponential(3)})
          </li>
          <li>
            Ljung-Box (lag {data.ljung_box.lags}): {data.ljung_box.statistic.toFixed(4)} (p ={" "}
            {data.ljung_box.p_value.toFixed(4)})
          </li>
          <li>
            Variance ratio (k={data.variance_ratio.k}): {data.variance_ratio.variance_ratio.toFixed(4)} (p ={" "}
            {data.variance_ratio.p_value.toFixed(4)})
          </li>
        </ul>
      </details>
    </div>
  );
}
