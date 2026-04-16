import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { AnalysisWorkspace } from "@/components/app/analysis-workspace"
import { buildAnalysisDataset } from "@/lib/mock-data"

vi.mock("@/components/app/waveform-panel", () => ({
  WaveformPanel: () => <div data-testid="waveform-panel">Waveform panel</div>,
}))

vi.mock("@/components/app/emotion-graph", () => ({
  EmotionGraph: () => <div data-testid="emotion-graph">Emotion graph</div>,
}))

vi.mock("@/components/app/embedding-plot", () => ({
  EmbeddingPlot: () => <div data-testid="embedding-plot">Embedding plot</div>,
}))

describe("AnalysisWorkspace", () => {
  it("renders the waveform, emotion graph, and embedding plot", () => {
    const dataset = buildAnalysisDataset({
      kind: "single",
      callIds: ["call-001"],
      label: "Mumbai pricing objections - fintech sales",
    })

    render(<AnalysisWorkspace dataset={dataset} />)

    expect(screen.getByTestId("waveform-panel")).toBeInTheDocument()
    expect(screen.getByTestId("emotion-graph")).toBeInTheDocument()
    expect(screen.getByTestId("embedding-plot")).toBeInTheDocument()
    expect(screen.queryByText("Overview")).not.toBeInTheDocument()
    expect(screen.queryByText("Scope")).not.toBeInTheDocument()
    expect(screen.queryByText("Model runs")).not.toBeInTheDocument()
  })
})
