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
import type { CallRecord } from "@/lib/types"

type CallsViewProps = {
  calls: CallRecord[]
}

export function CallsView({ calls }: CallsViewProps) {
  const [search, setSearch] = React.useState("")
  const [statusFilter, setStatusFilter] = React.useState<string>("all")
  const [selectedIds, setSelectedIds] = React.useState<string[]>([])
  const [previewCallId, setPreviewCallId] = React.useState<string | null>(null)
  const deferredSearch = React.useDeferredValue(search)

  const filteredCalls = calls.filter((call) => {
    const matchesSearch =
      call.title.toLowerCase().includes(deferredSearch.toLowerCase()) ||
      call.summary.toLowerCase().includes(deferredSearch.toLowerCase())
    const matchesStatus = statusFilter === "all" || call.status === statusFilter

    return matchesSearch && matchesStatus
  })

  const previewCall =
    calls.find((call) => call.id === previewCallId) ?? null

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
        header: "Call",
        cell: ({ row }) => (
          <div className="flex flex-col gap-1">
            <span className="font-medium">{row.original.title}</span>
            <span className="text-xs text-muted-foreground">{row.original.summary}</span>
          </div>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => (
          <Badge variant={row.original.status === "ready" ? "secondary" : "outline"}>
            {row.original.status}
          </Badge>
        ),
      },
      {
        accessorKey: "declaredLanguage",
        header: "Language",
      },
      {
        accessorKey: "speakerCount",
        header: "Speakers",
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
      <div className="flex flex-col gap-6 p-4 md:p-6">
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold">Calls library</h1>
          <p className="text-sm text-muted-foreground">
            Search calls, preview sessions, and build a grouped analysis from selected rows.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Filters</CardTitle>
            <CardDescription>Keep the UI close to the stock shadcn data-table pattern.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4 md:flex-row md:items-center">
            <div className="relative flex-1">
              <SearchIcon className="pointer-events-none absolute top-1/2 left-2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                className="pl-8"
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search calls"
                value={search}
              />
            </div>
            <Select
              onValueChange={(value) => setStatusFilter(value ?? "all")}
              value={statusFilter}
            >
              <SelectTrigger className="w-full md:w-44">
                <SelectValue />
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
                  Open a grouped analysis with the currently selected calls.
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
            <CardTitle>All calls</CardTitle>
            <CardDescription>{filteredCalls.length} rows match the current filters.</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
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

      <Sheet open={previewCall != null} onOpenChange={(open) => !open && setPreviewCallId(null)}>
        <SheetContent side="right">
          <SheetHeader>
            <SheetTitle>{previewCall?.title ?? "Call preview"}</SheetTitle>
            <SheetDescription>Frontend-only preview state backed by mock repositories.</SheetDescription>
          </SheetHeader>
          {previewCall ? (
            <div className="flex flex-col gap-4 p-4">
              <div className="flex gap-2">
                <Badge variant="secondary">{previewCall.status}</Badge>
                <Badge variant="outline">{previewCall.reviewState}</Badge>
              </div>
              <div className="grid gap-2 text-sm text-muted-foreground">
                <p>Language: {previewCall.declaredLanguage}</p>
                <p>Speakers: {previewCall.speakerCount}</p>
                <p>Region: {previewCall.region}</p>
                <p>Duration: {Math.round(previewCall.durationSeconds / 60)} min</p>
              </div>
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
