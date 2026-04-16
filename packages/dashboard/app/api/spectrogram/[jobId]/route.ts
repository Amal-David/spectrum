import fs from "node:fs";
import path from "node:path";

export async function GET(_request: Request, context: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await context.params;
  const repoRoot = path.resolve(process.cwd(), "../..");
  const bundlePath = path.join(repoRoot, "runs", jobId, "bundle.json");
  const bundle = fs.existsSync(bundlePath) ? JSON.parse(fs.readFileSync(bundlePath, "utf8")) : null;
  const imagePath =
    bundle?.spectrogram?.image_path ??
    bundle?.artifacts?.spectrogram_path ??
    path.join(repoRoot, "runs", jobId, "spectrogram", "audio.png");

  if (!imagePath || !fs.existsSync(imagePath)) {
    return new Response("Not found", { status: 404 });
  }

  const buffer = fs.readFileSync(imagePath);
  return new Response(buffer, {
    headers: {
      "Content-Type": "image/png",
      "Content-Length": `${buffer.length}`,
    },
  });
}
