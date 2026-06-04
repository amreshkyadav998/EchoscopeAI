"use client";

import axios, { AxiosError, AxiosRequestConfig } from "axios";
import { useAuth } from "@/store/auth";

const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export const api = axios.create({ baseURL: BASE });

// attach the access token
api.interceptors.request.use((config) => {
  const token = useAuth.getState().accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// auto-refresh on 401, then retry the original request once
let refreshing: Promise<string | null> | null = null;

async function refreshAccess(): Promise<string | null> {
  const { refreshToken, setAccess, logout } = useAuth.getState();
  if (!refreshToken) {
    logout();
    return null;
  }
  try {
    const resp = await axios.post(`${BASE}/api/v1/auth/refresh`, { refresh_token: refreshToken });
    const access = resp.data.access_token as string;
    setAccess(access);
    if (resp.data.refresh_token) {
      useAuth.getState().setTokens(access, resp.data.refresh_token);
    }
    return access;
  } catch {
    logout();
    return null;
  }
}

api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original = error.config as AxiosRequestConfig & { _retried?: boolean };
    if (error.response?.status === 401 && original && !original._retried) {
      original._retried = true;
      refreshing = refreshing || refreshAccess();
      const access = await refreshing;
      refreshing = null;
      if (access) {
        original.headers = { ...original.headers, Authorization: `Bearer ${access}` };
        return api(original);
      }
    }
    return Promise.reject(error);
  }
);
