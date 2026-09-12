import { useEffect, useMemo, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000'
const REALTIME_REFRESH_MS = 15000

function money(value) {
  if (value == null) return '-'
  return `${(value / 100000000).toFixed(2)} 亿`
}

function pct(value) {
  if (value == null) return '-'
  return `${Number(value).toFixed(2)}%`
}

function localTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

export default function App() {
  const [stocks, setStocks] = useState([])
  const [rules, setRules] = useState(null)
  const [form, setForm] = useState(null)
  const [scanner, setScanner] = useState(null)
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [updatedAt, setUpdatedAt] = useState(null)

  async function loadDefaults() {
    const rulesRes = await fetch(`${API_BASE}/api/rules`, { cache: 'no-store' })
    if (!rulesRes.ok) throw new Error('获取筛选规则失败')
    const data = await rulesRes.json()
    setRules(data)
    setForm(data)
    return data
  }

  async function loadMonitor() {
    try {
      const [statusRes, eventsRes] = await Promise.all([
        fetch(`${API_BASE}/api/scanner/status`, { cache: 'no-store' }),
        fetch(`${API_BASE}/api/scanner/events?limit=30`, { cache: 'no-store' }),
      ])
      if (statusRes.ok) setScanner(await statusRes.json())
      if (eventsRes.ok) setEvents(await eventsRes.json())
    } catch (_) {
      // 主筛选请求会单独显示错误，监控区短暂失败不打断页面。
    }
  }

  async function refresh(activeRules = form || rules) {
    setLoading(true)
    setError('')
    try {
      let currentRules = activeRules
      if (!currentRules) currentRules = await loadDefaults()
      const params = new URLSearchParams({
        limit: '100',
        turnover_min: currentRules.turnover_min,
        turnover_max: currentRules.turnover_max,
        net_inflow_min_cny: currentRules.net_inflow_min_cny,
        net_profit_yoy_min: currentRules.net_profit_yoy_min,
        revenue_yoy_min: currentRules.revenue_yoy_min,
        _: Date.now().toString(),
      })
      const stocksRes = await fetch(`${API_BASE}/api/stocks?${params}`, { cache: 'no-store' })
      if (!stocksRes.ok) throw new Error((await stocksRes.json()).detail || '获取股票数据失败')
      setStocks(await stocksRes.json())
      setUpdatedAt(new Date())
      await loadMonitor()
    } catch (e) {
      setError(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDefaults().then((defaults) => refresh(defaults)).catch((e) => {
      setError(e.message || String(e))
      setLoading(false)
    })
  }, [])

  useEffect(() => {
    if (!form) return
    const timer = setInterval(() => refresh(form), REALTIME_REFRESH_MS)
    return () => clearInterval(timer)
  }, [form])

  const ruleText = useMemo(() => {
    if (!form) return []
    return [
      `换手率 ${form.turnover_min}%–${form.turnover_max}%`,
      `主力净流入 > ${(form.net_inflow_min_cny / 100000000).toFixed(2)} 亿`,
      `归母净利润同比 ≥ ${form.net_profit_yoy_min}%`,
      `营业总收入同比 ≥ ${form.revenue_yoy_min}%`,
    ]
  }, [form])

  function setRule(key, value) {
    setForm((prev) => ({ ...prev, [key]: Number(value) }))
  }

  return (
    <main className="page">
      <header className="hero">
        <div>
          <p className="eyebrow">A-SHARE REALTIME SCREENER</p>
          <h1>A股实时条件选股器</h1>
          <p className="sub">盘中行情 + 主力资金流 + 最新财报增长条件联合筛选</p>
        </div>
        <button onClick={() => refresh(form)} disabled={loading}>{loading ? '刷新中…' : '立即刷新'}</button>
      </header>

      {form && (
        <section className="rulesEditor">
          <label>换手率最小值<input type="number" value={form.turnover_min} onChange={(e) => setRule('turnover_min', e.target.value)} /></label>
          <label>换手率最大值<input type="number" value={form.turnover_max} onChange={(e) => setRule('turnover_max', e.target.value)} /></label>
          <label>主力净流入（亿元）<input type="number" step="0.1" value={form.net_inflow_min_cny / 100000000} onChange={(e) => setRule('net_inflow_min_cny', Number(e.target.value) * 100000000)} /></label>
          <label>净利润同比（%）<input type="number" value={form.net_profit_yoy_min} onChange={(e) => setRule('net_profit_yoy_min', e.target.value)} /></label>
          <label>营收同比（%）<input type="number" value={form.revenue_yoy_min} onChange={(e) => setRule('revenue_yoy_min', e.target.value)} /></label>
          <button onClick={() => refresh(form)} disabled={loading}>应用条件</button>
        </section>
      )}

      <section className="rules">
        {ruleText.map((item) => <div className="rule" key={item}>{item}</div>)}
      </section>

      <section className="summary">
        <div><span>符合股票</span><strong>{stocks.length}</strong></div>
        <div><span>后台扫描</span><strong>{scanner?.market_open ? '交易中 · 15秒' : '休市待机'}</strong></div>
        <div><span>最后实时刷新</span><strong>{updatedAt ? updatedAt.toLocaleTimeString() : '-'}</strong></div>
      </section>

      {error && <div className="error">{error}</div>}

      <section className="tableWrap">
        <table>
          <thead><tr><th>代码</th><th>名称</th><th>现价</th><th>涨跌幅</th><th>换手率</th><th>主力净流入</th><th>净利润同比</th><th>营收同比</th></tr></thead>
          <tbody>
            {!loading && stocks.length === 0 && !error && <tr><td colSpan="8" className="empty">当前没有同时满足全部条件的股票</td></tr>}
            {stocks.map((s) => (
              <tr key={s.code}>
                <td className="code">{s.code}</td><td>{s.name}</td><td>{s.price ?? '-'}</td>
                <td className={s.pct_change >= 0 ? 'up' : 'down'}>{pct(s.pct_change)}</td>
                <td>{pct(s.turnover_rate)}</td><td>{money(s.net_inflow_cny)}</td><td>{pct(s.net_profit_yoy)}</td><td>{pct(s.revenue_yoy)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="eventsSection">
        <div className="sectionTitle">
          <div><p className="eyebrow">BACKGROUND SCANNER</p><h2>最近进入 / 离开记录</h2></div>
          <span>{scanner?.last_scan ? `最近扫描：${localTime(scanner.last_scan.scanned_at)}` : '等待交易时段扫描'}</span>
        </div>
        <div className="tableWrap">
          <table>
            <thead><tr><th>时间</th><th>动作</th><th>代码</th><th>名称</th><th>换手率</th><th>主力净流入</th><th>当时涨跌幅</th></tr></thead>
            <tbody>
              {events.length === 0 && <tr><td colSpan="7" className="empty">暂无进入/离开记录</td></tr>}
              {events.map((e) => (
                <tr key={e.id}>
                  <td>{localTime(e.event_at)}</td>
                  <td><span className={e.event_type === 'ENTER' ? 'eventEnter' : 'eventExit'}>{e.event_type === 'ENTER' ? '进入' : '离开'}</span></td>
                  <td className="code">{e.code}</td><td>{e.name}</td><td>{pct(e.turnover_rate)}</td><td>{money(e.net_inflow_cny)}</td><td>{pct(e.pct_change)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  )
}
