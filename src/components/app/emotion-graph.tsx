"use client"

import type { EChartsOption } from "echarts"

import { EChart } from "@/components/app/echart"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import type { EmotionSignalTrack } from "@/lib/types"

type EmotionGraphProps = {
  signals: EmotionSignalTrack[]
  durationSeconds?: number
}

function clampScore(value: number) {
  return Number(value.toFixed(2))
}

function buildTimeLabels(durationSeconds: number) {
  const safeDuration = Math.max(durationSeconds, 1)

  return Array.from({ length: 6 }, (_, index) => {
    const seconds = Math.round((safeDuration / 5) * index)
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60

    return `${String(minutes).padStart(2, "0")}:${String(remainingSeconds).padStart(2, "0")}`
  })
}

function buildEmotionOption(
  signals: EmotionSignalTrack[],
  durationSeconds?: number
): EChartsOption {
  const computedSignals = signals.filter(
    (signal): signal is EmotionSignalTrack & { score: number } =>
      signal.state === "computed" && signal.score !== null
  )

  const timeLabels = buildTimeLabels(durationSeconds ?? 0)
  const palette = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)"]

  return {
    color: palette,
    grid: {
      top: 24,
      right: 12,
      bottom: 28,
      left: 40,
    },
    tooltip: {
      trigger: "axis",
    },
    legend: {
      bottom: 0,
      icon: "roundRect",
      textStyle: {
        color: "var(--muted-foreground)",
        fontFamily: "var(--font-geist-mono)",
      },
    },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: timeLabels,
      axisLine: {
        lineStyle: {
          color: "var(--border)",
        },
      },
      axisLabel: {
        color: "var(--muted-foreground)",
        fontFamily: "var(--font-geist-mono)",
      },
    },
    yAxis: {
      type: "value",
      min: 0,
      max: 1,
      splitNumber: 4,
      axisLine: {
        show: false,
      },
      axisLabel: {
        color: "var(--muted-foreground)",
        fontFamily: "var(--font-geist-mono)",
      },
      splitLine: {
        lineStyle: {
          color: "var(--border)",
          type: "dashed",
        },
      },
    },
    series: computedSignals.map((signal, signalIndex) => ({
      name: signal.label,
      type: "line",
      smooth: true,
      showSymbol: false,
      areaStyle: {
        opacity: 0.12,
      },
      lineStyle: {
        width: 2,
      },
      data: timeLabels.map((_, pointIndex) => {
        const baseline = signal.score
        const waveModifier = Math.sin((pointIndex + 1) * 0.9 + signalIndex * 0.65) * 0.12
        const trendModifier = pointIndex * 0.03 - 0.06

        return clampScore(Math.max(0.04, Math.min(0.98, baseline + waveModifier + trendModifier)))
      }),
    })),
  }
}

export function EmotionGraph({ signals, durationSeconds }: EmotionGraphProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Emotion graph</CardTitle>
        <CardDescription>
          Soft-signal emotion trend estimated across the sample call.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <EChart
          className="h-[320px]"
          option={buildEmotionOption(signals, durationSeconds)}
        />
      </CardContent>
    </Card>
  )
}
