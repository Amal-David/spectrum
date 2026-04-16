"use client"

import Link from "next/link"
import {
  ArrowRightIcon,
  AudioLinesIcon,
  BotIcon,
  GlobeIcon,
  ShieldAlertIcon,
  TrendingUpIcon,
  UsersIcon,
} from "lucide-react"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Scatter,
  ScatterChart,
  XAxis,
  YAxis,
} from "recharts"
import type { EChartsOption } from "echarts"

import { EChart } from "@/components/app/echart"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { dashboardDataset } from "@/lib/mock-data"

const businessTrendConfig = {
  conversations: {
    label: "Conversations",
    color: "var(--chart-1)",
  },
  completions: {
    label: "Completions",
    color: "var(--chart-3)",
  },
  escalations: {
    label: "Escalations",
    color: "var(--chart-4)",
  },
} satisfies ChartConfig

const outcomeMixConfig = {
  resolved: {
    label: "Resolved",
    color: "var(--chart-2)",
  },
  converted: {
    label: "Converted",
    color: "var(--chart-3)",
  },
  escalated: {
    label: "Escalated",
    color: "var(--chart-4)",
  },
  abandoned: {
    label: "Abandoned",
    color: "var(--chart-5)",
  },
} satisfies ChartConfig

const languageConfig = {
  callVolume: {
    label: "Call volume",
    color: "var(--chart-2)",
  },
  completionRate: {
    label: "Completion rate",
    color: "var(--chart-3)",
  },
} satisfies ChartConfig

const behaviorConfig = {
  hesitationScore: {
    label: "Hesitation",
    color: "var(--chart-4)",
  },
  interruptionRate: {
    label: "Interruption rate",
    color: "var(--chart-5)",
  },
  overlapRate: {
    label: "Overlap rate",
    color: "var(--chart-2)",
  },
} satisfies ChartConfig

const qualityConfig = {
  avgSnrDb: {
    label: "Avg SNR",
    color: "var(--chart-1)",
  },
  noisySegmentRate: {
    label: "Noisy segment rate",
    color: "var(--chart-4)",
  },
  insightDiscountRate: {
    label: "Insight discount rate",
    color: "var(--chart-5)",
  },
} satisfies ChartConfig

const workflowConfig = {
  successRate: {
    label: "Success rate",
    color: "var(--chart-2)",
  },
  escalationRate: {
    label: "Escalation rate",
    color: "var(--chart-4)",
  },
} satisfies ChartConfig

const stateMatrix = Array.from(
  dashboardDataset.emotionAggregates.reduce((set, item) => set.add(item.demographicLabel), new Set<string>())
)

const emotionMatrix = Array.from(
  dashboardDataset.emotionAggregates.reduce((set, item) => set.add(item.emotion), new Set<string>())
)

const emotionHeatmapOption: EChartsOption = {
  animation: false,
  grid: {
    left: 90,
    right: 24,
    top: 16,
    bottom: 32,
  },
  tooltip: {
    trigger: "item",
    formatter: (params) => {
      const entry = params as { value?: [number, number, number] }
      const value = Array.isArray(entry.value) ? entry.value[2] : entry.value
      const state = Array.isArray(entry.value) ? stateMatrix[entry.value[1] as number] : ""
      const emotion = Array.isArray(entry.value)
        ? emotionMatrix[entry.value[0] as number]
        : ""

      return `${state}<br/>${emotion}: ${value}`
    },
  },
  xAxis: {
    type: "category",
    data: emotionMatrix,
    axisLabel: {
      fontFamily: "var(--font-geist-mono)",
    },
  },
  yAxis: {
    type: "category",
    data: stateMatrix,
    axisLabel: {
      fontFamily: "var(--font-geist-mono)",
    },
  },
  visualMap: {
    min: 0.2,
    max: 0.8,
    show: false,
    inRange: {
      color: ["#f5f5f5", "#a1a1aa", "#18181b"],
    },
  },
  series: [
    {
      type: "heatmap",
      data: dashboardDataset.emotionAggregates.map((item) => [
        emotionMatrix.indexOf(item.emotion),
        stateMatrix.indexOf(item.demographicLabel),
        Number(item.score.toFixed(2)),
      ]),
      emphasis: {
        itemStyle: {
          borderColor: "#18181b",
          borderWidth: 1,
        },
      },
      label: {
        show: true,
        formatter: (params) => {
          const entry = params as unknown as { data: [number, number, number] }
          return String(entry.data[2])
        },
        fontFamily: "var(--font-geist-mono)",
        fontSize: 10,
      },
    },
  ],
}

const statePerformanceOption: EChartsOption = {
  animation: false,
  tooltip: {
    trigger: "item",
    formatter: (params) => {
      const entry = params as unknown as {
        data: (typeof dashboardDataset.statePerformance)[number]
      }
      const data = entry.data
      return [
        `<strong>${data.state}</strong>`,
        `Call volume: ${data.callVolume.toLocaleString()}`,
        `Completion rate: ${data.completionRate}%`,
        `Escalation rate: ${data.escalationRate}%`,
        `Avg SNR: ${data.avgSnrDb} dB`,
      ].join("<br/>")
    },
  },
  xAxis: {
    min: 0,
    max: 10,
    show: false,
  },
  yAxis: {
    min: 0,
    max: 10,
    show: false,
  },
  series: [
    {
      type: "scatter",
      symbolSize: (value: number[]) => Math.max(value[2] / 120, 22),
      label: {
        show: true,
        position: "top",
        formatter: (params) => {
          const entry = params as unknown as {
            data: (typeof dashboardDataset.statePerformance)[number]
          }
          return entry.data.stateCode
        },
        fontFamily: "var(--font-geist-mono)",
        fontSize: 11,
      },
      itemStyle: {
        color: "#18181b",
        opacity: 0.8,
      },
      data: dashboardDataset.statePerformance.map((item) => ({
        ...item,
        value: [item.x, item.y, item.callVolume],
      })),
    },
  ],
}

const latencyBoxplotOption: EChartsOption = {
  animation: false,
  grid: {
    left: 40,
    right: 16,
    top: 12,
    bottom: 32,
  },
  tooltip: {
    trigger: "item",
  },
  xAxis: {
    type: "category",
    data: ["North", "West", "South", "East"],
    axisLabel: {
      fontFamily: "var(--font-geist-mono)",
    },
  },
  yAxis: {
    type: "value",
    axisLabel: {
      fontFamily: "var(--font-geist-mono)",
      formatter: "{value} ms",
    },
    splitLine: {
      lineStyle: {
        color: "#e4e4e7",
      },
    },
  },
  series: [
    {
      type: "boxplot",
      data: [
        [1200, 1700, 2200, 3200, 4200],
        [900, 1400, 1800, 2600, 3500],
        [800, 1200, 1600, 2100, 2800],
        [1000, 1600, 2100, 2900, 3700],
      ],
      itemStyle: {
        color: "#f4f4f5",
        borderColor: "#18181b",
      },
    },
  ],
}

const trustMatrixOption: EChartsOption = {
  animation: false,
  grid: {
    left: 70,
    right: 20,
    top: 12,
    bottom: 28,
  },
  tooltip: {
    trigger: "item",
  },
  xAxis: {
    type: "category",
    data: ["Low SNR", "VAD Instability", "Overlap", "Noise Tags"],
    axisLabel: {
      fontFamily: "var(--font-geist-mono)",
      interval: 0,
    },
  },
  yAxis: {
    type: "category",
    data: dashboardDataset.geographySummaries.map((item) => item.stateCode),
    axisLabel: {
      fontFamily: "var(--font-geist-mono)",
    },
  },
  visualMap: {
    min: 0,
    max: 4,
    show: false,
    inRange: {
      color: ["#fafafa", "#d4d4d8", "#71717a", "#18181b"],
    },
  },
  series: [
    {
      type: "heatmap",
      data: dashboardDataset.geographySummaries.flatMap((item, rowIndex) => [
        [0, rowIndex, item.avgSnrDb < 15 ? 4 : item.avgSnrDb < 18 ? 2 : 1],
        [1, rowIndex, item.trustTier === "review" ? 4 : item.trustTier === "discounted" ? 3 : 1],
        [2, rowIndex, item.hesitationScore > 0.55 ? 3 : 1],
        [3, rowIndex, item.frictionScore > 0.5 ? 3 : 1],
      ]),
      label: {
        show: true,
        formatter: (params) => {
          const entry = params as unknown as { data: [number, number, number] }
          return String(entry.data[2])
        },
        fontFamily: "var(--font-geist-mono)",
        fontSize: 10,
      },
    },
  ],
}

const topEmotionCohorts = [...dashboardDataset.emotionAggregates]
  .sort((left, right) => right.score - left.score)
  .slice(0, 4)

const regionComparison = Object.values(
  dashboardDataset.geographySummaries.reduce<
    Record<string, { region: string; callVolume: number; completionRate: number; escalationRate: number }>
  >((accumulator, item) => {
    const current =
      accumulator[item.region] ?? {
        region: item.region,
        callVolume: 0,
        completionRate: 0,
        escalationRate: 0,
      }

    current.callVolume += item.callVolume
    current.completionRate += item.completionRate
    current.escalationRate += item.escalationRate

    accumulator[item.region] = current

    return accumulator
  }, {})
).map((item) => ({
  ...item,
  completionRate: Number((item.completionRate / 2).toFixed(1)),
  escalationRate: Number((item.escalationRate / 2).toFixed(1)),
}))

const emotionByLanguage = dashboardDataset.demographicSlices.map((item) => ({
  language: item.language,
  frustrationRisk: Number(item.frustrationRisk.toFixed(2)),
  rapportScore: Number(item.rapportScore.toFixed(2)),
}))

const hesitationByState = dashboardDataset.geographySummaries.map((item) => ({
  state: item.stateCode,
  hesitationScore: Number(item.hesitationScore.toFixed(2)),
}))

const overlapByLanguage = dashboardDataset.behaviorAggregates.map((item) => ({
  language: item.demographicLabel,
  interruptionRate: Number(item.interruptionRate.toFixed(2)),
  overlapRate: Number(item.overlapRate.toFixed(2)),
}))

const workflowScatter = dashboardDataset.agentPerformance.map((item) => ({
  workflow: item.workflowLabel,
  trustScore: item.trustScore,
  successRate: Number((item.successRate * 100).toFixed(1)),
  volume: item.volume,
}))

const severityVariant = {
  critical: "destructive",
  watch: "secondary",
  info: "outline",
} as const

export function DashboardView() {
  return (
    <div className="flex min-w-0 flex-col gap-6 p-4 md:p-6">
      <div className="flex flex-col gap-2">
        <Badge variant="secondary" className="w-fit">
          Business dashboard
        </Badge>
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold text-balance">
            Google Analytics for voice AI agents
          </h1>
          <p className="max-w-4xl text-sm text-muted-foreground">
            Track business outcomes, India-first demographic performance, trusted emotion and
            behavior patterns, and the cohorts that need review before the next agent release.
          </p>
        </div>
      </div>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
        {dashboardDataset.businessMetrics.map((metric) => (
          <Card key={metric.id}>
            <CardHeader className="gap-1">
              <CardDescription>{metric.label}</CardDescription>
              <CardTitle className="font-mono tabular-nums">{metric.value}</CardTitle>
            </CardHeader>
            <CardContent className="flex items-center justify-between gap-3">
              <span className="text-xs text-muted-foreground">{metric.description}</span>
              {metric.delta ? <Badge variant="outline">{metric.delta}</Badge> : null}
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="grid gap-4 2xl:grid-cols-[1.8fr_1.2fr]">
        <Card>
          <CardHeader>
            <CardTitle>Business Overview</CardTitle>
            <CardDescription>
              Conversations, successful completions, and escalation volume over the last 7 days.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={businessTrendConfig}>
              <AreaChart accessibilityLayer data={dashboardDataset.businessTrend}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="date" tickLine={false} axisLine={false} tickMargin={8} />
                <YAxis tickLine={false} axisLine={false} tickMargin={8} />
                <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
                <Area
                  dataKey="conversations"
                  type="monotone"
                  fill="var(--color-conversations)"
                  fillOpacity={0.2}
                  stroke="var(--color-conversations)"
                />
                <Line
                  dataKey="completions"
                  dot={false}
                  stroke="var(--color-completions)"
                  strokeWidth={2}
                  type="monotone"
                />
                <Line
                  dataKey="escalations"
                  dot={false}
                  stroke="var(--color-escalations)"
                  strokeWidth={2}
                  type="monotone"
                />
              </AreaChart>
            </ChartContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Containment vs Escalation Mix</CardTitle>
            <CardDescription>
              Regional business outcomes across the active agent footprint.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={outcomeMixConfig}>
              <BarChart accessibilityLayer data={dashboardDataset.outcomeMix}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} />
                <YAxis tickLine={false} axisLine={false} tickMargin={8} />
                <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
                <Bar dataKey="resolved" fill="var(--color-resolved)" stackId="a" />
                <Bar dataKey="converted" fill="var(--color-converted)" stackId="a" />
                <Bar dataKey="escalated" fill="var(--color-escalated)" stackId="a" />
                <Bar dataKey="abandoned" fill="var(--color-abandoned)" stackId="a" />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 2xl:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>India Demographics Overview</CardTitle>
            <CardDescription>
              State-level performance view for call volume, completions, and trust-adjusted quality.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <EChart option={statePerformanceOption} className="h-[360px]" />
          </CardContent>
          <CardFooter>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <GlobeIcon data-icon="inline-start" />
              State is the primary demographic lens, with language as the main comparison layer.
            </div>
          </CardFooter>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top & Underperforming States</CardTitle>
            <CardDescription>
              Business and trust ranking for current India cohorts.
            </CardDescription>
          </CardHeader>
          <CardContent className="min-w-0">
            <Table className="min-w-[540px]">
              <TableHeader>
                <TableRow>
                  <TableHead>State</TableHead>
                  <TableHead>Volume</TableHead>
                  <TableHead>Completion</TableHead>
                  <TableHead>Escalation</TableHead>
                  <TableHead>Trust</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {dashboardDataset.geographySummaries.map((item) => (
                  <TableRow key={item.stateCode}>
                    <TableCell>
                      <div className="flex flex-col">
                        <span>{item.state}</span>
                        <span className="text-xs text-muted-foreground">{item.region}</span>
                      </div>
                    </TableCell>
                    <TableCell className="font-mono tabular-nums">
                      {item.callVolume.toLocaleString()}
                    </TableCell>
                    <TableCell className="font-mono tabular-nums">
                      {item.completionRate}%
                    </TableCell>
                    <TableCell className="font-mono tabular-nums">
                      {item.escalationRate}%
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          item.trustTier === "trusted"
                            ? "secondary"
                            : item.trustTier === "discounted"
                              ? "outline"
                              : "destructive"
                        }
                      >
                        {item.trustTier}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 2xl:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Language Distribution</CardTitle>
            <CardDescription>
              Call share and completion rate across primary language cohorts.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={languageConfig}>
              <BarChart accessibilityLayer data={dashboardDataset.languageDistribution} layout="vertical">
                <CartesianGrid horizontal={false} />
                <XAxis type="number" tickLine={false} axisLine={false} tickMargin={8} />
                <YAxis
                  dataKey="language"
                  tickLine={false}
                  axisLine={false}
                  tickMargin={8}
                  type="category"
                  width={110}
                />
                <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
                <Bar dataKey="callVolume" fill="var(--color-callVolume)" radius={6} />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Region Comparison</CardTitle>
            <CardDescription>
              Compare regional call share, completion, and escalation patterns.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={languageConfig}>
              <BarChart accessibilityLayer data={regionComparison}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="region" tickLine={false} axisLine={false} tickMargin={8} />
                <YAxis tickLine={false} axisLine={false} tickMargin={8} />
                <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
                <Bar dataKey="callVolume" fill="var(--color-callVolume)" radius={6} />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 2xl:grid-cols-[1.25fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Emotion Across Demographics</CardTitle>
            <CardDescription>
              Confidence-banded emotion matrix across major state cohorts.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <EChart option={emotionHeatmapOption} className="h-[360px]" />
          </CardContent>
        </Card>

        <div className="grid gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Emotion by Language</CardTitle>
              <CardDescription>
                Frustration and rapport by language cohort.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ChartContainer config={languageConfig}>
                <BarChart accessibilityLayer data={emotionByLanguage}>
                  <CartesianGrid vertical={false} />
                  <XAxis dataKey="language" tickLine={false} axisLine={false} tickMargin={8} />
                  <YAxis tickLine={false} axisLine={false} tickMargin={8} />
                  <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
                  <Bar dataKey="frustrationRisk" fill="var(--chart-4)" radius={6} />
                  <Bar dataKey="rapportScore" fill="var(--chart-2)" radius={6} />
                </BarChart>
              </ChartContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Top Emotion Cohorts</CardTitle>
              <CardDescription>
                Highest soft-signal patterns by score and confidence.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {topEmotionCohorts.map((item) => (
                <div key={item.id} className="flex items-center justify-between gap-3 rounded-lg border p-3">
                  <div className="flex flex-col gap-1">
                    <span className="text-sm font-medium">
                      {item.demographicLabel} · {item.emotion}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      sample {item.sampleSize.toLocaleString()} · {item.trustTier}
                    </span>
                  </div>
                  <Badge variant="outline" className="font-mono tabular-nums">
                    {item.score.toFixed(2)}
                  </Badge>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="grid gap-4 2xl:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Behavior Across Demographics</CardTitle>
            <CardDescription>
              Hesitation, overlap, and interruption patterns by cohort.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={behaviorConfig}>
              <BarChart accessibilityLayer data={hesitationByState}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="state" tickLine={false} axisLine={false} tickMargin={8} />
                <YAxis tickLine={false} axisLine={false} tickMargin={8} />
                <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
                <Bar dataKey="hesitationScore" fill="var(--color-hesitationScore)" radius={6} />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Latency by Region</CardTitle>
            <CardDescription>
              Distribution of response latency by region, using a compact boxplot.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <EChart option={latencyBoxplotOption} className="h-[320px]" />
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 2xl:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Overlap & Interruption by Language</CardTitle>
            <CardDescription>
              Conversation structure differences by cohort.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={behaviorConfig}>
              <BarChart accessibilityLayer data={overlapByLanguage}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="language" tickLine={false} axisLine={false} tickMargin={8} />
                <YAxis tickLine={false} axisLine={false} tickMargin={8} />
                <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
                <Bar dataKey="interruptionRate" fill="var(--color-interruptionRate)" radius={6} />
                <Bar dataKey="overlapRate" fill="var(--color-overlapRate)" radius={6} />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quality & Reliability</CardTitle>
            <CardDescription>
              Noise, VAD, and trust-adjusted coverage trends.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={qualityConfig}>
              <LineChart accessibilityLayer data={dashboardDataset.qualityTrend}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="date" tickLine={false} axisLine={false} tickMargin={8} />
                <YAxis tickLine={false} axisLine={false} tickMargin={8} />
                <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
                <Line dataKey="avgSnrDb" dot={false} stroke="var(--color-avgSnrDb)" strokeWidth={2} />
                <Line
                  dataKey="noisySegmentRate"
                  dot={false}
                  stroke="var(--color-noisySegmentRate)"
                  strokeWidth={2}
                />
                <Line
                  dataKey="insightDiscountRate"
                  dot={false}
                  stroke="var(--color-insightDiscountRate)"
                  strokeWidth={2}
                />
              </LineChart>
            </ChartContainer>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 2xl:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Environment Tag Distribution</CardTitle>
            <CardDescription>
              What is most frequently contaminating trust in the current call volume?
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={languageConfig}>
              <BarChart accessibilityLayer data={dashboardDataset.environmentTags} layout="vertical">
                <CartesianGrid horizontal={false} />
                <XAxis type="number" tickLine={false} axisLine={false} tickMargin={8} />
                <YAxis
                  dataKey="tag"
                  tickLine={false}
                  axisLine={false}
                  tickMargin={8}
                  type="category"
                  width={88}
                />
                <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
                <Bar dataKey="count" fill="var(--chart-3)" radius={6} />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Low-Trust Cohort Matrix</CardTitle>
            <CardDescription>
              Where low SNR, VAD instability, and overlap are most concentrated.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <EChart option={trustMatrixOption} className="h-[320px]" />
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 2xl:grid-cols-[1.2fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Agent / Workflow Performance</CardTitle>
            <CardDescription>
              Business outcome by workflow, version, and trust-adjusted quality.
            </CardDescription>
          </CardHeader>
          <CardContent className="min-w-0">
            <Table className="min-w-[720px]">
              <TableHeader>
                <TableRow>
                  <TableHead>Workflow</TableHead>
                  <TableHead>Agent</TableHead>
                  <TableHead>Version</TableHead>
                  <TableHead>Volume</TableHead>
                  <TableHead>Success</TableHead>
                  <TableHead>Escalation</TableHead>
                  <TableHead>Trust</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {dashboardDataset.agentPerformance.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>
                      <div className="flex flex-col">
                        <span>{item.workflowLabel}</span>
                        <span className="text-xs text-muted-foreground">{item.campaign}</span>
                      </div>
                    </TableCell>
                    <TableCell>{item.agentLabel}</TableCell>
                    <TableCell className="font-mono">{item.promptVersion}</TableCell>
                    <TableCell className="font-mono tabular-nums">
                      {item.volume.toLocaleString()}
                    </TableCell>
                    <TableCell className="font-mono tabular-nums">
                      {(item.successRate * 100).toFixed(1)}%
                    </TableCell>
                    <TableCell className="font-mono tabular-nums">
                      {(item.escalationRate * 100).toFixed(1)}%
                    </TableCell>
                    <TableCell className="font-mono tabular-nums">
                      {item.trustScore}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <div className="grid gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Workflow Outcome Mix</CardTitle>
              <CardDescription>
                Success and escalation comparison across workflows.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ChartContainer config={workflowConfig}>
                <BarChart accessibilityLayer data={dashboardDataset.agentPerformance}>
                  <CartesianGrid vertical={false} />
                  <XAxis dataKey="workflowLabel" tickLine={false} axisLine={false} tickMargin={8} />
                  <YAxis tickLine={false} axisLine={false} tickMargin={8} />
                  <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
                  <Bar dataKey="successRate" fill="var(--color-successRate)" radius={6} />
                  <Bar dataKey="escalationRate" fill="var(--color-escalationRate)" radius={6} />
                </BarChart>
              </ChartContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Trust vs Success</CardTitle>
              <CardDescription>
                Volume-weighted view of which workflows are both trusted and effective.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ChartContainer config={workflowConfig}>
                <ScatterChart accessibilityLayer margin={{ left: 8, right: 8, top: 8, bottom: 8 }}>
                  <CartesianGrid />
                  <XAxis
                    dataKey="trustScore"
                    name="Trust"
                    tickLine={false}
                    axisLine={false}
                    tickMargin={8}
                    type="number"
                  />
                  <YAxis
                    dataKey="successRate"
                    name="Success"
                    tickLine={false}
                    axisLine={false}
                    tickMargin={8}
                    type="number"
                  />
                  <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
                  <Scatter data={workflowScatter}>
                    {workflowScatter.map((item) => (
                      <Cell key={item.workflow} fill="#18181b" />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ChartContainer>
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1fr_320px]">
        <Card>
          <CardHeader>
            <CardTitle>Review Queue</CardTitle>
            <CardDescription>
              High-friction clusters, low-trust cohorts, and anomalies that need human attention.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {dashboardDataset.reviewQueue.map((item) => (
              <div key={item.id} className="flex flex-col gap-3 rounded-lg border p-4 md:flex-row md:items-center md:justify-between">
                <div className="flex min-w-0 flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{item.title}</span>
                    <Badge variant={severityVariant[item.severity]}>{item.severity}</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">{item.detail}</p>
                </div>
                <Button nativeButton={false} render={<Link href={item.href} />} variant="outline">
                  Open
                  <ArrowRightIcon data-icon="inline-end" />
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick Jump</CardTitle>
            <CardDescription>
              Move from business signals into catalog and forensic views.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Button nativeButton={false} render={<Link href="/calls" />} variant="outline">
              <AudioLinesIcon data-icon="inline-start" />
              Open calls catalog
            </Button>
            <Button nativeButton={false} render={<Link href="/analysis" />} variant="outline">
              <ShieldAlertIcon data-icon="inline-start" />
              Open analysis workspace
            </Button>
            <Button
              nativeButton={false}
              render={<Link href="/analysis?groupId=group-002" />}
              variant="outline"
            >
              <UsersIcon data-icon="inline-start" />
              Review collections cluster
            </Button>
            <Button
              nativeButton={false}
              render={<Link href="/analysis?groupId=group-001" />}
              variant="outline"
            >
              <BotIcon data-icon="inline-start" />
              Inspect pricing workflow
            </Button>
          </CardContent>
          <CardFooter>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <TrendingUpIcon data-icon="inline-start" />
              Start at the business layer, then drill down only where trust and outcome diverge.
            </div>
          </CardFooter>
        </Card>
      </section>
    </div>
  )
}
