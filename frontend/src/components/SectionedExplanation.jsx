import { useEffect, useState } from "react";

import {
  getHistory,
  getPrediction,
  getSectionedExplanation,
  getVolatility,
} from "../api/client.js";
import { themeColor } from "../theme.js";
import { buildPriceHistoryChartData } from "../utils/historyNarrative.js";
import ZoomableLine from "./ZoomableLine.jsx";

const MINI_OPTS = {
  responsive: true,
  maintainAspectRatio: false,
  animation: false,
  plugins: { legend: { display: false } },
  elements: { point: { radius: 0 }, line: { borderWidth: 1.5 } },
};

export default function SectionedExplanation({ ticker }) {
  const [sections, setSections] = useState({ loading: true, error: "", data: null });
  const [vol, setVol] = useState(null);
  const [hist, setHist] = useState(null);
  const [pred, setPred] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setSections({ loading: true, error: "", data: null });
    setVol(null);
    setHist(null);
    setPred(null);

    Promise.allSettled([getVolatility(ticker), getHistory(ticker), getPrediction(ticker)])
      .then(([v, h, p]) => {
        if (cancelled) return null;
        if (v.status === "fulfilled") setVol(v.value);
        if (h.status === "fulfilled") setHist(h.value);
        if (p.status === "fulfilled") setPred(p.value);
        return getSectionedExplanation(ticker);
      })
      .then((data) => {
        if (!cancelled && data) setSections({ loading: false, error: "", data });
      })
      .catch((err) => {
        if (cancelled) return;
        const message =
          err.response?.status === 404
            ? "Run an analysis for this ticker first."
            : err.response?.data?.detail || "Couldn't generate explanations.";
        setSections({ loading: false, error: message, data: null });
      });

    return () => {
      cancelled = true;
    };
  }, [ticker]);

  const riskChart = vol && {
    labels: vol.dates,
    datasets: [{ label: "Conditional volatility", data: vol.conditional_volatility, borderColor: themeColor("--chart-critical") }],
  };

  const trendChart =
    hist &&
    buildPriceHistoryChartData({ dates: hist.dates, close: hist.close }, hist.summary, {
      cyan: themeColor("--chart-cyan"),
      good: themeColor("--chart-good"),
      critical: themeColor("--chart-critical"),
    });

  const outlookChart = pred && {
    labels: pred.dates,
    datasets: [
      { label: "Actual", data: pred.actual, borderColor: themeColor("--chart-cyan") },
      { label: "Predicted", data: pred.predictions, borderColor: themeColor("--chart-violet") },
    ],
  };

  const cards = [
    { key: "risk_analysis", title: "Risk Analysis", chart: riskChart },
    { key: "historical_trends", title: "Historical Trends", chart: trendChart },
    { key: "future_outlook", title: "Future Outlook", chart: outlookChart },
  ];

  return (
    <>
      {cards.map(({ key, title, chart }) => {
        const sec = sections.data?.[key];
        return (
          <div className="card summary-panel" key={key}>
            <h2>{title}</h2>
            {chart && <ZoomableLine data={chart} options={MINI_OPTS} containerClassName="mini-chart" />}
            {sections.loading && <p className="hint">Generating explanation… (this can take a moment)</p>}
            {sections.error && <p className="error">{sections.error}</p>}
            {sec && (
              <>
                <ul className="summary-bullets">
                  {sec.key_points.map((point, i) => (
                    <li key={i}>{point}</li>
                  ))}
                </ul>
                <div className="summary-narrative">
                  <p>{sec.narrative}</p>
                </div>
              </>
            )}
          </div>
        );
      })}
    </>
  );
}
