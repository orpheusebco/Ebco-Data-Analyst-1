'use client'

import dynamic from 'next/dynamic'
import { useEffect, useState } from 'react'

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

// Validated categorical palette (colorblind-safe; see dataviz skill). Assigned in
// fixed order, never cycled — Plotly draws each trace from the next slot.
const SERIES_LIGHT = ['#2a78d6', '#1baf7a', '#eda100', '#008300', '#4a3aa7', '#e34948', '#e87ba4', '#eb6834']
const SERIES_DARK = ['#3987e5', '#199e70', '#c98500', '#008300', '#9085e9', '#e66767', '#d55181', '#d95926']

interface Theme {
  colorway: string[]
  surface: string
  textPrimary: string
  textSecondary: string
  grid: string
  axisLine: string
  hoverBg: string
}

const THEMES: Record<'light' | 'dark', Theme> = {
  light: {
    colorway: SERIES_LIGHT,
    surface: 'rgba(0,0,0,0)', // transparent — inherit the card surface
    textPrimary: '#0b0b0b',
    textSecondary: '#52514e',
    grid: '#ecebe6',
    axisLine: '#d5d4cd',
    hoverBg: '#ffffff',
  },
  dark: {
    colorway: SERIES_DARK,
    surface: 'rgba(0,0,0,0)',
    textPrimary: '#ffffff',
    textSecondary: '#c3c2b7',
    grid: '#2c2c2a',
    axisLine: '#3d3d3a',
    hoverBg: '#242422',
  },
}

function useThemeMode(): 'light' | 'dark' {
  const [mode, setMode] = useState<'light' | 'dark'>('light')
  useEffect(() => {
    const read = (): 'light' | 'dark' => {
      const attr = document.documentElement.getAttribute('data-theme')
      if (attr === 'dark' || attr === 'light') return attr
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    }
    setMode(read())
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = () => setMode(read())
    mq.addEventListener('change', onChange)
    const obs = new MutationObserver(onChange)
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    return () => {
      mq.removeEventListener('change', onChange)
      obs.disconnect()
    }
  }, [])
  return mode
}

// Deep-merge the theme's axis styling under the spec's axis (so the LLM's axis
// titles win, but our gridlines/fonts apply).
function mergeAxis(themeAxis: Record<string, unknown>, specAxis: unknown): Record<string, unknown> {
  return { ...themeAxis, ...((specAxis as Record<string, unknown>) ?? {}) }
}

const FONT_FAMILY =
  'ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif'

interface ChartViewProps {
  spec: unknown
}

export default function ChartView({ spec }: ChartViewProps) {
  const mode = useThemeMode()
  if (!isPlotlySpec(spec)) return null
  const t = THEMES[mode]

  const specLayout = (spec.layout ?? {}) as Record<string, unknown>

  const axisBase = {
    gridcolor: t.grid,
    zerolinecolor: t.axisLine,
    linecolor: t.axisLine,
    tickfont: { color: t.textSecondary, size: 12 },
    titlefont: { color: t.textSecondary, size: 13 },
    automargin: true,
  }

  const layout = {
    autosize: true,
    margin: { l: 56, r: 20, t: 44, b: 52 },
    colorway: t.colorway,
    paper_bgcolor: t.surface,
    plot_bgcolor: t.surface,
    font: { family: FONT_FAMILY, color: t.textSecondary, size: 12 },
    title: {
      font: { family: FONT_FAMILY, color: t.textPrimary, size: 15 },
      x: 0.02,
      xanchor: 'left' as const,
      ...(typeof specLayout.title === 'string'
        ? { text: specLayout.title }
        : ((specLayout.title as Record<string, unknown>) ?? {})),
    },
    hoverlabel: {
      bgcolor: t.hoverBg,
      bordercolor: t.axisLine,
      font: { family: FONT_FAMILY, color: t.textPrimary, size: 12 },
    },
    legend: {
      font: { color: t.textSecondary, size: 12 },
      orientation: 'h' as const,
      yanchor: 'bottom' as const,
      y: 1.02,
      xanchor: 'left' as const,
      x: 0,
    },
    bargap: 0.28,
    ...specLayout,
    // Re-apply deep-merged pieces after the spread so styling is not clobbered.
    xaxis: mergeAxis(axisBase, specLayout.xaxis),
    yaxis: mergeAxis(axisBase, specLayout.yaxis),
    title_merged: undefined,
  } as Record<string, unknown>
  delete layout.title_merged

  // Give bar marks a thin surface-colored separator so adjacent bars read cleanly.
  const data = (spec.data as Array<Record<string, unknown>>).map((trace) => {
    if (trace.type === 'bar') {
      return {
        ...trace,
        marker: {
          line: { width: 1, color: mode === 'dark' ? '#1a1a19' : '#fcfcfb' },
          ...((trace.marker as Record<string, unknown>) ?? {}),
        },
      }
    }
    return trace
  })

  return (
    <div
      data-testid="chart-view"
      className="mt-3 overflow-hidden rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900"
    >
      <Plot
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        data={data as any}
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
        style={{ width: '100%', height: '340px' }}
      />
    </div>
  )
}
