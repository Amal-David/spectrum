"use client"

import * as React from "react"
import WaveSurfer from "wavesurfer.js"
import Hover from "wavesurfer.js/dist/plugins/hover.esm.js"
import Minimap from "wavesurfer.js/dist/plugins/minimap.esm.js"
import Regions from "wavesurfer.js/dist/plugins/regions.esm.js"
import Timeline from "wavesurfer.js/dist/plugins/timeline.esm.js"
import { PauseIcon, PlayIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { WaveformTrack } from "@/lib/types"

type WaveformPanelProps = {
  audioUrl: string
  tracks: WaveformTrack[]
}

export function WaveformPanel({ audioUrl, tracks }: WaveformPanelProps) {
  const waveformRef = React.useRef<HTMLDivElement | null>(null)
  const timelineRef = React.useRef<HTMLDivElement | null>(null)
  const minimapRef = React.useRef<HTMLDivElement | null>(null)
  const wavesurferRef = React.useRef<WaveSurfer | null>(null)
  const [isPlaying, setIsPlaying] = React.useState(false)
  const [zoom, setZoom] = React.useState(40)

  React.useEffect(() => {
    if (!waveformRef.current || !timelineRef.current || !minimapRef.current) {
      return
    }

    const wavesurfer = WaveSurfer.create({
      container: waveformRef.current,
      url: audioUrl,
      height: 120,
      waveColor: "#d4d4d8",
      progressColor: "#18181b",
      cursorColor: "#18181b",
      barWidth: 2,
      barGap: 1,
      plugins: [
        Timeline.create({
          container: timelineRef.current,
        }),
        Minimap.create({
          container: minimapRef.current,
          height: 40,
          waveColor: "#d4d4d8",
          progressColor: "#71717a",
        }),
        Hover.create({
          lineColor: "#27272a",
          lineWidth: 1,
          labelBackground: "#18181b",
          labelColor: "#fafafa",
        }),
      ],
    })

    const regions = wavesurfer.registerPlugin(Regions.create())

    tracks
      .filter((track) =>
        ["pause", "overlap", "question", "behavior", "emotion"].includes(track.type)
      )
      .forEach((track) => {
        track.items.forEach((item) => {
          regions.addRegion({
            start: item.startMs / 1000,
            end: item.endMs / 1000,
            color:
              track.type === "overlap"
                ? "rgba(239, 68, 68, 0.18)"
                : track.type === "emotion"
                  ? "rgba(113, 113, 122, 0.15)"
                  : "rgba(161, 161, 170, 0.18)",
            drag: false,
            resize: false,
          })
        })
      })

    wavesurfer.on("play", () => setIsPlaying(true))
    wavesurfer.on("pause", () => setIsPlaying(false))
    wavesurfer.on("finish", () => setIsPlaying(false))
    wavesurferRef.current = wavesurfer

    return () => {
      wavesurfer.destroy()
      wavesurferRef.current = null
    }
  }, [audioUrl, tracks])

  React.useEffect(() => {
    wavesurferRef.current?.zoom(zoom)
  }, [zoom])

  const totalDurationMs = Math.max(
    1,
    ...tracks.flatMap((track) => track.items.map((item) => item.endMs))
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle>Timeline / player</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-2">
            <Button
              onClick={() => wavesurferRef.current?.playPause()}
              size="sm"
              variant="outline"
            >
              {isPlaying ? <PauseIcon data-icon="inline-start" /> : <PlayIcon data-icon="inline-start" />}
              {isPlaying ? "Pause" : "Play"}
            </Button>
          </div>
          <label className="flex items-center gap-3 text-sm text-muted-foreground">
            Zoom
            <input
              max={120}
              min={10}
              onChange={(event) => setZoom(Number(event.target.value))}
              type="range"
              value={zoom}
            />
          </label>
        </div>

        <div className="rounded-lg border p-3">
          <div ref={timelineRef} />
          <div ref={waveformRef} />
          <div ref={minimapRef} />
        </div>

        <div className="flex flex-col gap-3">
          {tracks.map((track) => (
            <div key={track.id} className="flex flex-col gap-1">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium">{track.label}</span>
                <span className="text-xs text-muted-foreground">
                  {track.type === "emotion" ? "experimental where shown" : "computed"}
                </span>
              </div>
              <div className="relative h-8 rounded-lg border bg-muted/30">
                {track.items.map((item) => {
                  const left = (item.startMs / totalDurationMs) * 100
                  const width = ((item.endMs - item.startMs) / totalDurationMs) * 100

                  return (
                    <button
                      key={item.id}
                      className="absolute top-1/2 h-5 -translate-y-1/2 rounded-md border bg-background px-2 text-xs"
                      onClick={() =>
                        wavesurferRef.current?.setTime(item.startMs / totalDurationMs)
                      }
                      style={{
                        left: `${left}%`,
                        width: `${Math.max(width, 3)}%`,
                      }}
                      type="button"
                    >
                      <span className="truncate">{item.label}</span>
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
