const DEFAULT_BACKEND_BASE_URL = "http://127.0.0.1:8000";

export function backendBaseUrl() {
  return process.env.SPECTRUM_API_BASE_URL ?? process.env.NEXT_PUBLIC_SPECTRUM_API_BASE_URL ?? DEFAULT_BACKEND_BASE_URL;
}

export function backendUrl(pathname: string) {
  return new URL(pathname, backendBaseUrl()).toString();
}
