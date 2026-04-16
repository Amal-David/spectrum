"use client"

import dynamic from "next/dynamic"
import type { EChartsOption } from "echarts"

import { cn } from "@/lib/utils"

const ReactECharts = dynamic(() => import("echarts-for-react"), {
  ssr: false,
})

type EChartProps = {
  option: EChartsOption
  className?: string
}

export function EChart({ option, className }: EChartProps) {
  return (
    <div className={cn("h-[320px] w-full", className)}>
      <ReactECharts
        lazyUpdate
        notMerge
        option={option}
        opts={{ renderer: "svg" }}
        style={{ height: "100%", width: "100%" }}
      />
    </div>
  )
}
