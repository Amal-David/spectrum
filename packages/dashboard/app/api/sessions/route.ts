import { backendUrl } from "../../../lib/backend";

export const runtime = "nodejs";

export async function POST(request: Request) {
  const body = await request.text();
  const response = await fetch(backendUrl("/api/v1/sessions"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body
  });

  return new Response(await response.text(), {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("content-type") ?? "application/json"
    }
  });
}
