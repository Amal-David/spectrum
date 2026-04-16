"use client"

import * as React from "react"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

type WaveformPanelProps = {
  audioUrl: string
  waveformDurationSeconds?: number
  waveformPeaks?: number[][]
}

function formatTime(seconds: number) {
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return "00:00"
  }

  const safeSeconds = Math.floor(seconds)
  const minutes = Math.floor(safeSeconds / 60)
  const remainingSeconds = safeSeconds % 60

  return `${String(minutes).padStart(2, "0")}:${String(remainingSeconds).padStart(2, "0")}`
}

export function WaveformPanel({
  audioUrl,
  waveformDurationSeconds,
  waveformPeaks,
}: WaveformPanelProps) {
  const audioRef = React.useRef<HTMLAudioElement | null>(null)
  const [currentTimeSeconds, setCurrentTimeSeconds] = React.useState(0)
  const [durationSeconds, setDurationSeconds] = React.useState(waveformDurationSeconds ?? 0)

  const peaks = waveformPeaks?.[0] ?? []
  const progressRatio =
    durationSeconds > 0 ? Math.min(currentTimeSeconds / durationSeconds, 1) : 0
  const playedBarCount =
    peaks.length > 0 ? Math.floor(progressRatio * peaks.length) : 0

  React.useEffect(() => {
    setDurationSeconds(waveformDurationSeconds ?? 0)
  }, [waveformDurationSeconds])

  return (
    <Card>
      <CardHeader>
        <CardTitle>Waveform</CardTitle>
        <CardDescription>
          Audio preview rendered from the sample call file.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="rounded-lg border bg-muted/20 p-4">
          {peaks.length > 0 ? (
            <svg
              aria-hidden="true"
              className="h-36 w-full text-foreground"
              data-testid="waveform-fallback"
              preserveAspectRatio="none"
              viewBox={`0 0 ${peaks.length} 100`}
            >
              {peaks.map((peak, index) => {
                const normalizedHeight = Math.max(Math.abs(peak) * 45, 1.5)
                const y = 50 - normalizedHeight
                const height = normalizedHeight * 2
                const isPlayed = index <= playedBarCount

                return (
                  <rect
                    key={`${index}-${peak}`}
                    fill="currentColor"
                    height={height}
                    opacity={isPlayed ? 0.95 : 0.22}
                    rx={0.45}
                    width={0.8}
                    x={index + 0.1}
                    y={y}
                  />
                )
              })}
            </svg>
          ) : (
            <div className="flex h-36 items-center justify-center rounded-md bg-muted text-sm text-muted-foreground">
              Waveform preview unavailable.
            </div>
          )}
        </div>

        <div className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
          <span className="font-mono tabular-nums">{formatTime(currentTimeSeconds)}</span>
          <span className="font-mono tabular-nums">{formatTime(durationSeconds)}</span>
        </div>

        <audio
          aria-label="Audio playback"
          controls
          onLoadedMetadata={(event) => {
            setDurationSeconds(event.currentTarget.duration || waveformDurationSeconds || 0)
          }}
          onTimeUpdate={(event) => {
            setCurrentTimeSeconds(event.currentTarget.currentTime)
          }}
          preload="metadata"
          ref={audioRef}
          src={audioUrl}
        />
      </CardContent>
    </Card>
  )
}
