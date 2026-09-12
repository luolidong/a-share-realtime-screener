import { useEffect, useMemo, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

function money(value) {
  if (value == null) return '-'
  return `${(value / 100000000).toFixed(2)} 亿`
}

function pct(value) {
  if (value == null) return '-'
  return `${Number(value).toFixed(2)}%`
}

export default function App() {
  const [stocks, setStocks] = useState([])
  const [rules, setRules] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [updatedAt, setUpdatedAt] = useState(null)

  async function refresh() {
    setLoading(true)
    setError('')
    try {
      const [stocksRes, rulesRes] = await Promise.all([
        fetch(`${API_BASE}/api/stocks?limit=100`),
        fetch(`${API_BASE}/api/rules`),
      ])
      if (!stocksRes.ok) throw new Error((await stocksRes.json()).detail || '获取股票数据失败')
      if (!rulesRes.ok) throw new Error('获取筛选规则失败')
      setStocks(await stocksRes.json())
      setRules(await rulesRes.json())
      setUpdatedAt(new Date())
    } catch (e) {
      setError(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
    const timer = setInterval(refresh, 60000)
    return () => clearInterval(timer)
  }, [])

  const ruleText = useMemo(() => {
    if (!rules) return []
    return [
      `换手率 ${rules.turnover_min}%–${rules.turnover_max}%`,
      `主力净流入 > ${(rules.net_inflow_min_cny / 100000000).toFixed(0)} 亿`,
      `归母净利润同比 ≥ ${rules.net_profit_yoy_min}%`,
      `营业总收入同比 ≥ ${rules.revenue_yoy_min}%`,
    ]
  }, [rules])

  return (
    <main className="page">
      <header className="hero">
        <div>
          <p className="eyebrow">A-SHARE REALTIME SCREENER</p>
          <h1>A股实时条件选股器</h1>
          <p className="sub">盘中行情 + 主力资金流 + 最新财报增长条件联合筛选</p>
        </div>
        <button onClick={refresh} disabled={loading}>{loading ? '刷新中…' : '立即刷新'}</button>
      </header>

      <section className="rules">
        {ruleText.map((item) => <div className="rule" key={item}>{item}</div>)}
      </section>

      <section className="summary">
        <div><span>符合股票</span><strong>{stocks.length}</strong></div>
        <div><span>刷新频率</span><strong>60 秒</strong></div>
        <div><span>最后更新</span><strong>{updatedAt ? updatedAt.toLocaleTimeString() : '-'}</strong></div>
      </section>

      {error && <div className="error">{error}</div>}

      <section className="tableWrap">
        <table>
          <thead>
            <tr>
              <th>代码</th><th>名称</th><th>现价</th><th>涨跌幅</th><th>换手率</th>
              <th>主力净流入</th><th>净利润同比</th><th>营收同比</th>
            </tr>
          </thead>
          <tbody>
            {!loading && stocks.length === 0 && !error && (
              <tr><td colSpan="8" className="empty">当前没有同时满足全部条件的股票</td></tr>
            )}
            {stocks.map((s) => (
              <tr key={s.code}>
                <td className="code">{s.code}</td>
                <td>{s.name}</td>
                <td>{s.price ?? '-'}</td>
                <td className={s.pct_change >= 0 ? 'up' : 'down'}>{pct(s.pct_change)}</td>
                <td>{pct(s.turnover_rate)}</td>
                <td>{money(s.net_inflow_cny)}</td>
                <td>{pct(s.net_profit_yoy)}</td>
                <td>{pct(s.revenue_yoy)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  )
}
