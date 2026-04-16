import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { EmotionGraph } from "@/components/app/emotion-graph"

vi.mock("@/components/app/echart", () => ({
  EChart: ({ option }: { option: { series?: Array<{ name?: string }> } }) => (
    <div data-testid="emotion-chart">{JSON.stringify(option.series?.map((item) => item.name))}</div>
  ),
}))

describe("EmotionGraph", () => {
  it("renders the emotion timeline chart", () => {
    render(
      <EmotionGraph
        durationSeconds={1272.64}
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

    expect(screen.getByText("Emotion graph")).toBeInTheDocument()
    expect(screen.getByTestId("emotion-chart")).toHaveTextContent("Calmness")
    expect(screen.getByTestId("emotion-chart")).toHaveTextContent("Frustration risk")
  })
})
