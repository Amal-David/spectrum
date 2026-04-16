"use client"

import * as React from "react"
import { FileJsonIcon, ListChecksIcon, SparklesIcon } from "lucide-react"

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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { WaveformPanel } from "@/components/app/waveform-panel"
import type { AnalysisDataset } from "@/lib/types"

type AnalysisWorkspaceProps = {
  dataset: AnalysisDataset
}

export function AnalysisWorkspace({ dataset }: AnalysisWorkspaceProps) {
  return (
    <div className="flex flex-col gap-6 p-4 md:p-6">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <Badge variant="secondary">
            {dataset.scope.kind === "single" ? "Single call" : "Grouped analysis"}
          </Badge>
          <Badge variant="outline">Backend placeholder</Badge>
          <Badge variant="outline">LLM placeholder</Badge>
        </div>
        <h1 className="text-2xl font-semibold">{dataset.scope.label}</h1>
        <p className="text-sm text-muted-foreground">
          Behavioral and emotional tracks are shown with equal UI priority, while experimental affect remains explicitly labeled.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {dataset.headlineMetrics.map((metric) => (
          <Card key={metric.id}>
            <CardHeader>
              <CardDescription>{metric.label}</CardDescription>
              <CardTitle>{metric.value}</CardTitle>
            </CardHeader>
            <CardContent className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                {metric.experimental ? "experimental" : "core metric"}
              </span>
              {metric.confidence ? <Badge variant="outline">{metric.confidence}</Badge> : null}
            </CardContent>
          </Card>
        ))}
      </div>

      <ResizablePanelGroup orientation="horizontal" className="min-h-[720px] rounded-xl border">
        <ResizablePanel defaultSize={72} minSize={60}>
          <div className="flex h-full flex-col gap-4 p-4">
            <WaveformPanel
              audioUrl={dataset.calls[0]?.audioUrl ?? "/demo-call.wav"}
              tracks={dataset.waveformTracks}
            />

            <Tabs defaultValue="overview">
              <TabsList>
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="timeline">Timeline</TabsTrigger>
                <TabsTrigger value="questions">Questions</TabsTrigger>
                <TabsTrigger value="evidence">Evidence</TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="mt-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <Card>
                    <CardHeader>
                      <CardTitle>Behavior signals</CardTitle>
                    </CardHeader>
                    <CardContent className="flex flex-col gap-3">
                      {dataset.behaviorSignals.map((signal) => (
                        <div key={signal.id} className="flex items-center justify-between gap-2 rounded-lg border p-3">
                          <div className="flex flex-col gap-1">
                            <span className="text-sm font-medium">{signal.label}</span>
                            <span className="text-xs text-muted-foreground">confidence {signal.confidence}</span>
                          </div>
                          <Badge variant="secondary">
                            {signal.score == null ? "not computed" : signal.score.toFixed(2)}
                          </Badge>
                        </div>
                      ))}
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader>
                      <CardTitle>Emotion signals</CardTitle>
                      <CardDescription>Experimental and confidence-banded.</CardDescription>
                    </CardHeader>
                    <CardContent className="flex flex-col gap-3">
                      {dataset.emotionSignals.map((signal) => (
                        <div key={signal.id} className="flex items-center justify-between gap-2 rounded-lg border p-3">
                          <div className="flex flex-col gap-1">
                            <span className="text-sm font-medium">{signal.label}</span>
                            <span className="text-xs text-muted-foreground">confidence {signal.confidence}</span>
                          </div>
                          <Badge variant="outline">
                            {signal.score == null ? "not computed" : signal.score.toFixed(2)}
                          </Badge>
                        </div>
                      ))}
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>

              <TabsContent value="timeline" className="mt-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Timeline notes</CardTitle>
                    <CardDescription>
                      The waveform lane is the primary timeline surface. This tab keeps the player focus visible while adding explanatory notes.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="grid gap-3">
                    {dataset.processingWarnings.map((warning) => (
                      <div key={warning.id} className="rounded-lg border p-3 text-sm">
                        <span className="font-medium">{warning.level}</span>
                        <p className="text-muted-foreground">{warning.message}</p>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="questions" className="mt-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Question drilldown</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Question</TableHead>
                          <TableHead>Answer speaker</TableHead>
                          <TableHead>Latency</TableHead>
                          <TableHead>Hesitation</TableHead>
                          <TableHead>Summaries</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {dataset.questionInsights.map((question) => (
                          <TableRow key={question.id}>
                            <TableCell className="max-w-[280px] whitespace-normal">{question.questionText}</TableCell>
                            <TableCell>{question.answerSpeaker}</TableCell>
                            <TableCell>{(question.responseLatencyMs / 1000).toFixed(1)}s</TableCell>
                            <TableCell>{question.hesitationIndex.toFixed(2)}</TableCell>
                            <TableCell className="max-w-[320px] whitespace-normal">
                              <div className="flex flex-col gap-1">
                                <span>{question.behaviorSummary}</span>
                                <span className="text-muted-foreground">{question.emotionSummary}</span>
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
                    </CardHeader>
                    <CardContent>
                      <Table>
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
                              <TableCell>{(item.timestampMs / 1000).toFixed(1)}s</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader>
                      <CardTitle>Raw JSON explorer</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ScrollArea className="h-80 rounded-lg border">
                        <pre className="p-4 text-xs">{JSON.stringify(dataset.rawJson, null, 2)}</pre>
                      </ScrollArea>
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </ResizablePanel>
        <ResizableHandle withHandle />
        <ResizablePanel defaultSize={28} minSize={20}>
          <ScrollArea className="h-full">
            <div className="flex flex-col gap-4 p-4">
              <Card>
                <CardHeader>
                  <CardTitle>Scope</CardTitle>
                  <CardDescription>{dataset.calls.length} call(s) loaded in this workspace.</CardDescription>
                </CardHeader>
                <CardContent className="flex flex-col gap-3">
                  {dataset.calls.map((call) => (
                    <div key={call.id} className="rounded-lg border p-3">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-medium">{call.title}</span>
                        <Badge variant="outline">{call.status}</Badge>
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">{call.summary}</p>
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
                  <CardDescription>Deliberate placeholders until backend integration exists.</CardDescription>
                </CardHeader>
                <CardContent className="flex flex-col gap-2">
                  {dataset.modelRuns.map((run) => (
                    <div key={run.id} className="flex items-center justify-between gap-2 rounded-lg border p-3 text-sm">
                      <div className="flex items-center gap-2">
                        <SparklesIcon className="size-4 text-muted-foreground" />
                        <div className="flex flex-col">
                          <span>{run.name}</span>
                          <span className="text-xs text-muted-foreground">{run.version}</span>
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
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  )
}
