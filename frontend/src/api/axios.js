// TODO for api-client: add interceptors for auth, retries, and structured error normalization.
import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  timeout: 60000,
});

export default api;
