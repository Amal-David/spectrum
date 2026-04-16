import { describe, expect, it } from "vitest"

import { getAppShellState } from "@/lib/navigation"

describe("getAppShellState", () => {
  it("returns Spectrum branding for the dashboard", () => {
    const state = getAppShellState({
      pathname: "/",
      searchParams: new URLSearchParams(),
    })

    expect(state.appName).toBe("Spectrum")
    expect(state.breadcrumbs.map((item) => item.label)).toEqual(["Dashboard"])
  })

  it("returns the selected call as the last analysis breadcrumb", () => {
    const state = getAppShellState({
      pathname: "/analysis",
      searchParams: new URLSearchParams("callId=call-001"),
    })

    expect(state.breadcrumbs.map((item) => item.label)).toEqual([
      "Dashboard",
      "Analysis",
      "Mumbai pricing objections - fintech sales",
    ])
  })

  it("returns the saved group as the last grouped analysis breadcrumb", () => {
    const state = getAppShellState({
      pathname: "/analysis",
      searchParams: new URLSearchParams("groupId=group-001"),
    })

    expect(state.breadcrumbs.map((item) => item.label)).toEqual([
      "Dashboard",
      "Analysis",
      "Pricing friction cluster",
    ])
  })
})
