import axios from "axios";

const client = axios.create({
  baseURL: "http://localhost:8000",
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export async function login(email, password) {
  const { data } = await client.post("/api/login", { email, password });
  return data;
}

export async function register(email, password) {
  const { data } = await client.post("/api/register", { email, password });
  return data;
}

export async function getEfficiency(ticker) {
  const { data } = await client.get("/api/efficiency", { params: { ticker } });
  return data;
}

export async function getVolatility(ticker) {
  const { data } = await client.get("/api/volatility", { params: { ticker } });
  return data;
}

export async function getPrediction(ticker) {
  const { data } = await client.get("/api/predict", { params: { ticker } });
  return data;
}

export async function getExplanation(ticker) {
  const { data } = await client.get("/api/explain", { params: { ticker } });
  return data;
}

export async function getModelComparison(ticker) {
  const { data } = await client.get("/api/predict/compare", { params: { ticker } });
  return data;
}

export async function getMarketSummary() {
  const { data } = await client.get("/api/market-summary");
  return data;
}

export async function getSectionedExplanation(ticker) {
  const { data } = await client.get("/api/explain-chat/sections", { params: { ticker } });
  return data;
}

export async function getBacktest(ticker, transactionCost = 0.5) {
  const { data } = await client.get("/api/predict/backtest", {
    params: { ticker, transaction_cost: transactionCost },
  });
  return data;
}

export async function getRollingImpact(ticker, window = 60) {
  const { data } = await client.get("/api/predict/rolling-impact", { params: { ticker, window } });
  return data;
}

export async function getHistory(ticker) {
  const { data } = await client.get("/api/history", { params: { ticker } });
  return data;
}

export async function explainChat(ticker, question = null) {
  const { data } = await client.post("/api/explain-chat", { ticker, question });
  return data;
}

export async function getDetailedFactors(ticker) {
  const { data } = await client.get("/api/explain-chat/factors", { params: { ticker } });
  return data;
}

export async function getMe() {
  const { data } = await client.get("/api/me");
  return data;
}

export default client;
