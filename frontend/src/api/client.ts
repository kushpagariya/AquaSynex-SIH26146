/**
 * Centralized API client for AquaSynex FastAPI backend.
 * Handles environment-based URL resolution, request/response lifecycle,
 * canonical envelope unwrapping, and structured error propagation.
 */

import type { ApiResponse } from "./types"

export class ApiErrorClass extends Error {
  status: number
  code: string
  details?: Record<string, unknown>

  constructor(status: number, code: string, message: string, details?: Record<string, unknown>) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.code = code
    this.details = details
  }
}

/**
 * Resolves the backend base URL.
 * Defaults to "/api" (which is reverse-proxied by Vite in dev) or uses VITE_API_BASE_URL.
 */
export function getApiBaseUrl(): string {
  const envUrl = import.meta.env.VITE_API_BASE_URL
  if (envUrl && typeof envUrl === "string") {
    return envUrl.replace(/\/+$/, "")
  }
  return "/api"
}

export function buildQuery(params?: Record<string, unknown>): string {
  if (!params) return ""
  const searchParams = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.append(key, String(value))
    }
  }
  const qs = searchParams.toString()
  return qs ? `?${qs}` : ""
}

/**
 * Performs an HTTP request against the AquaSynex backend and returns the full ApiResponse envelope.
 */
export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<ApiResponse<T>> {
  const baseUrl = getApiBaseUrl()
  const cleanPath = path.startsWith("/") ? path : `/${path}`
  // If baseUrl already ends with /api and path starts with /api, remove one prefix
  const url = baseUrl.endsWith("/api") && cleanPath.startsWith("/api/")
    ? `${baseUrl}${cleanPath.slice(4)}`
    : `${baseUrl}${cleanPath}`

  const headers = new Headers(options?.headers)
  if (!(options?.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }
  headers.set("Accept", "application/json")

  let response: Response
  try {
    response = await fetch(url, {
      ...options,
      headers,
    })
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Network error"
    throw new ApiErrorClass(
      0,
      "NETWORK_ERROR",
      `Unable to reach TraceGrid backend at ${baseUrl}. Ensure backend server is running. (${message})`,
    )
  }

  let body: ApiResponse<T>
  try {
    body = await response.json()
  } catch {
    throw new ApiErrorClass(
      response.status,
      "INVALID_JSON",
      `Backend returned unparseable response (HTTP ${response.status} ${response.statusText})`,
    )
  }

  if (!response.ok || !body.success) {
    const errObj = body.error
    throw new ApiErrorClass(
      response.status,
      errObj?.code || "API_ERROR",
      errObj?.message || `Request failed with HTTP ${response.status}`,
      errObj?.details,
    )
  }

  return body
}

/**
 * Convenience wrapper returning unwrapped data from ApiResponse.
 */
export async function apiData<T>(path: string, options?: RequestInit): Promise<T> {
  const envelope = await apiFetch<T>(path, options)
  return envelope.data as T
}
