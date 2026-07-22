import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bar } from "react-chartjs-2";

import { getMarketSummary } from "../api/client.js";
import ErrorRetry from "../components/ErrorRetry.jsx";
import LoadingSkeleton from "../components/LoadingSkeleton.jsx";
import { themeColor } from "../theme.js";

function histogram(values, bins = 8) {
  if (values.length === 0) return { labels: [], counts: [] };
  const min = Math.min(...values);
  const max = Math.max(...values);
  const width = (max - min) / bins || 1;
  const counts = new Array(bins).fill(0);
  for (const v of values) {
    const idx = Math.min(bins - 1, Math.floor((v - min) / width));
    counts[idx] += 1;
  }
  const labels = counts.map((_, i) => `${(min + i * width).toFixed(2)}`);
  return { labels, counts };
}

const STAT_BLOCKS = [
  { key: "adf_stat", label: "ADF statistic", hint: "More negative = stronger rejection of a unit root (mean-reverting, not a pure random walk)." },
  { key: "variance_ratio", label: "Variance ratio", hint: "Far from 1.0 = returns deviate from a random walk (momentum > 1, mean-reversion < 1)." },
  { key: "garch_persistence", label: "GARCH persistence (α+β)", hint: "Closer to 1 = volatility clusters harder and shocks fade more slowly." },
];

export default function MarketOverview() {
  const [state, setState] = useState({ loading: true, error: "", data: null });
  const [query, setQuery] = useState("");

  async function load() {
    setState({ loading: true, error: "", data: null });
    try {
      const data = await getMarketSummary();
      setState({ loading: false, error: "", data });
    } catch (err) {
      const message =
        err.response?.status === 404
          ? "Market summary hasn't been built yet. Run scripts/build_market_summary.py on the backend."
          : err.response?.data?.detail || "Failed to load market summary.";
      setState({ loading: false, error: message, data: null });
    }
  }

  useEffect(() => {
    load();
  }, []);

  const { loading, error, data } = state;

  let adfHist = null;
  if (data) {
    const values = data.per_symbol.map((r) => r.adf_stat);
    const { labels, counts } = histogram(values);
    adfHist = {
      labels,
      datasets: [
        {
          label: "Number of symbols",
          data: counts,
          backgroundColor: themeColor("--chart-cyan"),
        },
      ],
    };
  }

  const histOptions = {
    responsive: true,
    animation: false,
    plugins: { legend: { display: false } },
    scales: { x: { title: { display: true, text: "ADF statistic (bin start)" } } },
  };

  return (
    <div className="market-overview">
      <Link to="/dashboard" className="toggle-link">
        &larr; Back to dashboard
      </Link>
      <h1>Market Overview</h1>

      {loading && (
        <div className="card">
          <LoadingSkeleton />
        </div>
      )}

      {error && (
        <div className="card">
          <ErrorRetry message={error} onRetry={load} />
        </div>
      )}

      {!loading && !error && data && (
        <>
          <p className="hint">
            Aggregated across the {data.n_symbols_processed} highest-turnover NEPSE symbols
            {data.n_symbols_skipped > 0 ? ` (${data.n_symbols_skipped} skipped for insufficient data)` : ""}.
            {data.generated_at ? ` Last computed ${new Date(data.generated_at).toLocaleString()}.` : ""}
          </p>

          <div className="card risk-indicator">
            <span className="stat-label">Evidence against weak-form efficiency</span>
            <p className="stat-value">{data.pct_against_efficiency}% of symbols</p>
            <p className="hint">
              {data.n_against_efficiency} of {data.n_symbols_processed} symbols show significant return
              autocorrelation and/or a variance ratio that departs from a random walk (p &lt; 0.05).
            </p>
          </div>

          <div className="stat-cards">
            {STAT_BLOCKS.map(({ key, label, hint }) => {
              const s = data[key];
              return (
                <div className="stat-card" key={key}>
                  <span className="stat-label">{label}</span>
                  <span className="stat-value">{s.mean?.toFixed(3)}</span>
                  <p className="stat-explain">
                    mean {s.mean?.toFixed(3)} · median {s.median?.toFixed(3)} · std {s.std?.toFixed(3)}
                    <br />
                    {hint}
                  </p>
                </div>
              );
            })}
          </div>

          <div className="card chart-fade-in">
            <h2>Distribution of ADF statistics across the market</h2>
            <p className="hint">
              How many of the {data.n_symbols_processed} symbols fall in each ADF-statistic range. A cluster of very
              negative values means much of the market is mean-reverting rather than a pure random walk.
            </p>
            <Bar data={adfHist} options={histOptions} />
          </div>

          {(() => {
            const q = query.trim().toUpperCase();
            const rows = q ? data.per_symbol.filter((r) => r.symbol.includes(q)) : data.per_symbol;
            return (
              <div className="card summary-panel">
                <h2>Per-symbol detail</h2>
                <div className="explorer-controls">
                  <input
                    type="search"
                    placeholder="Search symbol (e.g. NABIL)"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    aria-label="Search symbol"
                  />
                  {q && (
                    <button type="button" onClick={() => setQuery("")}>
                      Clear
                    </button>
                  )}
                </div>
                <p className="hint">
                  Showing {rows.length} of {data.per_symbol.length} symbols.
                </p>

                {rows.length === 0 ? (
                  <p className="hint">
                    No symbol matching "{query.trim()}" in this summary. It covers only the{" "}
                    {data.n_symbols_processed} highest-turnover symbols — rebuild with a wider universe
                    (<code>python scripts/build_market_summary.py --n 100</code>) to include more.
                  </p>
                ) : (
                  <div className="table-scroll">
                    <table className="comparison-table">
                      <thead>
                        <tr>
                          <th>Symbol</th>
                          <th>Against efficiency?</th>
                          <th>ADF statistic</th>
                          <th>Variance ratio</th>
                          <th>GARCH persistence</th>
                        </tr>
                      </thead>
                      <tbody>
                        {rows.map((r) => (
                          <tr key={r.symbol} className={q && r.symbol === q ? "comparison-row-selected" : ""}>
                            <td>{r.symbol}</td>
                            <td className={r.against_efficiency ? "diff-up" : "diff-down"}>
                              {r.against_efficiency ? "Yes" : "No"}
                            </td>
                            <td>{r.adf_stat.toFixed(3)}</td>
                            <td>{r.variance_ratio.toFixed(3)}</td>
                            <td>{r.garch_persistence.toFixed(3)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })()}
        </>
      )}
    </div>
  );
}
