import { backendUrl } from "../../../../../lib/backend";

export const runtime = "nodejs";

export async function POST(request: Request, context: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await context.params;
  const formData = await request.formData();
  const response = await fetch(backendUrl(`/api/v1/sessions/${jobId}/upload`), {
    method: "POST",
    body: formData
  });

  return new Response(await response.text(), {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("content-type") ?? "application/json"
    }
  });
}
