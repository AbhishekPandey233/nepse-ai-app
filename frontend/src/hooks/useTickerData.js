import { useEffect, useState } from "react";

export function useTickerData(fetchFn, ticker) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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
  }, [fetchFn, ticker]);

  return { data, loading, error };
}
