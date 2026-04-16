"use client"

import Link from "next/link"
import { ArrowRightIcon, TrendingUpIcon } from "lucide-react"
import { Area, AreaChart, Bar, BarChart, CartesianGrid, XAxis } from "recharts"

import { Badge } from "@/components/ui/badge"
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
import { Button } from "@/components/ui/button"
import { calls, dashboardMetrics, dashboardTrendSeries, recentAnomalies } from "@/lib/mock-data"

const volumeChartConfig = {
  calls: {
    label: "Calls",
    color: "var(--chart-1)",
  },
} satisfies ChartConfig

const signalChartConfig = {
  overlap: {
    label: "Overlap",
    color: "var(--chart-2)",
  },
  hesitation: {
    label: "Hesitation",
    color: "var(--chart-3)",
  },
} satisfies ChartConfig

export function DashboardView() {
  return (
    <div className="flex flex-col gap-6 p-4 md:p-6">
      <div className="flex flex-col gap-2">
        <Badge variant="secondary" className="w-fit">
          Home dashboard
        </Badge>
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold">Voice analytics workspace</h1>
          <p className="text-sm text-muted-foreground">
            Track call volume, hesitation, overlap, and experimental affect signals with stock shadcn UI and mock repositories.
          </p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {dashboardMetrics.map((metric) => (
          <Card key={metric.id}>
            <CardHeader>
              <CardDescription>{metric.label}</CardDescription>
              <CardTitle>{metric.value}</CardTitle>
            </CardHeader>
            <CardFooter className="justify-between">
              <span className="text-xs text-muted-foreground">vs last period</span>
              {metric.delta ? (
                <Badge variant="outline">{metric.delta}</Badge>
              ) : null}
            </CardFooter>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[2fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Call volume</CardTitle>
            <CardDescription>Trend of analyzed calls over the last 7 days.</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={volumeChartConfig}>
              <BarChart accessibilityLayer data={dashboardTrendSeries}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="date" tickLine={false} axisLine={false} tickMargin={8} />
                <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
                <Bar dataKey="calls" radius={6} fill="var(--color-calls)" />
              </BarChart>
            </ChartContainer>
          </CardContent>
          <CardFooter>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <TrendingUpIcon data-icon="inline-start" />
              Average analyzed calls are up week over week.
            </div>
          </CardFooter>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent anomalies</CardTitle>
            <CardDescription>Fast scan of the most important outliers.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {recentAnomalies.map((item) => (
              <div key={item.id} className="flex flex-col gap-1 rounded-lg border p-3">
                <span className="text-sm font-medium">{item.title}</span>
                <p className="text-sm text-muted-foreground">{item.detail}</p>
              </div>
            ))}
          </CardContent>
          <CardFooter>
            <Button nativeButton={false} render={<Link href="/calls" />} variant="outline">
              Review calls
              <ArrowRightIcon data-icon="inline-end" />
            </Button>
          </CardFooter>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-[2fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Behavior vs emotion</CardTitle>
            <CardDescription>
              Equal-priority summary chart for overlap and hesitation signals.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={signalChartConfig}>
              <AreaChart
                accessibilityLayer
                data={dashboardTrendSeries}
                margin={{ left: 12, right: 12 }}
              >
                <CartesianGrid vertical={false} />
                <XAxis dataKey="date" tickLine={false} axisLine={false} tickMargin={8} />
                <ChartTooltip cursor={false} content={<ChartTooltipContent indicator="line" />} />
                <Area
                  dataKey="overlap"
                  type="monotone"
                  fill="var(--color-overlap)"
                  fillOpacity={0.25}
                  stroke="var(--color-overlap)"
                />
                <Area
                  dataKey="hesitation"
                  type="monotone"
                  fill="var(--color-hesitation)"
                  fillOpacity={0.15}
                  stroke="var(--color-hesitation)"
                />
              </AreaChart>
            </ChartContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent analyses</CardTitle>
            <CardDescription>Latest ready calls available for inspection.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {calls
              .filter((call) => call.status === "ready")
              .slice(0, 3)
              .map((call) => (
                <div key={call.id} className="flex flex-col gap-1 rounded-lg border p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium">{call.title}</span>
                    <Badge variant="outline">{call.reviewState}</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">{call.summary}</p>
                </div>
              ))}
          </CardContent>
          <CardFooter>
            <Button
              nativeButton={false}
              render={<Link href="/analysis" />}
              variant="outline"
            >
              Open analysis
              <ArrowRightIcon data-icon="inline-end" />
            </Button>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}
