import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://localhost:8000/api/v1',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Always attach the current JWT from localStorage
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    } else {
      // Ensure no stale Authorization header lingers
      delete config.headers.Authorization;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: On 401, clear the stale JWT and force re-login
// This prevents the scenario where an expired JWT silently falls through
// to a session cookie belonging to a DIFFERENT user (role collision).
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear the expired/invalid JWT so it can't pollute future requests
      localStorage.removeItem('token');
      // Notify AuthContext to reset auth state and redirect to login
      window.dispatchEvent(new Event('auth:unauthorized'));
    }
    return Promise.reject(error);
  }
);

export default api;
