import { useEffect, useMemo, useRef, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000'
const US_DEFAULTS = { pct_min: 2, pct_max: 10, rvol_min: 1.5, amount_min_usd: 50000000, market_cap_min_usd: 1000000000 }

const pct = (v) => v == null ? '-' : `${Number(v).toFixed(2)}%`
const cny = (v) => v == null ? '-' : `${(v / 1e8).toFixed(2)} 亿`
const usd = (v) => v == null ? '-' : v >= 1e9 ? `$${(v / 1e9).toFixed(2)}B` : `$${(v / 1e6).toFixed(2)}M`
function dateTime(v) { return v ? v.toLocaleString('zh-CN', { year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false }) : '尚未查询' }

export default function App() {
  const [market, setMarket] = useState('cn')
  const [stocks, setStocks] = useState([])
  const [rules, setRules] = useState(null)
  const [form, setForm] = useState(null)
  const [usForm, setUsForm] = useState(US_DEFAULTS)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [updatedAt, setUpdatedAt] = useState(null)
  const busy = useRef(false)

  async function loadDefaults() {
    const res = await fetch(`${API_BASE}/api/rules`, { cache:'no-store' })
    if (!res.ok) throw new Error('获取筛选规则失败')
    const data = await res.json(); setRules(data); setForm(data); return data
  }

  async function refreshCN(active = form || rules) {
    if (busy.current) return; busy.current = true; setLoading(true); setError('')
    try {
      const r = active || await loadDefaults()
      const p = new URLSearchParams({ limit:'100', ...r, _:Date.now().toString() })
      const res = await fetch(`${API_BASE}/api/stocks?${p}`, { cache:'no-store' })
      if (!res.ok) throw new Error((await res.json()).detail || '获取股票数据失败')
      setStocks(await res.json()); setUpdatedAt(new Date())
    } catch(e) { setError(e.message || String(e)) } finally { busy.current=false; setLoading(false) }
  }

  async function refreshUS() {
    if (busy.current) return; busy.current=true; setLoading(true); setError('')
    try {
      const p = new URLSearchParams({ limit:'100', ...usForm, _:Date.now().toString() })
      const res = await fetch(`${API_BASE}/api/us/stocks?${p}`, { cache:'no-store' })
      if (!res.ok) throw new Error((await res.json()).detail || '获取美股数据失败')
      setStocks(await res.json()); setUpdatedAt(new Date())
    } catch(e) { setError(e.message || String(e)) } finally { busy.current=false; setLoading(false) }
  }

  useEffect(() => { loadDefaults().catch(e => setError(e.message)).finally(() => setLoading(false)) }, [])
  function switchMarket(next) { setMarket(next); setStocks([]); setUpdatedAt(null); setError('') }
  function setRule(key, value) { setForm(p => ({...p, [key]:Number(value)})) }
  function setUS(key, value) { setUsForm(p => ({...p, [key]:Number(value)})) }

  const cnRuleText = useMemo(() => !form ? [] : [
    `换手率 ${form.turnover_min}%–${form.turnover_max}%`, `主力净流入 > ${(form.net_inflow_min_cny/1e8).toFixed(2)} 亿`,
    `归母净利润同比 ≥ ${form.net_profit_yoy_min}%`, `营业总收入同比 ≥ ${form.revenue_yoy_min}%`
  ], [form])

  const isCN = market === 'cn'
  return <main className="page">
    <nav className="marketTabs"><button className={isCN?'active':''} onClick={() => switchMarket('cn')}>A股看板</button><button className={!isCN?'active':''} onClick={() => switchMarket('us')}>美股看板</button></nav>
    <header className="hero"><div><p className="eyebrow">{isCN?'A-SHARE':'U.S. STOCK'} ON-DEMAND SCREENER</p><h1>{isCN?'A股':'美股'}条件选股器</h1><p className="sub">{isCN?'手动查询当前行情、主力资金流与最新财报增长条件':'筛选当天强势、交易活跃且流动性充足的美股'}</p></div><button onClick={isCN?()=>refreshCN(form):refreshUS} disabled={loading}>{loading?'查询中…':'立即查询'}</button></header>

    {isCN && form && <section className="rulesEditor">
      <label>换手率最小值<input type="number" value={form.turnover_min} onChange={e=>setRule('turnover_min',e.target.value)}/></label><label>换手率最大值<input type="number" value={form.turnover_max} onChange={e=>setRule('turnover_max',e.target.value)}/></label><label>主力净流入（亿元）<input type="number" step="0.1" value={form.net_inflow_min_cny/1e8} onChange={e=>setRule('net_inflow_min_cny',Number(e.target.value)*1e8)}/></label><label>净利润同比（%）<input type="number" value={form.net_profit_yoy_min} onChange={e=>setRule('net_profit_yoy_min',e.target.value)}/></label><label>营收同比（%）<input type="number" value={form.revenue_yoy_min} onChange={e=>setRule('revenue_yoy_min',e.target.value)}/></label><button onClick={()=>refreshCN(form)} disabled={loading}>按当前条件查询</button>
    </section>}

    {!isCN && <section className="rulesEditor usRules">
      <label>涨幅最小值（%）<input type="number" value={usForm.pct_min} onChange={e=>setUS('pct_min',e.target.value)}/></label><label>涨幅最大值（%）<input type="number" value={usForm.pct_max} onChange={e=>setUS('pct_max',e.target.value)}/></label><label>RVOL 最小值<input type="number" step="0.1" value={usForm.rvol_min} onChange={e=>setUS('rvol_min',e.target.value)}/></label><label>成交额最小（百万美元）<input type="number" value={usForm.amount_min_usd/1e6} onChange={e=>setUS('amount_min_usd',Number(e.target.value)*1e6)}/></label><label>市值最小（十亿美元）<input type="number" value={usForm.market_cap_min_usd/1e9} onChange={e=>setUS('market_cap_min_usd',Number(e.target.value)*1e9)}/></label><button onClick={refreshUS} disabled={loading}>按当前条件查询</button>
    </section>}

    <section className="rules">{(isCN?cnRuleText:[`涨跌幅 +${usForm.pct_min}%～+${usForm.pct_max}%`,`相对成交量 RVOL ≥ ${usForm.rvol_min}`,`成交额 ≥ ${usd(usForm.amount_min_usd)}`,`市值 ≥ ${usd(usForm.market_cap_min_usd)}`]).map(x=><div className="rule" key={x}>{x}</div>)}</section>
    {!isCN && <div className="notice">美股第一版已启用实时行情、成交额、市值和 20 日平均成交量计算 RVOL；营收同比与 EPS 增长筛选将在财报数据源稳定性验证后接入。</div>}
    <section className="summary"><div><span>符合股票</span><strong>{stocks.length}</strong></div><div><span>最后查询时间</span><strong>{dateTime(updatedAt)}</strong></div></section>
    {error && <div className="error">{error}</div>}
    <section className="tableWrap"><table><thead>{isCN?<tr><th>代码</th><th>名称</th><th>现价</th><th>涨跌幅</th><th>换手率</th><th>主力净流入</th><th>净利润同比</th><th>营收同比</th></tr>:<tr><th>代码</th><th>公司</th><th>现价</th><th>涨跌幅</th><th>RVOL</th><th>成交量</th><th>成交额</th><th>市值</th></tr>}</thead><tbody>
      {!loading && updatedAt && stocks.length===0 && !error && <tr><td colSpan="8" className="empty">当前没有同时满足条件的股票</td></tr>}{!loading && !updatedAt && !error && <tr><td colSpan="8" className="empty">点击“立即查询”获取当前符合条件的股票</td></tr>}
      {stocks.map(s => isCN?<tr key={s.code}><td className="code">{s.code}</td><td>{s.name}</td><td>{s.price??'-'}</td><td className={s.pct_change>=0?'up':'down'}>{pct(s.pct_change)}</td><td>{pct(s.turnover_rate)}</td><td>{cny(s.net_inflow_cny)}</td><td>{pct(s.net_profit_yoy)}</td><td>{pct(s.revenue_yoy)}</td></tr>:<tr key={s.symbol}><td className="code">{s.symbol}</td><td>{s.name}</td><td>{s.price==null?'-':`$${s.price.toFixed(2)}`}</td><td className={s.pct_change>=0?'up':'down'}>{pct(s.pct_change)}</td><td>{s.rvol?.toFixed(2)??'-'}</td><td>{s.volume?.toLocaleString()??'-'}</td><td>{usd(s.amount_usd)}</td><td>{usd(s.market_cap_usd)}</td></tr>)}
    </tbody></table></section>
  </main>
}
