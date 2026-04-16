import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it } from "vitest"

import { CallsView } from "@/components/app/calls-view"
import { calls } from "@/lib/mock-data"

describe("CallsView", () => {
  it("shows a grouped analysis action after selecting multiple calls", async () => {
    const user = userEvent.setup()

    render(<CallsView calls={calls} />)

    await user.click(
      screen.getByLabelText("Select Mumbai pricing objections - fintech sales")
    )
    await user.click(
      screen.getByLabelText("Select Kolkata repayment assurance - collections")
    )

    const action = screen.getByRole("button", { name: "Analyze selected" })

    expect(action).toHaveAttribute(
      "href",
      "/analysis?calls=call-001%2Ccall-005"
    )
  })
})
