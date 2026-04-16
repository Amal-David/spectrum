import { NextRequest, NextResponse } from "next/server";

import { backendUrl } from "../../../../../lib/backend";

export async function POST(request: NextRequest, { params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;
  const response = await fetch(backendUrl(`/api/v1/sessions/${jobId}/roles`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: await request.text(),
    cache: "no-store",
  });
  const payload = await response.text();
  return new NextResponse(payload, {
    status: response.status,
    headers: { "Content-Type": response.headers.get("content-type") ?? "application/json" },
  });
}
