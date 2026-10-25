import { useCallback, useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import './App.css'

const API_URL = 'http://127.0.0.1:8000'

const numberFormatter = new Intl.NumberFormat('en-US')
const compactFormatter = new Intl.NumberFormat('en-US', {
  notation: 'compact',
  maximumFractionDigits: 2
})

// format sql values for display without changing the api response
const sqlNumberFormatter = new Intl.NumberFormat('en-US', {
  useGrouping: true,
  maximumFractionDigits: 2
})
const moneyFormatter = new Intl.NumberFormat('en-US', {
  useGrouping: true,
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})

function isMoneyColumn(column) {
  return /(?:revenue|price|amount|sales|cost|profit|freight|payment|value_brl)/i.test(String(column))
}

function formatSqlCell(column, value) {
  if (value === null || value === undefined) return 'NULL'
  const columnName = String(column).toLowerCase()
  if (columnName === 'month' && typeof value === 'string') {
    const match = value.match(/^(\d{4})-(\d{2})-01(?:T00:00:00(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?$/)
    if (match) return `${match[1]}-${match[2]}`
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    if (isMoneyColumn(column)) return moneyFormatter.format(value)
    if (/(?:count|quantity|total|sum|average|avg)/i.test(columnName)) {
      return sqlNumberFormatter.format(value)
    }
  }
  return String(value)
}

// Hide narrative Markdown tables that repeat structured SQL results.
// Matching tolerates extra rows (e.g. empty months), different month labels,
// escaped pipe characters, and missing outer pipes.
function removeDuplicatedSqlTable(answer, tables) {
  if (!answer || !Array.isArray(tables) || tables.length === 0) return answer

  const lines = answer.split(/\r?\n/)
  const output = []
  const normalize = (line) => line.trim().replace(/\\\|/g, '|')
  const cellsOf = (line) => normalize(line).replace(/^\|/, '').replace(/\|$/, '')
    .split('|').map((cell) => cell.trim())
  const isTableLine = (line) => normalize(line).includes('|')
  const isSeparator = (line) => {
    const cells = cellsOf(line)
    return cells.length >= 2 && cells.every((cell) => /^:?-{3,}:?$/.test(cell))
  }
  const numericValue = (value) => {
    if (value === null || value === undefined || typeof value === 'boolean') return null
    const str = String(value).replace(/,/g, '').trim()
    if (!/^-?\d+(?:\.\d+)?$/.test(str)) return null
    const n = Number(str)
    return Number.isFinite(n) ? n : null
  }
  const monetaryColumns = (table) => (table.columns || [])
    .filter((column) => isMoneyColumn(column))

  for (let i = 0; i < lines.length;) {
    if (!isTableLine(lines[i]) || i + 1 >= lines.length || !isSeparator(lines[i + 1])) {
      output.push(lines[i])
      i++
      continue
    }

    let end = i + 2
    while (end < lines.length && isTableLine(lines[end])) end++
    const markdownRows = lines.slice(i + 2, end).map(cellsOf)

    const duplicate = tables.some((table) => {
      if (!Array.isArray(table.rows) || table.rows.length < 2 || markdownRows.length < 2) {
        return false
      }
      // Compare monetary results first, since month labels may be formatted
      // differently (e.g. 'Jan' versus '2018-01').
      const columns = monetaryColumns(table)
      if (columns.length === 0) return false

      const sqlValues = table.rows.flatMap((row) => columns
        .map((column) => numericValue(row[column]))
        .filter((value) => value !== null))
      if (sqlValues.length < 2) return false

      const narrativeValues = markdownRows.flatMap((row) => row
        .map(numericValue).filter((value) => value !== null))
      const remaining = [...narrativeValues]
      let matches = 0
      for (const value of sqlValues) {
        const index = remaining.findIndex((candidate) =>
          Math.abs(value - candidate) < 0.000001)
        if (index >= 0) {
          matches++
          remaining.splice(index, 1)
        }
      }
      // All (or nearly all) database monetary values must occur in the
      // narrative table. Extra narrative rows are permitted.
      return matches >= 2 && matches / sqlValues.length >= 0.8
    })

    if (!duplicate) output.push(...lines.slice(i, end))
    i = end
  }

  return output.join('\n').replace(/\n{3,}/g, '\n\n').trim()
}

// Export the original SQL result, not the rounded values shown in the UI.
// Escape CSV characters and prevent spreadsheet formula execution.
function csvCell(value) {
  if (value === null || value === undefined) return ''
  let text = String(value)
  if (/^[\s\u0000-\u001f]*[=+@-]/.test(text) && typeof value === 'string') {
    text = "'" + text
  }
  return `"${text.replace(/"/g, '""')}"`
}

function downloadSqlCsv(table, tableIndex) {
  const columns = Array.isArray(table.columns) ? table.columns : []
  const rows = Array.isArray(table.rows) ? table.rows : []
  if (columns.length === 0) return

  const csvRows = [
    columns.map(csvCell).join(','),
    ...rows.map((row) => columns.map((column) => csvCell(row[column])).join(','))
  ]
  // UTF-8 BOM improves Excel compatibility with non-ASCII characters.
  const blob = new Blob(['\uFEFF', csvRows.join('\r\n')], {
    type: 'text/csv;charset=utf-8;'
  })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `database_results_${tableIndex + 1}.csv`
  document.body.appendChild(link)
  link.click()
  link.remove()
  // Delay revocation to allow the browser to start the download.
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}


// Use structured SQL data to draw a chart without extra dependencies.
// Charts are offered only when a categorical column and a numeric measure exist.
function isMonthColumn(column) {
  return /^(month|order_month|year_month|month_year|period)$/i.test(String(column))
}

function buildChartData(table) {
  const columns = Array.isArray(table?.columns) ? table.columns : []
  const rows = Array.isArray(table?.rows) ? table.rows : []
  if (columns.length < 2 || rows.length < 2 || rows.length > 60) return null

  const numericColumns = columns.filter((column) => {
    const values = rows.map((row) => row[column]).filter((value) => value !== null && value !== undefined)
    return values.length >= 2 && values.every((value) =>
      (typeof value === 'number' && Number.isFinite(value)) ||
      (typeof value === 'string' && value.trim() !== '' && Number.isFinite(Number(value)))
    )
  })
  const valueColumn = numericColumns.find(isMoneyColumn) || numericColumns[0]
  const categoryColumn = columns.find((column) => !numericColumns.includes(column))
  if (!valueColumn || !categoryColumn) return null

  // Normalize month labels from PostgreSQL timestamps and YYYY-MM strings.
  // Keep original table values untouched for CSV export.
  const isMonthCategory = isMonthColumn(categoryColumn)
  const points = rows.map((row) => {
    const rawLabel = row[categoryColumn]
    const formattedLabel = formatSqlCell(categoryColumn, rawLabel)
    const monthMatch = isMonthCategory && rawLabel != null
      ? String(rawLabel).trim().match(/^(\d{4})-(0[1-9]|1[0-2])(?:-\d{2})?(?:[T\s].*)?$/)
      : null
    return {
      label: monthMatch ? `${monthMatch[1]}-${monthMatch[2]}` : formattedLabel,
      value: row[valueColumn] === null || row[valueColumn] === undefined
        ? null : Number(row[valueColumn])
    }
  })
  if (points.filter((point) => point.value !== null && Number.isFinite(point.value)).length < 2) return null
  return { points, valueColumn, categoryColumn }
}

function SqlInteractiveChart({ table }) {
  const [chartType, setChartType] = useState('bar')
  const chartSvgRef = useRef(null)
  const [exportError, setExportError] = useState('')
  const [startPeriod, setStartPeriod] = useState('')
  const [endPeriod, setEndPeriod] = useState('')
  const data = buildChartData(table)
  if (!data) return null

  const { points: allPoints, valueColumn, categoryColumn } = data
  // Only offer a period filter when every category is a sortable YYYY-MM label.
  const hasPeriods = isMonthColumn(categoryColumn) && allPoints.every((point) =>
    /^\d{4}-(0[1-9]|1[0-2])$/.test(String(point.label))
  )
  const periods = hasPeriods
    ? [...new Set(allPoints.map((point) => String(point.label)))].sort()
    : []
  const effectiveStart = periods.includes(startPeriod) ? startPeriod : periods[0]
  const effectiveEnd = periods.includes(endPeriod) ? endPeriod : periods[periods.length - 1]
  const points = hasPeriods
    ? allPoints.filter((point) => point.label >= effectiveStart && point.label <= effectiveEnd)
    : allPoints
  const invalidPeriod = hasPeriods && effectiveStart > effectiveEnd

  const width = 760
  const height = 320
  const margin = { top: 24, right: 22, bottom: 72, left: 74 }
  const plotWidth = width - margin.left - margin.right
  const plotHeight = height - margin.top - margin.bottom
  const values = points.map((point) => point.value).filter((value) => value !== null)
  const minValue = Math.min(0, ...values)
  const maxValue = Math.max(0, ...values)
  const range = maxValue - minValue || 1
  const yFor = (value) => margin.top + (maxValue - value) / range * plotHeight
  const zeroY = yFor(0)
  const step = plotWidth / Math.max(1, points.length)
  const compact = (value) => compactFormatter.format(value)
  const formatValue = (value) => isMoneyColumn(valueColumn)
    ? moneyFormatter.format(value)
    : sqlNumberFormatter.format(value)
  const labelStep = Math.max(1, Math.ceil(points.length / 12))
  async function downloadChartPng() {
    const svgElement = chartSvgRef.current
    if (!svgElement || invalidPeriod || points.length === 0) return
    setExportError('')

    const exportWidth = 1520
    const exportHeight = 640
    const svgClone = svgElement.cloneNode(true)
    svgClone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
    svgClone.setAttribute('width', String(exportWidth))
    svgClone.setAttribute('height', String(exportHeight))
    // Keep SVG coordinates consistent while exporting a high-resolution image.
    svgClone.setAttribute('viewBox', `0 0 ${width} ${height}`)
    const svgText = new XMLSerializer().serializeToString(svgClone)
    const svgBlob = new Blob([svgText], { type: 'image/svg+xml;charset=utf-8' })
    const svgUrl = URL.createObjectURL(svgBlob)

    try {
      const img = new Image()
      await new Promise((resolve, reject) => {
        img.onload = resolve
        img.onerror = () => reject(new Error('Could not render the chart image.'))
        img.src = svgUrl
      })

      const canvas = document.createElement('canvas')
      canvas.width = exportWidth
      canvas.height = exportHeight
      const context = canvas.getContext('2d')
      if (!context) throw new Error('Canvas is not available.')
      context.fillStyle = '#ffffff'
      context.fillRect(0, 0, exportWidth, exportHeight)
      context.drawImage(img, 0, 0, exportWidth, exportHeight)

      const pngBlob = await new Promise((resolve, reject) => {
        canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error('PNG export failed.')), 'image/png')
      })
      const pngUrl = URL.createObjectURL(pngBlob)
      const link = document.createElement('a')
      link.href = pngUrl
      link.download = `analysis_chart_${chartType}${hasPeriods ? `_${effectiveStart}_to_${effectiveEnd}` : ''}.png`
      document.body.appendChild(link)
      link.click()
      link.remove()
      setTimeout(() => URL.revokeObjectURL(pngUrl), 1000)
    } catch (error) {
      setExportError(error.message || 'Could not download chart.')
    } finally {
      URL.revokeObjectURL(svgUrl)
    }
  }


  const segments = []
  let currentSegment = []
  points.forEach((point, index) => {
    if (point.value === null || !Number.isFinite(point.value)) {
      if (currentSegment.length) segments.push(currentSegment)
      currentSegment = []
    } else {
      currentSegment.push(`${margin.left + (index + 0.5) * step},${yFor(point.value)}`)
    }
  })
  if (currentSegment.length) segments.push(currentSegment)

  return (
    <div className="sql-interactive-chart">
      <div className="sql-chart-heading">
        <div>
          <strong>Interactive Visualization</strong>
          <span>{valueColumn} by {categoryColumn}</span>
        </div>
        <div className="sql-chart-actions">
          <div className="sql-chart-switch" role="group" aria-label="Chart type">
            <button type="button" className={chartType === 'bar' ? 'selected' : ''}
              aria-pressed={chartType === 'bar'} onClick={() => setChartType('bar')}>Bar Chart</button>
            <button type="button" className={chartType === 'line' ? 'selected' : ''}
              aria-pressed={chartType === 'line'} onClick={() => setChartType('line')}>Line Chart</button>
          </div>
          <button type="button" className="sql-chart-download" disabled={invalidPeriod} onClick={downloadChartPng}>
            ↓ Download PNG
          </button>
        </div>
      </div>
      {hasPeriods && (
        <div className="sql-chart-period-filter">
          <span className="sql-chart-filter-title">Period</span>
          <label>From
            <select value={effectiveStart} onChange={(event) => setStartPeriod(event.target.value)}>
              {periods.map((period) => <option key={period} value={period}>{period}</option>)}
            </select>
          </label>
          <label>To
            <select value={effectiveEnd} onChange={(event) => setEndPeriod(event.target.value)}>
              {periods.map((period) => <option key={period} value={period}>{period}</option>)}
            </select>
          </label>
          <button type="button" className="sql-chart-reset"
            onClick={() => { setStartPeriod(''); setEndPeriod('') }}>
            Reset
          </button>
          <span className="sql-chart-period-count">{points.length} months shown</span>
        </div>
      )}
      {invalidPeriod && <p className="sql-chart-export-error" role="alert">The start month must be before or equal to the end month.</p>}
      {!invalidPeriod && <div className="sql-chart-scroll">
        <svg ref={chartSvgRef} viewBox={`0 0 ${width} ${height}`} role="img"
          aria-label={`${chartType} chart showing ${valueColumn} by ${categoryColumn}`}>
          {Array.from({ length: 5 }, (_, i) => {
            const tick = minValue + (range * i) / 4
            const y = yFor(tick)
            return (
              <g key={i}>
                <line x1={margin.left} x2={width - margin.right} y1={y} y2={y}
                  stroke="#e8edf5" strokeDasharray="4 4" />
                <text x={margin.left - 12} y={y + 4} textAnchor="end" fontSize="12" fill="#64748b">
                  {compact(tick)}
                </text>
              </g>
            )
          })}
          <line x1={margin.left} x2={width - margin.right} y1={zeroY} y2={zeroY} stroke="#94a3b8" />
          {points.map((point, index) => {
            const x = margin.left + (index + 0.5) * step
            const valid = point.value !== null && Number.isFinite(point.value)
            const y = valid ? yFor(point.value) : zeroY
            return (
              <g key={index}>
                {chartType === 'bar' && valid && (
                  <rect x={x - Math.max(3, step * 0.34)} y={Math.min(y, zeroY)}
                    width={Math.max(6, step * 0.68)} height={Math.max(1, Math.abs(zeroY - y))}
                    rx="3" fill="#5368e8">
                    <title>{`${point.label}: ${formatValue(point.value)}`}</title>
                  </rect>
                )}
                {index % labelStep === 0 && (
                  <text x={x} y={height - margin.bottom + 18} fontSize="11" fill="#64748b"
                    textAnchor="end" transform={`rotate(-35 ${x} ${height - margin.bottom + 18})`}>
                    {String(point.label).slice(0, 18)}
                  </text>
                )}
              </g>
            )
          })}
          {chartType === 'line' && (
            <g>
              {segments.map((segment, index) => (
                <polyline key={index} points={segment.join(' ')} fill="none"
                  stroke="#5368e8" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />
              ))}
              {points.map((point, index) => point.value !== null && Number.isFinite(point.value) && (
                <circle key={index} cx={margin.left + (index + 0.5) * step}
                  cy={yFor(point.value)} r="5" fill="#5368e8" stroke="white" strokeWidth="2">
                  <title>{`${point.label}: ${formatValue(point.value)}`}</title>
                </circle>
              ))}
            </g>
          )}
        </svg>
      </div>}
      <div className="sql-chart-footnote">Hover over a bar or point to see its exact value. Missing values are not treated as zero.</div>
      {exportError && <p className="sql-chart-export-error" role="alert">{exportError}</p>}
    </div>
  )
}

function App() {
  const [activePage, setActivePage] = useState('overview')
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  // One conversation ID per browser tab; refreshed tabs start a new session.
  const conversationIdRef = useRef(crypto.randomUUID())
  const [loading, setLoading] = useState(false)

  const [stats, setStats] = useState(null)
  const [statsLoading, setStatsLoading] = useState(true)
  const [statsError, setStatsError] = useState(false)

  const [reports, setReports] = useState([])
  const [reportsLoading, setReportsLoading] = useState(false)
  const [reportsError, setReportsError] = useState('')

  const [monitoring, setMonitoring] = useState(null)
  const [monitoringLoading, setMonitoringLoading] = useState(false)
  const [monitoringError, setMonitoringError] = useState('')
  const [monitoringCheckedAt, setMonitoringCheckedAt] = useState(null)

  const chatEndRef = useRef(null)
  const monitoringRequestRef = useRef(null)

  useEffect(() => {
    const controller = new AbortController()

    async function loadDashboardStats() {
      try {
        const response = await fetch(`${API_URL}/dashboard/stats`, {
          signal: controller.signal
        })

        if (!response.ok) {
          throw new Error('Failed to load dashboard statistics')
        }

        const data = await response.json()
        setStats(data)
        setStatsError(false)
      } catch (error) {
        if (error.name !== 'AbortError') {
          setStatsError(true)
        }
      } finally {
        if (!controller.signal.aborted) {
          setStatsLoading(false)
        }
      }
    }

    loadDashboardStats()

    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (activePage !== 'reports') return

    const controller = new AbortController()

    async function loadReports() {
      setReportsLoading(true)
      setReportsError('')

      try {
        const response = await fetch(`${API_URL}/reports/list`, {
          signal: controller.signal
        })

        if (!response.ok) {
          throw new Error('Unable to load reports')
        }

        const data = await response.json()
        setReports(data.reports || [])
      } catch (error) {
        if (error.name !== 'AbortError') {
          setReportsError(error.message)
        }
      } finally {
        if (!controller.signal.aborted) {
          setReportsLoading(false)
        }
      }
    }

    loadReports()

    return () => controller.abort()
  }, [activePage])

  const loadMonitoring = useCallback(async () => {
    if (monitoringRequestRef.current) return

    const controller = new AbortController()
    monitoringRequestRef.current = controller

    setMonitoringLoading(true)
    setMonitoringError('')

    try {
      const response = await fetch(`${API_URL}/monitoring/status`, {
        signal: controller.signal,
        cache: 'no-store'
      })

      if (!response.ok) {
        throw new Error('Unable to load monitoring status')
      }

      const data = await response.json()

      if (!controller.signal.aborted) {
        setMonitoring(data)
        setMonitoringCheckedAt(new Date())
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        setMonitoringError(error.message)
      }
    } finally {
      if (monitoringRequestRef.current === controller) {
        monitoringRequestRef.current = null
        setMonitoringLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    if (activePage !== 'monitoring') return

    loadMonitoring()

    const interval = setInterval(() => {
      loadMonitoring()
    }, 30000)

    return () => {
      clearInterval(interval)

      if (monitoringRequestRef.current) {
        monitoringRequestRef.current.abort()
        monitoringRequestRef.current = null
      }
    }
  }, [activePage, loadMonitoring])

  useEffect(() => {
    if (activePage === 'overview' || activePage === 'assistant') {
      chatEndRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest'
      })
    }
  }, [messages, loading, activePage])

  const statCards = [
    {
      label: 'Total Revenue',
      value: stats
        ? `${stats.currency === 'BRL' ? 'R$ ' : `${stats.currency} `}${compactFormatter.format(stats.total_revenue)}`
        : statsLoading ? 'Loading...' : 'Unavailable',
      description: 'Product revenue'
    },
    {
      label: 'Total Orders',
      value: stats
        ? numberFormatter.format(stats.total_orders)
        : statsLoading ? 'Loading...' : 'Unavailable',
      description: 'E-commerce orders'
    },
    {
      label: 'Total Products',
      value: stats
        ? numberFormatter.format(stats.total_products)
        : statsLoading ? 'Loading...' : 'Unavailable',
      description: 'Available products'
    },
    {
      label: 'Total Sellers',
      value: stats
        ? numberFormatter.format(stats.total_sellers)
        : statsLoading ? 'Loading...' : 'Unavailable',
      description: 'Marketplace sellers'
    }
  ]

  async function handleSubmit(event) {
    event.preventDefault()

    const currentQuestion = question.trim()
    if (!currentQuestion || loading) return

    setMessages((previous) => [
      ...previous,
      { role: 'user', content: currentQuestion }
    ])

    setQuestion('')
    setLoading(true)

    try {
      const response = await fetch(`${API_URL}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: currentQuestion,
          conversation_id: conversationIdRef.current
        })
      })

      if (!response.ok) {
        let errorMessage = `API request failed: ${response.status}`

        try {
          const errorData = await response.json()

          if (typeof errorData.detail === 'string') {
            errorMessage = errorData.detail
          }
        } catch {
          errorMessage = `API request failed: ${response.status}`
        }

        throw new Error(errorMessage)
      }

      const data = await response.json()

      setMessages((previous) => [
        ...previous,
        {
          role: 'assistant',
          content: data.answer || 'No analysis was returned.',
          charts: data.charts || [],
          reports: data.reports || [],
          tables: data.tables || []
        }
      ])
    } catch (error) {
      setMessages((previous) => [
        ...previous,
        {
          role: 'assistant',
          content: `Unable to complete the analysis: ${error.message}`,
          charts: [],
          reports: [],
          tables: []
        }
      ])
    } finally {
      setLoading(false)
    }
  }

  function formatDate(timestamp) {
    return new Date(timestamp * 1000).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  function renderAssistant() {
    return (
      <section className="assistant-panel">
        <div className="panel-header">
          <div>
            <h2>AI Analysis Assistant</h2>
            <p>Ask questions about your database.</p>
          </div>

          <span className="agent-status">
            {loading ? '● Agent Working' : '● Agent Ready'}
          </span>
        </div>

        <div className="chat-messages">
          {messages.length === 0 && !loading && (
            <div className="welcome-message">
              <div className="welcome-icon">✦</div>
              <h3>What would you like to analyze?</h3>
              <p>
                Ask about revenue, customers, products,
                delivery performance or business trends.
              </p>
            </div>
          )}

          {messages.map((message, index) => (
            <div key={index} className={`message ${message.role}`}>
              <div className="message-content">
                {message.role === 'assistant' ? (
                  <ReactMarkdown>{removeDuplicatedSqlTable(message.content, message.tables)}</ReactMarkdown>
                ) : (
                  message.content
                )}
              </div>

              {message.tables?.length > 0 && (
                <div className="message-tables">
                  {message.tables.map((table, tableIndex) => (
                    <div className="sql-table-card" key={tableIndex}>
                      <div className="sql-table-header">
                        <span>Database Results {message.tables.length > 1 ? `${tableIndex + 1}` : ''}</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <span>{table.row_count} rows</span>
                          <button
                            type="button"
                            onClick={() => downloadSqlCsv(table, tableIndex)}
                            aria-label="Download database results as CSV"
                            style={{
                              border: '1px solid #94a3b8',
                              borderRadius: '6px',
                              padding: '6px 10px',
                              background: 'transparent',
                              color: 'inherit',
                              cursor: 'pointer',
                              fontSize: '12px',
                              fontWeight: 600
                            }}
                          >
                            ↓ Download CSV
                          </button>
                        </div>
                      </div>

                      <div className="sql-table-scroll">
                        <table className="sql-results-table">
                          <thead>
                            <tr>
                              {table.columns.map((column) => (
                                <th key={column}>{column}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {table.rows.map((row, rowIndex) => (
                              <tr key={rowIndex}>
                                {table.columns.map((column) => (
                                  <td key={column}>
                                    {formatSqlCell(column, row[column])}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <SqlInteractiveChart table={table} />
                    </div>
                  ))}
                </div>
              )}

              {message.charts?.length > 0 && (
                <div className="message-charts">
                  {message.charts.map((chart, chartIndex) => (
                    <div
                      className="chart-container"
                      key={`${chart}-${chartIndex}`}
                    >
                      <div className="chart-header">
                        <span>Analysis Chart</span>
                      </div>

                      <img
                        src={`${API_URL}${chart}`}
                        alt="Generated data analysis chart"
                        className="analysis-chart"
                      />

                      <a
                        href={`${API_URL}${chart}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="chart-link"
                      >
                        Open Chart ↗
                      </a>
                    </div>
                  ))}
                </div>
              )}

              {message.reports?.length > 0 && (
                <div className="message-reports">
                  {message.reports.map((report, reportIndex) => (
                    <a
                      key={`${report}-${reportIndex}`}
                      href={`${API_URL}${report}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="report-link"
                    >
                      <span>▤</span>
                      <span>Open Analysis Report</span>
                      <span>↗</span>
                    </a>
                  ))}
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="message assistant">
              <div className="loading-indicator">
                <span className="loading-dot"></span>
                Analyzing your data...
              </div>
            </div>
          )}

          <div ref={chatEndRef}></div>
        </div>

        <form className="chat-form" onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder={
              loading
                ? 'Agent is analyzing...'
                : 'Ask your AI Data Analyst...'
            }
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            disabled={loading}
          />

          <button
            type="submit"
            disabled={loading || !question.trim()}
          >
            {loading ? 'Analyzing...' : 'Send →'}
          </button>
        </form>
      </section>
    )
  }

  return (
    <div className="dashboard">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">✦</div>
          <div>
            <h2>AI Data Analyst</h2>
            <p>Intelligent Analytics</p>
          </div>
        </div>

        <nav className="navigation">
          <button
            className={`nav-item ${activePage === 'overview' ? 'active' : ''}`}
            onClick={() => setActivePage('overview')}
          >
            ◈ Overview
          </button>

          <button
            className={`nav-item ${activePage === 'assistant' ? 'active' : ''}`}
            onClick={() => setActivePage('assistant')}
          >
            ◉ AI Assistant
          </button>

          <button
            className={`nav-item ${activePage === 'reports' ? 'active' : ''}`}
            onClick={() => setActivePage('reports')}
          >
            ▥ Reports
          </button>

          <button
            className={`nav-item ${activePage === 'monitoring' ? 'active' : ''}`}
            onClick={() => setActivePage('monitoring')}
          >
            ◷ Monitoring
          </button>
        </nav>

        <div className="sidebar-footer">
          <span className="status-dot"></span>
          {statsLoading
            ? 'Checking Database...'
            : statsError
              ? 'Database Unavailable'
              : 'PostgreSQL Connected'}
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="eyebrow">ANALYTICS WORKSPACE</p>

            <h1>
              {activePage === 'reports'
                ? 'Analysis Reports'
                : activePage === 'monitoring'
                  ? 'System Monitoring'
                  : activePage === 'assistant'
                    ? 'AI Assistant'
                    : 'Dashboard Overview'}
            </h1>

            <p className="subtitle">
              {activePage === 'reports'
                ? 'Explore reports generated by your AI agent.'
                : activePage === 'monitoring'
                  ? 'Monitor the health of your analytics workspace.'
                  : 'Explore your data with an intelligent AI agent.'}
            </p>
          </div>

          <div className="topbar-badge">
            AI Agent Workspace
          </div>
        </header>

        {activePage === 'overview' && (
          <section className="stats-grid">
            {statCards.map((card) => (
              <div className="stat-card" key={card.label}>
                <p>{card.label}</p>
                <h2>{card.value}</h2>
                <span>{card.description}</span>
              </div>
            ))}
          </section>
        )}

        {(activePage === 'overview' || activePage === 'assistant') &&
          renderAssistant()}

        {activePage === 'reports' && (
          <section className="reports-page">
            <div className="reports-heading">
              <div>
                <h2>Generated Reports</h2>
                <p>Reports saved by your AI Data Analyst Agent.</p>
              </div>

              <span className="reports-count">
                {reports.length} Reports
              </span>
            </div>

            {reportsLoading && (
              <div className="reports-empty">
                Loading reports...
              </div>
            )}

            {reportsError && (
              <div className="reports-empty">
                {reportsError}
              </div>
            )}

            {!reportsLoading && !reportsError && reports.length === 0 && (
              <div className="reports-empty">
                No reports generated yet.
              </div>
            )}

            {!reportsLoading && !reportsError && reports.length > 0 && (
              <div className="reports-grid">
                {reports.map((report) => (
                  <div className="report-card" key={report.filename}>
                    <div className="report-card-icon">▤</div>
                    <h3>{report.name}</h3>

                    <p className="report-card-date">
                      {formatDate(report.created_at)}
                    </p>

                    <div className="report-card-footer">
                      <span>{report.size_kb} KB · Markdown</span>

                      <a
                        href={`${API_URL}${report.url}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="report-open-button"
                      >
                        Open Report ↗
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {activePage === 'monitoring' && (
          <section className="reports-page">
            <div className="reports-heading">
              <div>
                <h2>System Health</h2>
                <p>Live status of your analytics infrastructure.</p>
              </div>

              <div className="monitoring-actions">
                <span className="reports-count">
                  System Monitoring
                </span>

                <button
                  type="button"
                  className="monitoring-refresh-button"
                  disabled={monitoringLoading}
                  onClick={loadMonitoring}
                >
                  {monitoringLoading
                    ? 'Refreshing...'
                    : '↻ Refresh Status'}
                </button>
              </div>
            </div>

            {monitoringLoading && !monitoring && (
              <div className="reports-empty">
                Checking system status...
              </div>
            )}

            {monitoringError && (
              <div className="reports-empty">
                {monitoringError}
              </div>
            )}

            {monitoring && (
              <>
                <div className="monitoring-grid">
                  <div className="monitoring-card">
                    <div className="monitoring-icon">◉</div>
                    <h3>FastAPI Server</h3>

                    <span
                      className={`monitoring-status ${monitoring.api}`}
                    >
                      {monitoring.api === 'online'
                        ? '● Online'
                        : '● Offline'}
                    </span>

                    <p>Backend API availability</p>
                  </div>

                  <div className="monitoring-card">
                    <div className="monitoring-icon">▤</div>
                    <h3>PostgreSQL Database</h3>

                    <span
                      className={`monitoring-status ${monitoring.database}`}
                    >
                      {monitoring.database === 'online'
                        ? '● Online'
                        : '● Offline'}
                    </span>

                    <p>Database connection status</p>
                  </div>

                  <div className="monitoring-card">
                    <div className="monitoring-icon">✦</div>
                    <h3>AI Agent</h3>

                    <span
                      className={`monitoring-status ${
                        monitoring.agent === 'loaded'
                          ? 'loaded'
                          : 'offline'
                      }`}
                    >
                      {monitoring.agent === 'loaded'
                        ? '● Loaded'
                        : '● Unavailable'}
                    </span>

                    <p>Agent loaded, provider not checked</p>
                  </div>

                  <div className="monitoring-card">
                    <div className="monitoring-icon">▥</div>
                    <h3>Generated Reports</h3>

                    <strong>
                      {monitoring.reports_generated}
                    </strong>

                    <p>Markdown reports stored</p>
                  </div>

                  <div className="monitoring-card">
                    <div className="monitoring-icon">▧</div>
                    <h3>Generated Charts</h3>

                    <strong>
                      {monitoring.charts_generated}
                    </strong>

                    <p>PNG charts stored</p>
                  </div>
                </div>

                {monitoringCheckedAt && (
                  <p className="monitoring-last-check">
                    Last checked:{' '}
                    {monitoringCheckedAt.toLocaleTimeString('en-US')}
                    {' · '}Auto-refresh every 30 seconds
                  </p>
                )}
              </>
            )}
          </section>
        )}
      </main>
    </div>
  )
}

export default App
