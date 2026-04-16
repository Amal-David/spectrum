import { describe, expect, it } from "vitest"

import { GET } from "@/app/api/sample-audio/[file]/route"

describe("sample audio route", () => {
  it("serves byte ranges for browser audio playback", async () => {
    const request = new Request("http://localhost:3000/api/sample-audio/sample-one.wav", {
      headers: {
        Range: "bytes=0-1023",
      },
    })

    const response = await GET(request, {
      params: Promise.resolve({ file: "sample-one.wav" }),
    })

    expect(response.status).toBe(206)
    expect(response.headers.get("accept-ranges")).toBe("bytes")
    expect(response.headers.get("content-range")).toMatch(/^bytes 0-1023\/\d+$/)
    expect(response.headers.get("content-length")).toBe("1024")
    expect(response.headers.get("content-type")).toBe("audio/wav")
  })
})
