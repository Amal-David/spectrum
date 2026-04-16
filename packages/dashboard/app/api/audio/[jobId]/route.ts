import fs from "node:fs";
import path from "node:path";

export async function GET(_request: Request, context: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await context.params;
  const repoRoot = path.resolve(process.cwd(), "../..");
  const bundlePath = path.join(repoRoot, "runs", jobId, "bundle.json");
  const bundle = fs.existsSync(bundlePath) ? JSON.parse(fs.readFileSync(bundlePath, "utf8")) : null;
  const audioPath =
    bundle?.artifacts?.normalized_audio_path ??
    bundle?.artifacts?.original_audio_path ??
    path.join(repoRoot, "runs", jobId, "normalized", "audio.wav");

  if (!fs.existsSync(audioPath)) {
    return new Response("Not found", { status: 404 });
  }

  const buffer = fs.readFileSync(audioPath);
  return new Response(buffer, {
    headers: {
      "Content-Type": audioPath.endsWith(".mp3") ? "audio/mpeg" : "audio/wav",
      "Content-Length": `${buffer.length}`
    }
  });
}
