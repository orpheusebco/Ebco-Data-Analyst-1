'use client'

import dynamic from 'next/dynamic'

// Plotly touches `window` at import time, so it must be loaded client-side only.
// react-plotly.js is dynamically imported with SSR disabled; the static export
// therefore never evaluates it on the server.
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false })

interface PlotlySpec {
  data: unknown[]
  layout?: Record<string, unknown>
}

function isPlotlySpec(spec: unknown): spec is PlotlySpec {
  return (
    typeof spec === 'object' &&
    spec !== null &&
    Array.isArray((spec as { data?: unknown }).data) &&
    (spec as { data: unknown[] }).data.length > 0
  )
}

interface ChartViewProps {
  spec: unknown
}

export default function ChartView({ spec }: ChartViewProps) {
  if (!isPlotlySpec(spec)) return null

  const layout = {
    autosize: true,
    margin: { l: 48, r: 16, t: 32, b: 48 },
    ...(spec.layout ?? {}),
  }

  return (
    <div data-testid="chart-view" className="mt-3 overflow-hidden rounded-lg border border-slate-200 bg-white">
      <Plot
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        data={spec.data as any}
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        layout={layout as any}
        config={{
          responsive: true,
          displaylogo: false,
          // Keep the default modebar (includes hover, zoom and the toImage
          // export button); only strip the noisier selection tools.
          modeBarButtonsToRemove: ['lasso2d', 'select2d'],
        }}
        useResizeHandler
        style={{ width: '100%', height: '320px' }}
      />
    </div>
  )
}
