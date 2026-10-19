
import { useCallback, useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import './App.css'

const API_URL = 'http://127.0.0.1:8000'

const numberFormatter = new Intl.NumberFormat('en-US')
const compactFormatter = new Intl.NumberFormat('en-US', {
  notation: 'compact',
  maximumFractionDigits: 2
})

function App() {
  const [activePage, setActivePage] = useState('overview')
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
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
        body: JSON.stringify({ question: currentQuestion })
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
          reports: data.reports || []
        }
      ])
    } catch (error) {
      setMessages((previous) => [
        ...previous,
        {
          role: 'assistant',
          content: `Unable to complete the analysis: ${error.message}`,
          charts: [],
          reports: []
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
                  <ReactMarkdown>{message.content}</ReactMarkdown>
                ) : (
                  message.content
                )}
              </div>

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
