// Deterministic (no-LLM) prose built directly from history_summary.py's computed stats --
// always numerically accurate and instant, unlike routing this through the local LLM.

export function buildTrendSummary(ticker, summary) {
  const direction = summary.overall_return_pct >= 0 ? "risen" : "fallen";
  const absReturn = Math.abs(summary.overall_return_pct).toFixed(1);

  const bullets = [
    `${ticker} has ${direction} ${absReturn}% from ${summary.period_start} to ${summary.period_end}.`,
    `Highest close: ${summary.highest_close.price.toFixed(2)} on ${summary.highest_close.date}.`,
    `Lowest close: ${summary.lowest_close.price.toFixed(2)} on ${summary.lowest_close.date}.`,
    `Largest single-day gain: +${summary.top_gains[0].return_pct.toFixed(2)}% on ${summary.top_gains[0].date}.`,
    `Largest single-day loss: ${summary.top_losses[0].return_pct.toFixed(2)}% on ${summary.top_losses[0].date}.`,
  ];

  const otherGains = summary.top_gains
    .slice(1)
    .map((g) => `+${g.return_pct.toFixed(2)}% on ${g.date}`)
    .join(", ");
  const otherLosses = summary.top_losses
    .slice(1)
    .map((l) => `${l.return_pct.toFixed(2)}% on ${l.date}`)
    .join(", ");

  const paragraphs = [
    `Over the observed period (${summary.period_start} to ${summary.period_end}), ${ticker}'s price has ${direction} ` +
      `by ${absReturn}%, reaching a high of ${summary.highest_close.price.toFixed(2)} on ${summary.highest_close.date} ` +
      `and a low of ${summary.lowest_close.price.toFixed(2)} on ${summary.lowest_close.date}.`,
    `The largest single-day moves were a gain of +${summary.top_gains[0].return_pct.toFixed(2)}% on ${summary.top_gains[0].date}` +
      `${otherGains ? ` (other notable gains: ${otherGains})` : ""} and a loss of ${summary.top_losses[0].return_pct.toFixed(2)}% ` +
      `on ${summary.top_losses[0].date}${otherLosses ? ` (other notable losses: ${otherLosses})` : ""}. Sharp single-day swings ` +
      "like these often coincide with earnings releases, corporate actions, or broader market news.",
    summary.high_volatility_periods.length > 0
      ? `The stock went through ${summary.high_volatility_periods.length} period(s) of unusually high volatility (above its ` +
        `own 80th percentile), including ${summary.high_volatility_periods
          .slice(0, 3)
          .map((p) => `${p.start} to ${p.end}`)
          .join(", ")}${summary.high_volatility_periods.length > 3 ? ", among others" : ""}.`
      : "The stock has not shown any periods of unusually high volatility (above its own 80th percentile) in this dataset.",
  ];

  return { bullets, paragraphs };
}

export function buildVolatilityExplanation(ticker, { currentValue, topPercent, threshold, params, highVolatilityPeriods }) {
  const alpha = params["alpha[1]"];
  const beta = params["beta[1]"];
  const persistence = alpha + beta;

  const persistenceLevel =
    persistence > 0.9 ? "very high" : persistence > 0.7 ? "high" : persistence > 0.4 ? "moderate" : "low";
  const reactsStrongly = alpha > 0.15;

  const recentPeriods = highVolatilityPeriods.slice(-3).map((p) => `${p.start} to ${p.end}`);

  const bullets = [
    `Current conditional (GARCH-fitted) volatility is ${currentValue.toFixed(5)}, in the top ` +
      `${topPercent <= 0 ? "of its" : `${topPercent}% of its`} own historical range.`,
    `Volatility persistence (alpha + beta = ${persistence.toFixed(2)}) is ${persistenceLevel}: once volatility rises, ` +
      `it tends to ${persistenceLevel === "very high" || persistenceLevel === "high" ? "stay elevated for a while" : "fade relatively quickly"}.`,
    `The stock ${reactsStrongly ? "reacts strongly" : "reacts only mildly"} to fresh shocks (alpha = ${alpha.toFixed(2)}): ` +
      `${reactsStrongly ? "a single large price move can spike volatility quickly" : "single-day moves have a fairly muted effect on near-term volatility"}.`,
    highVolatilityPeriods.length > 0
      ? `This stock has been through ${highVolatilityPeriods.length} similar high-volatility period(s) before, most ` +
        `recently ${highVolatilityPeriods[highVolatilityPeriods.length - 1].start} to ` +
        `${highVolatilityPeriods[highVolatilityPeriods.length - 1].end}.`
      : "This is the first time in the observed history that volatility has approached this level.",
  ];

  const paragraphs = [
    `${ticker} currently sits ${topPercent <= 0 ? "at the highest point" : `in the top ${topPercent}%`} of its own ` +
      `historical volatility range, with a fitted conditional volatility of ${currentValue.toFixed(5)} against a ` +
      `historical 80th-percentile threshold of ${threshold.toFixed(5)}.`,
    `The fitted GARCH(1,1) model gives alpha = ${alpha.toFixed(2)} and beta = ${beta.toFixed(2)} (combined persistence ` +
      `${persistence.toFixed(2)}). In plain terms: volatility here is ` +
      `${persistenceLevel === "very high" || persistenceLevel === "high" ? "sticky -- once it rises, it typically takes a while to settle back down" : "relatively short-lived -- spikes tend to fade quickly"}, ` +
      `and the stock ${reactsStrongly ? "reacts strongly" : "reacts only mildly"} to fresh news or large single-day price moves.`,
    highVolatilityPeriods.length > 0
      ? `Looking at this stock's own history, similar elevated-volatility patterns have occurred ` +
        `${highVolatilityPeriods.length} time(s) before, including ${recentPeriods.join(", ")}. This suggests the ` +
        "current conditions, while notable, are not unprecedented for this stock."
      : "There is no earlier period in this dataset with comparably high volatility, which makes the current level " +
        "unusual for this stock specifically.",
  ];

  return { bullets, paragraphs };
}

export function buildPriceHistoryChartData(history, summary, colors) {
  const { dates, close } = history;

  const gainDates = new Set(summary.top_gains.map((g) => g.date));
  const lossDates = new Set(summary.top_losses.map((l) => l.date));

  const pointColors = dates.map((d) => {
    if (d === summary.highest_close.date || gainDates.has(d)) return colors.good;
    if (d === summary.lowest_close.date || lossDates.has(d)) return colors.critical;
    return "transparent";
  });
  const pointRadii = dates.map((d) =>
    d === summary.highest_close.date || d === summary.lowest_close.date || gainDates.has(d) || lossDates.has(d) ? 5 : 0
  );

  return {
    labels: dates,
    datasets: [
      {
        label: "Close price",
        data: close,
        borderColor: colors.cyan,
        pointBackgroundColor: pointColors,
        pointRadius: pointRadii,
        pointHoverRadius: 6,
      },
    ],
  };
}
