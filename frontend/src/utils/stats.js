export function quantile(sortedValues, q) {
  const pos = (sortedValues.length - 1) * q;
  const base = Math.floor(pos);
  const rest = pos - base;
  if (sortedValues[base + 1] !== undefined) {
    return sortedValues[base] + rest * (sortedValues[base + 1] - sortedValues[base]);
  }
  return sortedValues[base];
}

// % of `values` that are <= `value` -- e.g. 92 means value is higher than 92% of history
export function percentileRank(value, values) {
  const belowOrEqual = values.filter((v) => v <= value).length;
  return (belowOrEqual / values.length) * 100;
}
