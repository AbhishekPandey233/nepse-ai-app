import { useEffect, useState } from "react";

export function useTickerData(fetchFn, ticker) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    if (!ticker) return;
    let cancelled = false;

    setLoading(true);
    setError("");
    setData(null);

    fetchFn(ticker)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err) => {
        if (!cancelled) setError(err.response?.data?.detail || "Failed to load data.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [fetchFn, ticker, retryCount]);

  const retry = () => setRetryCount((n) => n + 1);

  return { data, loading, error, retry };
}
