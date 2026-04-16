import { callGroups, calls } from "@/lib/mock-data"

type AppShellStateInput = {
  pathname: string
  searchParams: URLSearchParams
}

type AppShellBreadcrumb = {
  href?: string
  label: string
}

type AppShellState = {
  appName: string
  appSubtitle: string
  breadcrumbs: AppShellBreadcrumb[]
}

function getAnalysisLabel(searchParams: URLSearchParams) {
  const groupId = searchParams.get("groupId")

  if (groupId) {
    return callGroups.find((group) => group.id === groupId)?.name
  }

  const callId = searchParams.get("callId")

  if (callId) {
    return calls.find((call) => call.id === callId)?.title
  }

  const selectedCalls = searchParams.get("calls")

  if (selectedCalls) {
    const callIds = selectedCalls.split(",").map((item) => item.trim())
    const matchingGroup = callGroups.find(
      (group) =>
        group.callIds.length === callIds.length &&
        group.callIds.every((id) => callIds.includes(id))
    )

    if (matchingGroup) {
      return matchingGroup.name
    }

    if (callIds.length === 1) {
      return calls.find((call) => call.id === callIds[0])?.title
    }

    return `${callIds.length} selected calls`
  }

  return undefined
}

export function getAppShellState({
  pathname,
  searchParams,
}: AppShellStateInput): AppShellState {
  const appName = "Spectrum"
  const appSubtitle = "Voice agent analytics"

  if (pathname === "/calls") {
    return {
      appName,
      appSubtitle,
      breadcrumbs: [
        { href: "/", label: "Dashboard" },
        { label: "Calls" },
      ],
    }
  }

  if (pathname === "/analysis") {
    const analysisLabel = getAnalysisLabel(searchParams)

    return {
      appName,
      appSubtitle,
      breadcrumbs: analysisLabel
        ? [
            { href: "/", label: "Dashboard" },
            { href: "/analysis", label: "Analysis" },
            { label: analysisLabel },
          ]
        : [{ href: "/", label: "Dashboard" }, { label: "Analysis" }],
    }
  }

  return {
    appName,
    appSubtitle,
    breadcrumbs: [{ label: "Dashboard" }],
  }
}

export type { AppShellBreadcrumb, AppShellState }
