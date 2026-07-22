import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { addHolding, deleteHolding, getHoldings, updateHolding } from "../api/client.js";
import LoadingSkeleton from "../components/LoadingSkeleton.jsx";

const EMPTY_FORM = { symbol: "", quantity: "", buy_price: "", buy_date: "" };

const fmt = (v, digits = 2) => (v === null || v === undefined ? "--" : Number(v).toFixed(digits));

export default function PortfolioPage() {
  const [holdings, setHoldings] = useState([]);
  const [state, setState] = useState({ loading: true, error: "" });
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);
  const [submitError, setSubmitError] = useState("");

  async function load() {
    setState({ loading: true, error: "" });
    try {
      setHoldings(await getHoldings());
      setState({ loading: false, error: "" });
    } catch (err) {
      setState({ loading: false, error: err.response?.data?.detail || "Failed to load portfolio." });
    }
  }

  useEffect(() => {
    load();
  }, []);

  function resetForm() {
    setForm(EMPTY_FORM);
    setEditingId(null);
    setSubmitError("");
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitError("");
    const payload = {
      quantity: Number(form.quantity),
      buy_price: Number(form.buy_price),
      buy_date: form.buy_date || null,
    };
    try {
      if (editingId) {
        await updateHolding(editingId, payload);
      } else {
        await addHolding({ ...payload, symbol: form.symbol.trim().toUpperCase() });
      }
      resetForm();
      await load();
    } catch (err) {
      setSubmitError(err.response?.data?.detail || "Could not save. Check the values and try again.");
    }
  }

  function startEdit(h) {
    setEditingId(h.id);
    setForm({ symbol: h.symbol, quantity: String(h.quantity), buy_price: String(h.buy_price), buy_date: h.buy_date || "" });
    setSubmitError("");
  }

  async function handleDelete(id) {
    await deleteHolding(id);
    if (editingId === id) resetForm();
    await load();
  }

  const totals = holdings.reduce(
    (acc, h) => {
      acc.cost += h.total_buy_cost || 0;
      acc.net += h.net_sell_value ?? 0;
      acc.charges += h.total_charges ?? h.buy_costs?.total ?? 0;
      acc.pnl += h.net_pnl ?? 0;
      return acc;
    },
    { cost: 0, net: 0, charges: 0, pnl: 0 }
  );
  const totalPnlPct = totals.cost > 0 ? (totals.pnl / totals.cost) * 100 : 0;
  const pnlClass = (v) => (v > 0 ? "diff-up" : v < 0 ? "diff-down" : "");

  return (
    <div className="portfolio-page">
      <Link to="/dashboard" className="toggle-link">
        &larr; Back to dashboard
      </Link>
      <h1>My Portfolio</h1>

      <div className="card summary-panel">
        <h2>{editingId ? "Edit holding" : "Add a holding"}</h2>
        <form onSubmit={handleSubmit}>
          <div className="explorer-controls">
            <input
              type="text"
              placeholder="Symbol (e.g. NABIL)"
              value={form.symbol}
              onChange={(e) => setForm({ ...form, symbol: e.target.value })}
              disabled={Boolean(editingId)}
              required
            />
            <input
              type="number"
              step="any"
              min="0"
              placeholder="Quantity"
              value={form.quantity}
              onChange={(e) => setForm({ ...form, quantity: e.target.value })}
              required
            />
            <input
              type="number"
              step="any"
              min="0"
              placeholder="Buy price / share (Rs.)"
              value={form.buy_price}
              onChange={(e) => setForm({ ...form, buy_price: e.target.value })}
              required
            />
            <input
              type="date"
              value={form.buy_date}
              onChange={(e) => setForm({ ...form, buy_date: e.target.value })}
              aria-label="Buy date"
            />
            <button type="submit" className="btn-primary">
              {editingId ? "Save changes" : "Add holding"}
            </button>
            {editingId && (
              <button type="button" onClick={resetForm}>
                Cancel
              </button>
            )}
          </div>
          {editingId && <p className="hint">Symbol can't be changed &mdash; delete and re-add to move to another symbol.</p>}
          {submitError && <p className="error">{submitError}</p>}
        </form>
      </div>

      {state.loading && (
        <div className="card">
          <LoadingSkeleton />
        </div>
      )}
      {state.error && <p className="error">{state.error}</p>}

      {!state.loading && !state.error && (
        <div className="card summary-panel">
          <h2>Holdings</h2>
          {holdings.length === 0 ? (
            <p className="hint">No holdings yet. Add one above to track its live profit/loss.</p>
          ) : (
            <div className="table-scroll">
              <table className="comparison-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Qty</th>
                    <th>Buy price/share</th>
                    <th>Latest close</th>
                    <th>Total cost (incl. fees)</th>
                    <th>Value if sold (net)</th>
                    <th>Charges + CGT</th>
                    <th>Net P&amp;L</th>
                    <th>Net P&amp;L %</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {holdings.map((h) => (
                    <tr key={h.id}>
                      <td>{h.symbol}</td>
                      <td>{fmt(h.quantity)}</td>
                      <td>{fmt(h.buy_price)}</td>
                      <td>{fmt(h.latest_close)}</td>
                      <td>{fmt(h.total_buy_cost)}</td>
                      <td>{fmt(h.net_sell_value)}</td>
                      <td title={h.sell_costs ? `Buy fees ${fmt(h.buy_costs.total)} + sell fees ${fmt(h.sell_costs.total - h.sell_costs.capital_gains_tax)} + CGT ${fmt(h.sell_costs.capital_gains_tax)} (${(h.sell_costs.cgt_rate * 100).toFixed(1)}%)` : undefined}>
                        {fmt(h.total_charges)}
                      </td>
                      <td className={pnlClass(h.net_pnl)}>{h.net_pnl === null ? "--" : fmt(h.net_pnl)}</td>
                      <td className={pnlClass(h.net_pnl_pct)}>{h.net_pnl_pct === null ? "--" : `${fmt(h.net_pnl_pct)}%`}</td>
                      <td>
                        <button type="button" onClick={() => startEdit(h)}>
                          Edit
                        </button>{" "}
                        <button type="button" onClick={() => handleDelete(h.id)}>
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="comparison-row-selected">
                    <td colSpan={4}>Total</td>
                    <td>{fmt(totals.cost)}</td>
                    <td>{fmt(totals.net)}</td>
                    <td>{fmt(totals.charges)}</td>
                    <td className={pnlClass(totals.pnl)}>{fmt(totals.pnl)}</td>
                    <td className={pnlClass(totals.pnl)}>{fmt(totalPnlPct)}%</td>
                    <td />
                  </tr>
                </tfoot>
              </table>
            </div>
          )}
          <p className="hint">
            Marked to the latest close in the dataset. Net figures apply real NEPSE charges on both sides &mdash;
            broker commission (slab-based), SEBON fee (0.015%), DP charge (Rs 25/script), and capital gains tax on
            profit (5% if held &ge; 365 days, else 7.5%). Hover a "Charges + CGT" cell for the breakdown. Prices in
            Nepalese Rupees.
          </p>
        </div>
      )}
    </div>
  );
}
