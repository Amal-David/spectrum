import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { EmbeddingPlot } from "@/components/app/embedding-plot"

vi.mock("@/components/app/echart", () => ({
  EChart: ({ option }: { option: { series?: Array<{ name?: string }> } }) => (
    <div data-testid="embedding-chart">{JSON.stringify(option.series?.map((item) => item.name))}</div>
  ),
}))

describe("EmbeddingPlot", () => {
  it("renders the embedding plot card", () => {
    render(
      <EmbeddingPlot
        signals={[
          {
            id: "e1",
            label: "Calmness",
            state: "computed",
            score: 0.58,
            confidence: "medium",
            experimental: true,
          },
          {
            id: "e2",
            label: "Frustration risk",
            state: "computed",
            score: 0.42,
            confidence: "medium",
            experimental: true,
          },
        ]}
      />
    )

    expect(screen.getByText("Embedding plot")).toBeInTheDocument()
    expect(screen.getByTestId("embedding-chart")).toHaveTextContent("Emotion space")
  })
})
