"use client"

import type { EChartsOption } from "echarts"

import { EChart } from "@/components/app/echart"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import type { EmotionSignalTrack } from "@/lib/types"

type EmbeddingPlotProps = {
  signals: EmotionSignalTrack[]
}

type PlotPoint = {
  pointLabel: string
  x: number
  y: number
  size: number
  score: number
}

function buildEmbeddingPoints(signals: EmotionSignalTrack[]): PlotPoint[] {
  const referencePoints: PlotPoint[] = [
    { pointLabel: "Neutral", x: 0.08, y: -0.04, size: 16, score: 0.34 },
    { pointLabel: "Interest", x: -0.24, y: -0.28, size: 18, score: 0.41 },
    { pointLabel: "Surprise", x: 0.34, y: -0.34, size: 17, score: 0.39 },
    { pointLabel: "Focus", x: -0.12, y: 0.16, size: 16, score: 0.38 },
  ]

  const anchors: Record<string, [number, number]> = {
    Calmness: [-0.3, 0.34],
    Determination: [0.2, 0.52],
    "Frustration risk": [0.54, 0.12],
  }

  const signalPoints = signals
    .filter((signal): signal is EmotionSignalTrack & { score: number } => signal.score !== null)
    .map((signal, index) => {
      const anchor = anchors[signal.label] ?? [index * 0.18 - 0.2, 0.2 - index * 0.16]

      return {
        pointLabel: signal.label,
        x: anchor[0],
        y: anchor[1],
        size: 18 + signal.score * 16,
        score: signal.score,
      }
    })

  return [...referencePoints, ...signalPoints]
}

function buildEmbeddingOption(signals: EmotionSignalTrack[]): EChartsOption {
  const points = buildEmbeddingPoints(signals)
  const referenceLabels = new Set(["Neutral", "Interest", "Surprise", "Focus"])

  return {
    animation: false,
    grid: {
      top: 16,
      right: 16,
      bottom: 16,
      left: 16,
    },
    tooltip: {
      formatter: (params: unknown) => {
        const point = (params as { data?: PlotPoint }).data

        if (!point) {
          return ""
        }

        return `${point.pointLabel}<br/>Score: ${point.score.toFixed(2)}`
      },
    },
    xAxis: {
      min: -1,
      max: 1,
      show: false,
    },
    yAxis: {
      min: -1,
      max: 1,
      show: false,
    },
    series: [
      {
        name: "Reference space",
        type: "scatter",
        data: points
          .filter((point) => referenceLabels.has(point.pointLabel))
          .map((point) => ({ ...point, value: [point.x, point.y, point.size] })),
        symbolSize: (value: number[]) => value[2],
        itemStyle: {
          color: "var(--muted)",
          opacity: 0.8,
        },
        label: {
          show: true,
          formatter: (params: unknown) =>
            ((params as { data?: PlotPoint }).data?.pointLabel ?? ""),
          position: "right",
          color: "var(--foreground)",
          backgroundColor: "var(--background)",
          borderColor: "var(--border)",
          borderWidth: 1,
          borderRadius: 999,
          padding: [4, 8],
        },
      },
      {
        name: "Emotion space",
        type: "scatter",
        data: points
          .filter((point) => !referenceLabels.has(point.pointLabel))
          .map((point) => ({ ...point, value: [point.x, point.y, point.size] })),
        symbolSize: (value: number[]) => value[2],
        itemStyle: {
          color: "var(--foreground)",
        },
        label: {
          show: true,
          formatter: (params: unknown) =>
            ((params as { data?: PlotPoint }).data?.pointLabel ?? ""),
          position: "right",
          color: "var(--foreground)",
          backgroundColor: "var(--background)",
          borderColor: "var(--border)",
          borderWidth: 1,
          borderRadius: 999,
          padding: [4, 8],
        },
      },
    ],
  }
}

export function EmbeddingPlot({ signals }: EmbeddingPlotProps) {
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Embedding plot</CardTitle>
        <CardDescription>
          A simple 2D emotion space built from the sample call signals.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <EChart
          className="h-[660px] min-h-[320px]"
          option={buildEmbeddingOption(signals)}
        />
      </CardContent>
    </Card>
  )
}
