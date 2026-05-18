import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  timeout: 30000,
});

export const getExchangeRate = () => api.get("/exchange-rate").then((r) => r.data);

export const getProducts = (params = {}) =>
  api.get("/products", { params }).then((r) => r.data);

export const refreshProducts = () => api.post("/products/refresh").then((r) => r.data);

export const getProductAnalysis = (id) =>
  api.get(`/products/${id}/analysis`).then((r) => r.data);

export const getComparisons = (params = {}) =>
  api.get("/compare", { params }).then((r) => r.data);

export const getEVAnalysis = (params = {}) =>
  api.get("/ev", { params }).then((r) => r.data);

export const getKnownSetsEV = () =>
  api.get("/ev/sets").then((r) => r.data);

export const getDashboard = () => api.get("/dashboard").then((r) => r.data);

export const getProductTrend = (name) =>
  api.get(`/trends/${encodeURIComponent(name)}`).then((r) => r.data);

export default api;
