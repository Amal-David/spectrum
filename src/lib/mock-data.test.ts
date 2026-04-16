import { describe, expect, it } from "vitest"

import { calls } from "@/lib/mock-data"

describe("mock audio sources", () => {
  it("uses the real sample audio for one analysis call", () => {
    const sampleCall = calls.find((call) => call.id === "call-001")

    expect(sampleCall?.audioUrl).toBe("/api/sample-audio/sample-one.wav")
    expect(sampleCall?.audioAsset.originalUrl).toBe(
      "/api/sample-audio/sample-one.wav"
    )
  })
})
