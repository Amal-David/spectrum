"use client"

import * as React from "react"
import Link from "next/link"
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table"
import { EyeIcon, SearchIcon } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { buildAnalysisHref } from "@/lib/analysis-scope"
import type { BusinessOutcome, CallRecord, QualityTier, TrustTier } from "@/lib/types"

type CallsViewProps = {
  calls: CallRecord[]
}

type FilterValue = "all" | string

function uniqueValues(values: string[]) {
  return Array.from(new Set(values)).sort((left, right) =>
    left.localeCompare(right)
  )
}

function badgeVariantForQuality(tier: QualityTier) {
  if (tier === "healthy") {
    return "secondary" as const
  }

  return "outline" as const
}

function badgeVariantForTrust(tier: TrustTier) {
  if (tier === "trusted") {
    return "secondary" as const
  }

  return "outline" as const
}

function badgeVariantForOutcome(outcome: BusinessOutcome) {
  if (outcome === "resolved" || outcome === "converted") {
    return "secondary" as const
  }

  return "outline" as const
}

export function CallsView({ calls }: CallsViewProps) {
  const [search, setSearch] = React.useState("")
  const [statusFilter, setStatusFilter] = React.useState<FilterValue>("all")
  const [stateFilter, setStateFilter] = React.useState<FilterValue>("all")
  const [languageFilter, setLanguageFilter] = React.useState<FilterValue>("all")
  const [regionFilter, setRegionFilter] = React.useState<FilterValue>("all")
  const [qualityFilter, setQualityFilter] = React.useState<FilterValue>("all")
  const [trustFilter, setTrustFilter] = React.useState<FilterValue>("all")
  const [outcomeFilter, setOutcomeFilter] = React.useState<FilterValue>("all")
  const [workflowFilter, setWorkflowFilter] = React.useState<FilterValue>("all")
  const [reviewFilter, setReviewFilter] = React.useState<FilterValue>("all")
  const [selectedIds, setSelectedIds] = React.useState<string[]>([])
  const [previewCallId, setPreviewCallId] = React.useState<string | null>(null)
  const deferredSearch = React.useDeferredValue(search)

  const states = React.useMemo(
    () => uniqueValues(calls.map((call) => call.state)),
    [calls]
  )
  const languages = React.useMemo(
    () => uniqueValues(calls.map((call) => call.language)),
    [calls]
  )
  const regions = React.useMemo(
    () => uniqueValues(calls.map((call) => call.region)),
    [calls]
  )
  const workflows = React.useMemo(
    () => uniqueValues(calls.map((call) => call.workflowLabel)),
    [calls]
  )

  const filteredCalls = React.useMemo(() => {
    const normalizedSearch = deferredSearch.trim().toLowerCase()

    return calls.filter((call) => {
      const matchesSearch =
        normalizedSearch.length === 0 ||
        call.title.toLowerCase().includes(normalizedSearch) ||
        call.summary.toLowerCase().includes(normalizedSearch) ||
        call.state.toLowerCase().includes(normalizedSearch) ||
        call.workflowLabel.toLowerCase().includes(normalizedSearch) ||
        call.agentLabel.toLowerCase().includes(normalizedSearch)

      const matchesStatus =
        statusFilter === "all" || call.status === statusFilter
      const matchesState =
        stateFilter === "all" || call.state === stateFilter
      const matchesLanguage =
        languageFilter === "all" || call.language === languageFilter
      const matchesRegion =
        regionFilter === "all" || call.region === regionFilter
      const matchesQuality =
        qualityFilter === "all" || call.qualityTier === qualityFilter
      const matchesTrust =
        trustFilter === "all" || call.trustTier === trustFilter
      const matchesOutcome =
        outcomeFilter === "all" || call.businessOutcome === outcomeFilter
      const matchesWorkflow =
        workflowFilter === "all" || call.workflowLabel === workflowFilter
      const matchesReview =
        reviewFilter === "all" || call.reviewState === reviewFilter

      return (
        matchesSearch &&
        matchesStatus &&
        matchesState &&
        matchesLanguage &&
        matchesRegion &&
        matchesQuality &&
        matchesTrust &&
        matchesOutcome &&
        matchesWorkflow &&
        matchesReview
      )
    })
  }, [
    calls,
    deferredSearch,
    languageFilter,
    outcomeFilter,
    qualityFilter,
    regionFilter,
    reviewFilter,
    stateFilter,
    statusFilter,
    trustFilter,
    workflowFilter,
  ])

  const previewCall = calls.find((call) => call.id === previewCallId) ?? null

  const toggleCallSelection = (callId: string) => {
    React.startTransition(() => {
      setSelectedIds((current) =>
        current.includes(callId)
          ? current.filter((id) => id !== callId)
          : [...current, callId]
      )
    })
  }

  const columns = React.useMemo<ColumnDef<CallRecord>[]>(
    () => [
      {
        id: "select",
        header: () => <span className="sr-only">Select</span>,
        cell: ({ row }) => (
          <input
            aria-label={`Select ${row.original.title}`}
            checked={selectedIds.includes(row.original.id)}
            onChange={() => toggleCallSelection(row.original.id)}
            type="checkbox"
          />
        ),
      },
      {
        accessorKey: "title",
        header: "Session",
        cell: ({ row }) => (
          <div className="flex flex-col gap-1">
            <span className="font-medium">{row.original.title}</span>
            <span className="text-xs text-muted-foreground">
              {row.original.summary}
            </span>
          </div>
        ),
      },
      {
        id: "geo",
        header: "Geography",
        cell: ({ row }) => (
          <div className="flex flex-col gap-1">
            <span>{row.original.state}</span>
            <span className="text-xs text-muted-foreground">
              {row.original.region} · {row.original.language}
            </span>
          </div>
        ),
      },
      {
        id: "quality",
        header: "Quality / trust",
        cell: ({ row }) => (
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap gap-2">
              <Badge variant={badgeVariantForQuality(row.original.qualityTier)}>
                {row.original.qualityTier}
              </Badge>
              <Badge variant={badgeVariantForTrust(row.original.trustTier)}>
                {row.original.trustTier}
              </Badge>
            </div>
            <span className="font-mono text-xs text-muted-foreground tabular-nums">
              {row.original.avgSnrDb.toFixed(1)} dB SNR
            </span>
          </div>
        ),
      },
      {
        id: "workflow",
        header: "Workflow",
        cell: ({ row }) => (
          <div className="flex flex-col gap-1">
            <span>{row.original.workflowLabel}</span>
            <span className="text-xs text-muted-foreground">
              {row.original.agentLabel}
            </span>
          </div>
        ),
      },
      {
        accessorKey: "businessOutcome",
        header: "Outcome",
        cell: ({ row }) => (
          <Badge variant={badgeVariantForOutcome(row.original.businessOutcome)}>
            {row.original.businessOutcome}
          </Badge>
        ),
      },
      {
        id: "friction",
        header: "Friction",
        cell: ({ row }) => (
          <span className="font-mono text-sm tabular-nums">
            {row.original.frictionScore}
          </span>
        ),
      },
      {
        id: "actions",
        header: "Actions",
        cell: ({ row }) => (
          <div className="flex items-center gap-2">
            <Button
              onClick={() => setPreviewCallId(row.original.id)}
              size="sm"
              variant="outline"
            >
              <EyeIcon data-icon="inline-start" />
              Preview
            </Button>
            <Button
              nativeButton={false}
              render={<Link href={buildAnalysisHref([row.original.id])} />}
              size="sm"
              variant="ghost"
            >
              Analyze
            </Button>
          </div>
        ),
      },
    ],
    [selectedIds]
  )

  // TanStack Table is intentional here; the React Compiler warning is expected for this hook.
  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data: filteredCalls,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <>
      <div className="flex min-w-0 flex-col gap-6 p-4 md:p-6">
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold text-balance">Calls catalog</h1>
          <p className="text-sm text-muted-foreground">
            Search operational sessions, filter by geography and trust, then open
            a single-call or grouped forensic analysis.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Filters</CardTitle>
            <CardDescription>
              Business, geography, and trust filters stay on the table surface so
              the page still feels like stock shadcn data-table UI.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="relative">
              <SearchIcon className="pointer-events-none absolute top-1/2 left-2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                className="pl-8"
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search calls, states, workflows, or summaries"
                value={search}
              />
            </div>

            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
              <Select
                onValueChange={(value) => setStatusFilter(value ?? "all")}
                value={statusFilter}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectLabel>Status</SelectLabel>
                    <SelectItem value="all">All</SelectItem>
                    <SelectItem value="ready">Ready</SelectItem>
                    <SelectItem value="processing">Processing</SelectItem>
                    <SelectItem value="failed">Failed</SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>

              <Select
                onValueChange={(value) => setStateFilter(value ?? "all")}
                value={stateFilter}
              >
                <SelectTrigger>
                  <SelectValue placeholder="State" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectLabel>State</SelectLabel>
                    <SelectItem value="all">All states</SelectItem>
                    {states.map((state) => (
                      <SelectItem key={state} value={state}>
                        {state}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>

              <Select
                onValueChange={(value) => setLanguageFilter(value ?? "all")}
                value={languageFilter}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Language" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectLabel>Language</SelectLabel>
                    <SelectItem value="all">All languages</SelectItem>
                    {languages.map((language) => (
                      <SelectItem key={language} value={language}>
                        {language}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>

              <Select
                onValueChange={(value) => setRegionFilter(value ?? "all")}
                value={regionFilter}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Region" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectLabel>Region</SelectLabel>
                    <SelectItem value="all">All regions</SelectItem>
                    {regions.map((region) => (
                      <SelectItem key={region} value={region}>
                        {region}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>

              <Select
                onValueChange={(value) => setWorkflowFilter(value ?? "all")}
                value={workflowFilter}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Workflow" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectLabel>Workflow</SelectLabel>
                    <SelectItem value="all">All workflows</SelectItem>
                    {workflows.map((workflow) => (
                      <SelectItem key={workflow} value={workflow}>
                        {workflow}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <Select
                onValueChange={(value) => setQualityFilter(value ?? "all")}
                value={qualityFilter}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Quality tier" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectLabel>Quality tier</SelectLabel>
                    <SelectItem value="all">All quality tiers</SelectItem>
                    <SelectItem value="healthy">Healthy</SelectItem>
                    <SelectItem value="watch">Watch</SelectItem>
                    <SelectItem value="risky">Risky</SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>

              <Select
                onValueChange={(value) => setTrustFilter(value ?? "all")}
                value={trustFilter}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Trust tier" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectLabel>Trust tier</SelectLabel>
                    <SelectItem value="all">All trust tiers</SelectItem>
                    <SelectItem value="trusted">Trusted</SelectItem>
                    <SelectItem value="discounted">Discounted</SelectItem>
                    <SelectItem value="review">Review</SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>

              <Select
                onValueChange={(value) => setOutcomeFilter(value ?? "all")}
                value={outcomeFilter}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Business outcome" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectLabel>Business outcome</SelectLabel>
                    <SelectItem value="all">All outcomes</SelectItem>
                    <SelectItem value="resolved">Resolved</SelectItem>
                    <SelectItem value="escalated">Escalated</SelectItem>
                    <SelectItem value="abandoned">Abandoned</SelectItem>
                    <SelectItem value="converted">Converted</SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>

              <Select
                onValueChange={(value) => setReviewFilter(value ?? "all")}
                value={reviewFilter}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Review state" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectLabel>Review state</SelectLabel>
                    <SelectItem value="all">All review states</SelectItem>
                    <SelectItem value="unreviewed">Unreviewed</SelectItem>
                    <SelectItem value="needs-review">Needs review</SelectItem>
                    <SelectItem value="reviewed">Reviewed</SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {selectedIds.length > 0 ? (
          <Card>
            <CardContent className="flex flex-col gap-3 pt-4 md:flex-row md:items-center md:justify-between">
              <div className="flex flex-col gap-1">
                <span className="text-sm font-medium">
                  {selectedIds.length} call{selectedIds.length > 1 ? "s" : ""} selected
                </span>
                <span className="text-sm text-muted-foreground">
                  Open a grouped analysis for the current operational slice.
                </span>
              </div>
              <Button
                nativeButton={false}
                render={<Link href={buildAnalysisHref(selectedIds)} />}
              >
                Analyze selected
              </Button>
            </CardContent>
          </Card>
        ) : null}

        <Card>
          <CardHeader>
            <CardTitle>All sessions</CardTitle>
            <CardDescription>
              {filteredCalls.length} rows match the current filters.
            </CardDescription>
          </CardHeader>
          <CardContent className="min-w-0 overflow-x-auto">
            <Table className="min-w-[1180px]">
              <TableHeader>
                {table.getHeaderGroups().map((headerGroup) => (
                  <TableRow key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <TableHead key={header.id}>
                        {header.isPlaceholder
                          ? null
                          : flexRender(
                              header.column.columnDef.header,
                              header.getContext()
                            )}
                      </TableHead>
                    ))}
                  </TableRow>
                ))}
              </TableHeader>
              <TableBody>
                {table.getRowModel().rows.map((row) => (
                  <TableRow key={row.id}>
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id}>
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      <Sheet
        open={previewCall != null}
        onOpenChange={(open) => !open && setPreviewCallId(null)}
      >
        <SheetContent side="right" className="overflow-y-auto">
          <SheetHeader>
            <SheetTitle>{previewCall?.title ?? "Call preview"}</SheetTitle>
            <SheetDescription>
              Business and explainability context for this session.
            </SheetDescription>
          </SheetHeader>

          {previewCall ? (
            <div className="flex flex-col gap-4 p-4">
              <div className="flex flex-wrap gap-2">
                <Badge variant="secondary">{previewCall.status}</Badge>
                <Badge variant={badgeVariantForOutcome(previewCall.businessOutcome)}>
                  {previewCall.businessOutcome}
                </Badge>
                <Badge variant={badgeVariantForQuality(previewCall.qualityTier)}>
                  {previewCall.qualityTier}
                </Badge>
                <Badge variant={badgeVariantForTrust(previewCall.trustTier)}>
                  {previewCall.trustTier}
                </Badge>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>Business summary</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-2 text-sm text-muted-foreground">
                  <p>Workflow: {previewCall.workflowLabel}</p>
                  <p>Agent: {previewCall.agentLabel}</p>
                  <p>Prompt version: {previewCall.promptVersion}</p>
                  <p>Outcome: {previewCall.businessOutcome}</p>
                  <p>Review state: {previewCall.reviewState}</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Demographic tags</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-2 text-sm text-muted-foreground">
                  <p>State: {previewCall.state}</p>
                  <p>District: {previewCall.district ?? "Not provided"}</p>
                  <p>Region: {previewCall.region}</p>
                  <p>Language: {previewCall.language}</p>
                  <p>Duration: {Math.round(previewCall.durationSeconds / 60)} min</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Quality summary</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-2 text-sm text-muted-foreground">
                  <p className="font-mono tabular-nums">
                    Avg SNR: {previewCall.avgSnrDb.toFixed(1)} dB
                  </p>
                  <p className="font-mono tabular-nums">
                    Quality score: {previewCall.qualityScore}
                  </p>
                  <p className="font-mono tabular-nums">
                    Trust score: {previewCall.trustScore}
                  </p>
                  <p className="font-mono tabular-nums">
                    Friction score: {previewCall.frictionScore}
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Top question issue</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  {previewCall.topQuestionIssue}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Explainability mask</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col gap-3">
                  <div className="flex flex-wrap gap-2">
                    {previewCall.environmentTags.map((tag) => (
                      <Badge key={tag} variant="outline">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                  <Separator />
                  <div className="flex flex-col gap-2">
                    {previewCall.explainabilityFlags.length > 0 ? (
                      previewCall.explainabilityFlags.map((flag) => (
                        <p key={flag} className="text-sm text-muted-foreground">
                          {flag}
                        </p>
                      ))
                    ) : (
                      <p className="text-sm text-muted-foreground">
                        No explainability discounts on this session.
                      </p>
                    )}
                  </div>
                </CardContent>
              </Card>

              <p className="text-sm">{previewCall.summary}</p>

              <Button
                nativeButton={false}
                render={<Link href={buildAnalysisHref([previewCall.id])} />}
              >
                Open analysis
              </Button>
            </div>
          ) : null}
        </SheetContent>
      </Sheet>
    </>
  )
}
