import { backendUrl } from "../../../../lib/backend";

export async function GET(_request: Request, context: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await context.params;
  const upstream = await fetch(backendUrl(`/api/v1/sessions/${jobId}/spectrogram`), { cache: "no-store" });
  if (!upstream.ok) {
    return new Response(await upstream.text(), { status: upstream.status });
  }

  return new Response(upstream.body, {
    status: upstream.status,
    headers: Object.fromEntries(
      [
        ["Content-Type", upstream.headers.get("content-type") ?? "image/png"],
        ["Content-Length", upstream.headers.get("content-length")],
      ].filter((entry): entry is [string, string] => Boolean(entry[1]))
    ),
  });
}
