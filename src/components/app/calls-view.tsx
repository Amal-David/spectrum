"use client"

import * as React from "react"
import Link from "next/link"
import { SearchIcon, UploadIcon } from "lucide-react"

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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { demoAudioUrl } from "@/lib/mock-data"
import { buildAnalysisHref } from "@/lib/analysis-scope"
import type { CallRecord } from "@/lib/types"

type CallsViewProps = {
  calls: CallRecord[]
}

const dateFormatter = new Intl.DateTimeFormat("en", {
  month: "short",
  day: "numeric",
  year: "numeric",
})

function formatCallDate(value: string) {
  return dateFormatter.format(new Date(value))
}

function buildUploadedMockCall(file: File, index: number): CallRecord {
  const uploadedAt = new Date(Date.now() + index).toISOString()

  return {
    id:
      typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : `uploaded-${Date.now()}-${index}`,
    title: file.name,
    source: "upload",
    status: "ready",
    sessionType: "support",
    language: "Unknown",
    declaredLanguage: "Unknown",
    state: "Unknown",
    stateCode: "NA",
    region: "Unknown",
    speakerCount: 0,
    durationSeconds: 0,
    uploadedAt,
    reviewState: "unreviewed",
    summary: "Uploaded file awaiting analysis.",
    audioUrl: demoAudioUrl,
    audioAsset: {
      originalUrl: demoAudioUrl,
      normalizedUrl: demoAudioUrl,
      telephonyUrl: demoAudioUrl,
    },
    qualityTier: "watch",
    trustTier: "review",
    businessOutcome: "abandoned",
    workflowId: "wf-upload-pending",
    workflowLabel: "Upload Queue",
    agentLabel: "Pending",
    promptVersion: "pending",
    qualityScore: 0,
    trustScore: 0,
    frictionScore: 0,
    avgSnrDb: 0,
    explainabilityFlags: [],
    environmentTags: [],
    topQuestionIssue: "Analysis pending",
  }
}

export function CallsView({ calls }: CallsViewProps) {
  const [search, setSearch] = React.useState("")
  const [uploadedCalls, setUploadedCalls] = React.useState<CallRecord[]>([])
  const deferredSearch = React.useDeferredValue(search)
  const fileInputRef = React.useRef<HTMLInputElement | null>(null)

  const allCalls = React.useMemo(
    () => [...uploadedCalls, ...calls],
    [uploadedCalls, calls]
  )

  const filteredCalls = React.useMemo(() => {
    const normalizedSearch = deferredSearch.trim().toLowerCase()

    return allCalls.filter((call) => {
      if (normalizedSearch.length === 0) {
        return true
      }

      return (
        call.title.toLowerCase().includes(normalizedSearch) ||
        call.summary.toLowerCase().includes(normalizedSearch) ||
        call.state.toLowerCase().includes(normalizedSearch)
      )
    })
  }, [allCalls, deferredSearch])

  function handleFileSelection(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? [])

    if (files.length === 0) {
      return
    }

    const mockCalls = files.map((file, index) => buildUploadedMockCall(file, index))

    setUploadedCalls((current) => [...mockCalls.reverse(), ...current])
    event.target.value = ""
  }

  return (
    <div className="flex min-w-0 flex-col gap-6 p-4 md:p-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold text-balance">Calls catalog</h1>
        <p className="text-sm text-muted-foreground">
          A simple list of calls. Search, scan, and open a call analysis.
        </p>
      </div>

      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="relative max-w-md flex-1">
          <SearchIcon className="pointer-events-none absolute top-1/2 left-2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-8"
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search calls"
            value={search}
          />
        </div>

        <input
          ref={fileInputRef}
          className="hidden"
          multiple
          onChange={handleFileSelection}
          type="file"
        />
        <Button
          onClick={() => fileInputRef.current?.click()}
          size="sm"
          variant="outline"
        >
          <UploadIcon data-icon="inline-start" />
          Upload files
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All calls</CardTitle>
          <CardDescription>{filteredCalls.length} calls</CardDescription>
        </CardHeader>
        <CardContent className="min-w-0 overflow-x-auto">
          <Table className="min-w-[720px]">
            <TableHeader>
              <TableRow>
                <TableHead>Call</TableHead>
                <TableHead>State</TableHead>
                <TableHead>Date</TableHead>
                <TableHead className="w-[120px]">Open</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredCalls.map((call) => (
                <TableRow key={call.id}>
                  <TableCell className="whitespace-normal">
                    <div className="flex flex-col gap-1">
                      <span className="font-medium">{call.title}</span>
                      <span className="text-xs text-muted-foreground">
                        {call.summary}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>{call.state}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatCallDate(call.uploadedAt)}
                  </TableCell>
                  <TableCell>
                    {call.source === "upload" ? (
                      <Button
                        aria-label={`Analysis pending for ${call.title}`}
                        disabled
                        size="sm"
                        variant="outline"
                      >
                        Pending
                      </Button>
                    ) : (
                      <Button
                        nativeButton={false}
                        render={
                          <Link
                            aria-label={`Open ${call.title} analysis`}
                            href={buildAnalysisHref([call.id])}
                          />
                        }
                        size="sm"
                        variant="outline"
                      >
                        Open
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
