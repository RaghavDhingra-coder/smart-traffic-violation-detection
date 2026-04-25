// TODO for api-client: add interceptors for auth, retries, and structured error normalization.
import axios from "axios";

const defaultBaseUrl = import.meta.env.DEV ? "http://127.0.0.1:8000" : "/api";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || defaultBaseUrl,
  timeout: 60000,
});

export default api;
