import { API_URL } from "@/lib/config";
import type { ApiErrorBody, TokenPair } from "./types";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string | undefined;
  readonly fields: Record<string, string[]>;

  constructor(status: number, body: ApiErrorBody) {
    super(body.detail ?? "Что-то пошло не так. Попробуйте ещё раз.");
    this.name = "ApiError";
    this.status = status;
    this.code = body.code;
    this.fields = body.fields ?? {};
  }
}

// Access-токен живёт только в памяти. Refresh лежит в httpOnly-cookie, которую ставит бэкенд,
// поэтому все запросы идут с credentials: "include".
let accessToken: string | null = null;
let refreshInFlight: Promise<boolean> | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken() {
  return accessToken;
}

export async function refreshAccessToken(): Promise<boolean> {
  refreshInFlight ??= (async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/auth/refresh/`, {
        method: "POST",
        credentials: "include",
        headers: { Accept: "application/json" },
      });
      if (!res.ok) {
        setAccessToken(null);
        return false;
      }
      const data = (await res.json()) as TokenPair;
      setAccessToken(data.access);
      return true;
    } catch {
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

type Query = Record<string, string | number | boolean | string[] | undefined | null>;

export function buildQuery(query: Query = {}): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === "" || value === false) continue;
    if (Array.isArray(value)) {
      if (value.length) params.set(key, value.join(","));
    } else {
      params.set(key, String(value));
    }
  }
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  query?: Query;
  auth?: boolean;
  /** Кэш Next.js для серверных запросов (ISR). */
  revalidate?: number;
  signal?: AbortSignal;
}

export async function request<T>(
  path: string,
  options: RequestOptions = {},
  retried = false,
): Promise<T> {
  const { method = "GET", body, query, auth = false, revalidate, signal } = options;
  const headers: Record<string, string> = { Accept: "application/json" };
  let payload: BodyInit | undefined;

  if (body instanceof FormData) {
    payload = body;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  if (auth && accessToken) headers.Authorization = `Bearer ${accessToken}`;

  const url = `${API_URL}/api/v1${path}${buildQuery(query)}`;
  const res = await fetch(url, {
    method,
    headers,
    body: payload,
    credentials: "include",
    signal,
    ...(revalidate !== undefined ? { next: { revalidate } } : {}),
  });

  // На 401 один раз обновляем access-токен и повторяем запрос уже с ним.
  if (res.status === 401 && auth && !retried && (await refreshAccessToken())) {
    return request<T>(path, options, true);
  }
  if (!res.ok) {
    let errorBody: ApiErrorBody = {};
    try {
      errorBody = (await res.json()) as ApiErrorBody;
    } catch {
      // тело не JSON (например, 502 от прокси) — оставляем сообщение по умолчанию
    }
    throw new ApiError(res.status, errorBody);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
