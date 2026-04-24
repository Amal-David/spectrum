import { normalizeSessionBundle, type SessionBundle } from "./data";

export function mapSessionBundle(payload: unknown): SessionBundle {
  return normalizeSessionBundle(payload);
}

export function mapSessionBundles(payloads: unknown[]): SessionBundle[] {
  return payloads.map((payload) => mapSessionBundle(payload));
}
