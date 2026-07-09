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

export default client;
