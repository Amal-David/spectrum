"use client"

import { EmbeddingPlot } from "@/components/app/embedding-plot"
import { EmotionGraph } from "@/components/app/emotion-graph"
import { WaveformPanel } from "@/components/app/waveform-panel"
import type { AnalysisDataset } from "@/lib/types"

type AnalysisWorkspaceProps = {
  dataset: AnalysisDataset
}

export function AnalysisWorkspace({ dataset }: AnalysisWorkspaceProps) {
  const primaryCall = dataset.calls[0]

  return (
    <div className="flex min-w-0 flex-col gap-6 p-4 md:p-6">
      <div className="grid min-w-0 gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(320px,0.95fr)]">
        <div className="flex min-w-0 flex-col gap-6">
          <WaveformPanel
            audioUrl={primaryCall?.audioUrl ?? "/demo-call.wav"}
            waveformDurationSeconds={primaryCall?.waveformDurationSeconds}
            waveformPeaks={primaryCall?.waveformPeaks}
          />
          <EmotionGraph
            durationSeconds={primaryCall?.waveformDurationSeconds}
            signals={dataset.emotionSignals}
          />
        </div>
        <EmbeddingPlot signals={dataset.emotionSignals} />
      </div>
    </div>
  )
}
