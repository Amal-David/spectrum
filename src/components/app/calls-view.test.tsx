import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it } from "vitest"

import { CallsView } from "@/components/app/calls-view"
import { calls } from "@/lib/mock-data"

describe("CallsView", () => {
  it("renders a simplified call list without the heavy filter surface", () => {
    render(<CallsView calls={calls} />)

    expect(screen.queryByText("Filters")).not.toBeInTheDocument()
    expect(screen.getAllByPlaceholderText("Search calls").length).toBeGreaterThan(0)
    expect(
      screen.getByRole("button", { name: "Upload files" })
    ).toBeInTheDocument()
    expect(screen.getByRole("columnheader", { name: "Call" })).toBeInTheDocument()
    expect(screen.getByRole("columnheader", { name: "State" })).toBeInTheDocument()
    expect(screen.getByRole("columnheader", { name: "Date" })).toBeInTheDocument()
    expect(screen.queryByRole("columnheader", { name: "Quality / trust" })).not.toBeInTheDocument()
    expect(screen.queryByRole("columnheader", { name: "Workflow" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Preview" })).not.toBeInTheDocument()
  })

  it("adds uploaded files to the top of the calls list as mock rows", async () => {
    const user = userEvent.setup()

    render(<CallsView calls={calls} />)

    const input = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement | null

    expect(input).not.toBeNull()

    await user.upload(
      input!,
      [
        new File(["one"], "first-call.wav", { type: "audio/wav" }),
        new File(["two"], "second-call.mp3", { type: "audio/mpeg" }),
      ]
    )

    const rows = screen.getAllByRole("row")

    expect(screen.getByText("8 calls")).toBeInTheDocument()
    expect(screen.getByText("first-call.wav")).toBeInTheDocument()
    expect(screen.getByText("second-call.mp3")).toBeInTheDocument()
    expect(rows[1]).toHaveTextContent("second-call.mp3")
    expect(rows[2]).toHaveTextContent("first-call.wav")
    expect(
      screen.getByRole("button", { name: "Analysis pending for second-call.mp3" })
    ).toBeDisabled()
  })

  it("filters the call list from the search box", async () => {
    const user = userEvent.setup()

    render(<CallsView calls={calls} />)

    const searchInput = screen.getAllByPlaceholderText("Search calls")[0]

    await user.type(searchInput, "Ahmedabad")

    await waitFor(() => {
      expect(
        screen.getAllByText("Ahmedabad renewal intent - insurance sales").length
      ).toBeGreaterThan(0)
      expect(screen.getByText("1 calls")).toBeInTheDocument()
    })
  })

  it("keeps a direct open action for each call", () => {
    render(<CallsView calls={calls} />)

    expect(
      screen.getAllByRole("button", {
        name: "Open Mumbai pricing objections - fintech sales analysis",
      })[0]
    ).toHaveAttribute(
      "href",
      "/analysis?callId=call-001"
    )
  })
})
