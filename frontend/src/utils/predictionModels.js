export function resolveModels(data) {
  const xgboost = data.xgboost ?? (data.predictions ? data : null);
  const lstm = data.lstm ?? null;
  return { xgboost, lstm, hasBoth: Boolean(xgboost && lstm) };
}
