import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { AppHeader } from "@/components/app/app-header"

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
  }: {
    children: React.ReactNode
    href: string
  }) => <a href={href}>{children}</a>,
}))

vi.mock("next/navigation", () => ({
  usePathname: () => "/analysis",
  useSearchParams: () => new URLSearchParams("callId=call-001"),
}))

vi.mock("@/components/ui/sidebar", () => ({
  SidebarTrigger: () => <button type="button">Toggle sidebar</button>,
}))

describe("AppHeader", () => {
  it("uses the breadcrumb as the main header content without repeating the app title", () => {
    render(<AppHeader />)

    expect(screen.queryByText("Spectrum")).not.toBeInTheDocument()
    expect(screen.getByText("Dashboard")).toBeInTheDocument()
    expect(screen.getByText("Analysis")).toBeInTheDocument()
    expect(
      screen.getByText("Mumbai pricing objections - fintech sales")
    ).toBeInTheDocument()
  })
})
