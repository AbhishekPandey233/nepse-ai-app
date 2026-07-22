export function quantile(sortedValues, q) {
  const pos = (sortedValues.length - 1) * q;
  const base = Math.floor(pos);
  const rest = pos - base;
  if (sortedValues[base + 1] !== undefined) {
    return sortedValues[base] + rest * (sortedValues[base + 1] - sortedValues[base]);
  }
  return sortedValues[base];
}

export function percentileRank(value, values) {
  const belowOrEqual = values.filter((v) => v <= value).length;
  return (belowOrEqual / values.length) * 100;
}

export function contiguousRanges(dates, mask) {
  const ranges = [];
  let start = null;
  for (let i = 0; i < mask.length; i++) {
    if (mask[i] && start === null) {
      start = i;
    } else if (!mask[i] && start !== null) {
      ranges.push({ start: dates[start], end: dates[i - 1] });
      start = null;
    }
  }
  if (start !== null) {
    ranges.push({ start: dates[start], end: dates[mask.length - 1] });
  }
  return ranges;
}
