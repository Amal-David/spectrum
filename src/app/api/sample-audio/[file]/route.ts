import { readFile } from "node:fs/promises"
import path from "node:path"

import { NextResponse } from "next/server"

const sampleAudioDirectory = path.join(process.cwd(), "assets", "samples")

function parseRangeHeader(rangeHeader: string | null, fileSize: number) {
  if (!rangeHeader?.startsWith("bytes=")) {
    return null
  }

  const [rawStart, rawEnd] = rangeHeader.replace("bytes=", "").split("-")
  const start = Number(rawStart)
  const end = rawEnd ? Number(rawEnd) : Math.min(start + 1024 * 1024 - 1, fileSize - 1)

  if (!Number.isFinite(start) || !Number.isFinite(end) || start < 0 || end < start) {
    return null
  }

  return {
    start,
    end: Math.min(end, fileSize - 1),
  }
}

export async function GET(
  request: Request,
  context: { params: Promise<{ file: string }> }
) {
  const { file } = await context.params
  const safeFileName = path.basename(file)
  const filePath = path.join(sampleAudioDirectory, safeFileName)

  try {
    const audioBuffer = await readFile(filePath)
    const range = parseRangeHeader(request.headers.get("range"), audioBuffer.byteLength)

    if (range) {
      const chunk = audioBuffer.subarray(range.start, range.end + 1)

      return new NextResponse(chunk, {
        status: 206,
        headers: {
          "Accept-Ranges": "bytes",
          "Cache-Control": "public, max-age=3600",
          "Content-Length": String(chunk.byteLength),
          "Content-Range": `bytes ${range.start}-${range.end}/${audioBuffer.byteLength}`,
          "Content-Type": "audio/wav",
        },
      })
    }

    return new NextResponse(audioBuffer, {
      headers: {
        "Accept-Ranges": "bytes",
        "Cache-Control": "public, max-age=3600",
        "Content-Length": String(audioBuffer.byteLength),
        "Content-Type": "audio/wav",
      },
    })
  } catch {
    return NextResponse.json({ error: "Sample audio not found" }, { status: 404 })
  }
}
