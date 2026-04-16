"use client"

import * as React from "react"
import {
  AlertTriangleIcon,
  FileJsonIcon,
  ListChecksIcon,
  SparklesIcon,
} from "lucide-react"

import { WaveformPanel } from "@/components/app/waveform-panel"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import type {
  AnalysisDataset,
  BusinessOutcome,
  MetricCard,
  QualityTier,
  TrustTier,
} from "@/lib/types"

type AnalysisWorkspaceProps = {
  dataset: AnalysisDataset
}

function badgeVariantForTrust(tier: TrustTier) {
  if (tier === "trusted") {
    return "secondary" as const
  }

  return "outline" as const
}

function badgeVariantForQuality(tier: QualityTier) {
  if (tier === "healthy") {
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

function MetricGrid({
  description,
  items,
  title,
}: {
  description?: string
  items: MetricCard[]
  title: string
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {items.map((metric) => (
          <div key={metric.id} className="rounded-lg border p-3">
            <div className="flex items-start justify-between gap-2">
              <div className="flex flex-col gap-1">
                <span className="text-sm text-muted-foreground">{metric.label}</span>
                <span className="font-mono text-lg tabular-nums">{metric.value}</span>
              </div>
              {metric.confidence ? (
                <Badge variant="outline">{metric.confidence}</Badge>
              ) : null}
            </div>
            {(metric.delta || metric.experimental) ? (
              <div className="mt-2 flex flex-wrap gap-2">
                {metric.delta ? (
                  <Badge variant="outline" className="font-mono tabular-nums">
                    {metric.delta}
                  </Badge>
                ) : null}
                {metric.experimental ? (
                  <Badge variant="outline">experimental</Badge>
                ) : null}
              </div>
            ) : null}
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

export function AnalysisWorkspace({ dataset }: AnalysisWorkspaceProps) {
  const states = Array.from(new Set(dataset.calls.map((call) => call.state)))
  const languages = Array.from(new Set(dataset.calls.map((call) => call.language)))
  const workflows = Array.from(
    new Set(dataset.calls.map((call) => call.workflowLabel))
  )
  const outcomes = Array.from(
    new Set(dataset.calls.map((call) => call.businessOutcome))
  )
  const qualityTiers = Array.from(
    new Set(dataset.calls.map((call) => call.qualityTier))
  )
  const trustTiers = Array.from(
    new Set(dataset.calls.map((call) => call.trustTier))
  )
  const explainabilityFlags = Array.from(
    new Set(dataset.calls.flatMap((call) => call.explainabilityFlags))
  )
  const environmentTags = Array.from(
    new Set(dataset.calls.flatMap((call) => call.environmentTags))
  )

  const workspaceContent = (
    <div className="flex h-full min-w-0 flex-col gap-4 p-4">
      <WaveformPanel
        audioUrl={dataset.calls[0]?.audioUrl ?? "/demo-call.wav"}
        tracks={dataset.waveformTracks}
      />

      <Tabs defaultValue="overview" className="min-w-0">
        <TabsList className="h-auto flex-wrap justify-start">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
          <TabsTrigger value="questions">Questions</TabsTrigger>
          <TabsTrigger value="evidence">Evidence</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4 flex flex-col gap-4">
          <MetricGrid
            title="Quality"
            description="Audio quality and trust framing for the current scope."
            items={dataset.qualityMetrics}
          />
          <MetricGrid
            title="Structure"
            description="Conversation dynamics such as pauses, interruptions, and pacing."
            items={dataset.structureMetrics}
          />
          <MetricGrid
            title="Business"
            description="Workflow, outcome, and review state linked to this analysis."
            items={dataset.businessMetrics}
          />

          <div className="grid gap-4 xl:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Behavior signals</CardTitle>
                <CardDescription>
                  Signals are grouped as computed behavioral summaries, not raw truth.
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                {dataset.behaviorSignals.map((signal) => (
                  <div
                    key={signal.id}
                    className="flex items-center justify-between gap-3 rounded-lg border p-3"
                  >
                    <div className="flex flex-col gap-1">
                      <span className="text-sm font-medium">{signal.label}</span>
                      <span className="text-xs text-muted-foreground">
                        confidence {signal.confidence}
                      </span>
                    </div>
                    <Badge variant="secondary" className="font-mono tabular-nums">
                      {signal.score == null ? "not computed" : signal.score.toFixed(2)}
                    </Badge>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Affect signals</CardTitle>
                <CardDescription>
                  Experimental and always read with quality and trust context.
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                {dataset.emotionSignals.map((signal) => (
                  <div
                    key={signal.id}
                    className="flex items-center justify-between gap-3 rounded-lg border p-3"
                  >
                    <div className="flex flex-col gap-1">
                      <span className="text-sm font-medium">{signal.label}</span>
                      <span className="text-xs text-muted-foreground">
                        confidence {signal.confidence}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">experimental</Badge>
                      <Badge variant="outline" className="font-mono tabular-nums">
                        {signal.score == null ? "not computed" : signal.score.toFixed(2)}
                      </Badge>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="timeline" className="mt-4">
          <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
            <Card>
              <CardHeader>
                <CardTitle>Timeline interpretation</CardTitle>
                <CardDescription>
                  The waveform remains the main forensic surface. These notes explain
                  which segments are discounted or worth review.
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                {dataset.processingWarnings.map((warning) => (
                  <div
                    key={warning.id}
                    className="flex items-start gap-3 rounded-lg border p-3 text-sm"
                  >
                    <AlertTriangleIcon className="mt-0.5 size-4 text-muted-foreground" />
                    <div className="flex flex-col gap-1">
                      <span className="font-medium">{warning.level}</span>
                      <p className="text-muted-foreground">{warning.message}</p>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Active explainability mask</CardTitle>
                <CardDescription>
                  These flags tell you why a metric may be discounted.
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                <div className="flex flex-wrap gap-2">
                  {environmentTags.map((tag) => (
                    <Badge key={tag} variant="outline">
                      {tag}
                    </Badge>
                  ))}
                </div>
                <Separator />
                <div className="flex flex-col gap-2">
                  {explainabilityFlags.length > 0 ? (
                    explainabilityFlags.map((flag) => (
                      <p key={flag} className="text-sm text-muted-foreground">
                        {flag}
                      </p>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      No active explainability discounts in this scope.
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="questions" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Question drilldown</CardTitle>
              <CardDescription>
                Each question shows latency, hesitation, directness, affect tag, and
                any quality mask applied to the interpretation.
              </CardDescription>
            </CardHeader>
            <CardContent className="min-w-0 overflow-x-auto">
              <Table className="min-w-[980px]">
                <TableHeader>
                  <TableRow>
                    <TableHead>Question</TableHead>
                    <TableHead>Answer speaker</TableHead>
                    <TableHead>Latency</TableHead>
                    <TableHead>Answer length</TableHead>
                    <TableHead>Hesitation</TableHead>
                    <TableHead>Directness</TableHead>
                    <TableHead>Affect</TableHead>
                    <TableHead>Quality mask</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {dataset.questionInsights.map((question) => (
                    <TableRow key={question.id}>
                      <TableCell className="max-w-[320px] whitespace-normal">
                        <div className="flex flex-col gap-1">
                          <span>{question.questionText}</span>
                          <span className="text-xs text-muted-foreground">
                            {question.behaviorSummary}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>{question.answerSpeaker}</TableCell>
                      <TableCell className="font-mono tabular-nums">
                        {(question.responseLatencyMs / 1000).toFixed(1)}s
                      </TableCell>
                      <TableCell className="font-mono tabular-nums">
                        {question.answerLengthSeconds.toFixed(0)}s
                      </TableCell>
                      <TableCell className="font-mono tabular-nums">
                        {question.hesitationIndex.toFixed(2)}
                      </TableCell>
                      <TableCell className="font-mono tabular-nums">
                        {question.directnessScore.toFixed(2)}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{question.affectTag}</Badge>
                      </TableCell>
                      <TableCell className="max-w-[240px] whitespace-normal">
                        <div className="flex flex-wrap gap-2">
                          {question.qualityMask.length > 0 ? (
                            question.qualityMask.map((flag) => (
                              <Badge key={flag} variant="outline">
                                {flag}
                              </Badge>
                            ))
                          ) : (
                            <span className="text-sm text-muted-foreground">None</span>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="evidence" className="mt-4">
          <div className="grid gap-4 xl:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Evidence refs</CardTitle>
                <CardDescription>
                  Timestamp-linked references used by the current explanations.
                </CardDescription>
              </CardHeader>
              <CardContent className="min-w-0 overflow-x-auto">
                <Table className="min-w-[460px]">
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Timestamp</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {dataset.evidenceRefs.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell>{item.label}</TableCell>
                        <TableCell>{item.type}</TableCell>
                        <TableCell className="font-mono tabular-nums">
                          {(item.timestampMs / 1000).toFixed(1)}s
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Raw JSON explorer</CardTitle>
                <CardDescription>
                  Placeholder structured output so backend adapters can plug in later.
                </CardDescription>
              </CardHeader>
              <CardContent className="min-w-0">
                <ScrollArea className="h-80 rounded-lg border">
                  <pre className="break-words whitespace-pre-wrap p-4 text-xs font-mono tabular-nums">
                    {JSON.stringify(dataset.rawJson, null, 2)}
                  </pre>
                </ScrollArea>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )

  const inspectorContent = (
    <ScrollArea className="h-full">
      <div className="flex min-w-0 flex-col gap-4 p-4">
        <Card>
          <CardHeader>
            <CardTitle>Scope</CardTitle>
            <CardDescription>
              {dataset.calls.length} call(s) loaded in this workspace.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {dataset.calls.map((call) => (
              <div key={call.id} className="rounded-lg border p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium">{call.title}</span>
                  <Badge variant={badgeVariantForOutcome(call.businessOutcome)}>
                    {call.businessOutcome}
                  </Badge>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{call.summary}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Badge variant={badgeVariantForQuality(call.qualityTier)}>
                    {call.qualityTier}
                  </Badge>
                  <Badge variant={badgeVariantForTrust(call.trustTier)}>
                    {call.trustTier}
                  </Badge>
                  <Badge variant="outline">{call.workflowLabel}</Badge>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Warnings</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {dataset.processingWarnings.map((warning) => (
              <div key={warning.id} className="rounded-lg border p-3 text-sm">
                <span className="font-medium">{warning.level}</span>
                <p className="text-muted-foreground">{warning.message}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Model runs</CardTitle>
            <CardDescription>
              These are explicit placeholders until backend processing is connected.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {dataset.modelRuns.map((run) => (
              <div
                key={run.id}
                className="flex items-center justify-between gap-2 rounded-lg border p-3 text-sm"
              >
                <div className="flex items-center gap-2">
                  <SparklesIcon className="size-4 text-muted-foreground" />
                  <div className="flex flex-col">
                    <span>{run.name}</span>
                    <span className="font-mono text-xs text-muted-foreground">
                      {run.version}
                    </span>
                  </div>
                </div>
                <Badge variant="outline">{run.status}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Placeholder actions</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            <Button disabled variant="outline">
              <ListChecksIcon data-icon="inline-start" />
              AI summary placeholder
            </Button>
            <Button disabled variant="outline">
              <FileJsonIcon data-icon="inline-start" />
              Export placeholder
            </Button>
          </CardContent>
        </Card>
      </div>
    </ScrollArea>
  )

  return (
    <div className="flex min-w-0 flex-col gap-6 p-4 md:p-6">
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">
            {dataset.scope.kind === "single" ? "Single call" : "Grouped analysis"}
          </Badge>
          <Badge variant="outline">Backend placeholder</Badge>
          <Badge variant="outline">LLM placeholder</Badge>
          <Badge variant="outline">Affect is experimental</Badge>
        </div>

        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold text-balance">{dataset.scope.label}</h1>
          <p className="text-sm text-muted-foreground">
            This workspace links business outcome, demographic context, audio
            quality, and explainability so the call can be read like a forensic
            business event, not just a transcript.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          {states.map((state) => (
            <Badge key={state} variant="outline">
              {state}
            </Badge>
          ))}
          {languages.map((language) => (
            <Badge key={language} variant="outline">
              {language}
            </Badge>
          ))}
          {workflows.map((workflow) => (
            <Badge key={workflow} variant="outline">
              {workflow}
            </Badge>
          ))}
          {outcomes.map((outcome) => (
            <Badge key={outcome} variant={badgeVariantForOutcome(outcome)}>
              {outcome}
            </Badge>
          ))}
          {qualityTiers.map((tier) => (
            <Badge key={tier} variant={badgeVariantForQuality(tier)}>
              {tier}
            </Badge>
          ))}
          {trustTiers.map((tier) => (
            <Badge key={tier} variant={badgeVariantForTrust(tier)}>
              {tier}
            </Badge>
          ))}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {dataset.headlineMetrics.map((metric) => (
          <Card key={metric.id}>
            <CardHeader>
              <CardDescription>{metric.label}</CardDescription>
              <CardTitle className="font-mono tabular-nums">{metric.value}</CardTitle>
            </CardHeader>
            <CardContent className="flex items-center justify-between gap-2">
              <span className="text-xs text-muted-foreground">
                {metric.experimental ? "experimental" : "core metric"}
              </span>
              {metric.delta ? (
                <Badge variant="outline" className="font-mono tabular-nums">
                  {metric.delta}
                </Badge>
              ) : null}
            </CardContent>
          </Card>
        ))}
      </div>

      {explainabilityFlags.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Active trust discounts</CardTitle>
            <CardDescription>
              These flags lower confidence on some behavior or affect interpretations.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {explainabilityFlags.map((flag) => (
              <Badge key={flag} variant="outline">
                {flag}
              </Badge>
            ))}
          </CardContent>
        </Card>
      ) : null}

      <div className="grid gap-4 2xl:hidden">
        <div className="rounded-xl border">{workspaceContent}</div>
        <div className="rounded-xl border">{inspectorContent}</div>
      </div>

      <ResizablePanelGroup
        orientation="horizontal"
        className="hidden min-h-[720px] min-w-0 overflow-hidden rounded-xl border 2xl:flex"
      >
        <ResizablePanel defaultSize={72} minSize={60} className="min-w-0">
          {workspaceContent}
        </ResizablePanel>
        <ResizableHandle withHandle />
        <ResizablePanel defaultSize={28} minSize={20} className="min-w-0">
          {inspectorContent}
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  )
}
