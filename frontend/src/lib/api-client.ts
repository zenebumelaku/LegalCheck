/**
 * Centralized API Client for LegalCheck Ethiopia.
 * The app defaults to the real FastAPI backend; demo/offline behaviour is
 * opt-in via explicit environment flags rather than silent fallback.
 */

const API_BASE_URL =
  (typeof process !== 'undefined' && process.env?.NEXT_PUBLIC_API_BASE_URL) ||
  (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) ||
  '';

export function isDemoFallbackEnabled(): boolean {
  const envFlag =
    (typeof process !== 'undefined' && process.env?.NEXT_PUBLIC_ENABLE_DEMO_FALLBACK) ||
    (typeof import.meta !== 'undefined' && import.meta.env?.VITE_ENABLE_DEMO_FALLBACK) ||
    (typeof window !== 'undefined' && window.localStorage.getItem('lc_demo_fallback')) ||
    '';

  return envFlag === '1' || envFlag === 'true' || envFlag === 'yes';
}

export interface ApiRequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
}

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export async function apiRequest<T>(endpoint: string, options: ApiRequestOptions = {}): Promise<T> {
  const { params, headers, ...customConfig } = options;

  let url = `${API_BASE_URL}${endpoint}`;
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined) searchParams.append(key, String(val));
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += (url.includes('?') ? '&' : '?') + queryString;
    }
  }

  // Retrieve auth token if present
  let authHeader: Record<string, string> = {};
  if (typeof window !== 'undefined') {
    const sessionToken = sessionStorage.getItem('lc_auth_token');
    if (sessionToken) {
      authHeader = { Authorization: `Bearer ${sessionToken}` };
    }
  }

  const isMultipart = typeof FormData !== 'undefined' && customConfig.body instanceof FormData;
  const defaultHeaders: HeadersInit = {
    ...(isMultipart ? {} : { 'Content-Type': 'application/json' }),
    Accept: 'application/json',
    ...authHeader,
    ...headers,
  };

  try {
    const response = await fetch(url, {
      credentials: 'same-origin', // adheres to secure cookie / session guidelines
      headers: defaultHeaders,
      ...customConfig,
    });

    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch {
        errorData = { message: response.statusText };
      }
      throw new ApiError(
        errorData?.detail ||
          errorData?.error?.message ||
          errorData?.message ||
          `HTTP ${response.status}`,
        response.status,
        errorData
      );
    }

    if (response.status === 204) {
      return {} as T;
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      error instanceof Error ? error.message : 'Network request failed',
      0
    );
  }
}
