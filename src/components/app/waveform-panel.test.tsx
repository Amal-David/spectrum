import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { WaveformPanel } from "@/components/app/waveform-panel"

describe("WaveformPanel", () => {
  it("renders only the waveform preview and audio player", () => {
    render(
      <WaveformPanel
        audioUrl="/api/sample-audio/sample-one.wav"
        waveformDurationSeconds={1272.64}
        waveformPeaks={[[0.1, -0.2, 0.3]]}
      />
    )

    expect(screen.getByText("Waveform")).toBeInTheDocument()
    expect(screen.getByTestId("waveform-fallback")).toBeInTheDocument()
    expect(screen.getByLabelText("Audio playback")).toBeInTheDocument()
    expect(screen.queryByText("Speaker turns")).not.toBeInTheDocument()
    expect(screen.queryByText("Pause windows")).not.toBeInTheDocument()
    expect(screen.queryByText("Interruptions / overlaps")).not.toBeInTheDocument()
  })

  it("shows the sample audio source in the player", () => {
    render(
      <WaveformPanel
        audioUrl="/api/sample-audio/sample-one.wav"
        waveformDurationSeconds={1272.64}
        waveformPeaks={[[0.1, -0.2, 0.3]]}
      />
    )

    expect(screen.getAllByLabelText("Audio playback")[0]).toHaveAttribute(
      "src",
      "/api/sample-audio/sample-one.wav"
    )
  })
})
