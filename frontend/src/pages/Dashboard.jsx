import { useState } from "react";
import { Navigate } from "react-router-dom";

import { getEfficiency } from "../api/client.js";

const TICKERS = ["NABIL", "ADBL", "AHPC", "API", "AKPL"];

export default function Dashboard() {
  const [ticker, setTicker] = useState(TICKERS[0]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (!localStorage.getItem("token")) {
    return <Navigate to="/login" replace />;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await getEfficiency(ticker);
      console.log("efficiency result:", data);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to fetch analysis.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1>Dashboard</h1>
      <form onSubmit={handleSubmit}>
        <select value={ticker} onChange={(e) => setTicker(e.target.value)}>
          {TICKERS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={loading}>
          {loading ? "Loading..." : "Run efficiency analysis"}
        </button>
      </form>
      <p>Check the browser console for the result. Charts land in the next phase.</p>
    </div>
  );
}
