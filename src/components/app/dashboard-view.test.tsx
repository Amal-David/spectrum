import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { DashboardView } from "@/components/app/dashboard-view"

vi.mock("@/components/app/echart", () => ({
  EChart: () => <div data-testid="echart" />,
}))

vi.mock("@/components/ui/chart", () => ({
  ChartContainer: ({ children }: { children?: React.ReactNode }) => (
    <div>{children}</div>
  ),
  ChartTooltip: ({ children }: { children?: React.ReactNode }) => (
    <div>{children}</div>
  ),
  ChartTooltipContent: () => <div />,
}))

vi.mock("recharts", () => {
  const MockComponent = ({ children }: { children?: React.ReactNode }) => (
    <div>{children}</div>
  )

  return {
    Area: MockComponent,
    AreaChart: MockComponent,
    Bar: MockComponent,
    BarChart: MockComponent,
    CartesianGrid: MockComponent,
    Cell: MockComponent,
    Line: MockComponent,
    LineChart: MockComponent,
    Scatter: MockComponent,
    ScatterChart: MockComponent,
    XAxis: MockComponent,
    YAxis: MockComponent,
    ResponsiveContainer: MockComponent,
    Tooltip: MockComponent,
  }
})

describe("DashboardView", () => {
  it("does not render the dashboard intro hero block", () => {
    render(<DashboardView />)

    expect(screen.queryByText("Business dashboard")).not.toBeInTheDocument()
    expect(
      screen.queryByText("Google Analytics for voice AI agents")
    ).not.toBeInTheDocument()
    expect(
      screen.queryByText(/Track business outcomes, India-first demographic/)
    ).not.toBeInTheDocument()
  })
})
