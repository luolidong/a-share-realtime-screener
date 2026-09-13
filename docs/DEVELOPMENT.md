# 从 0 开发 A 股实时条件选股器

这份文档说明在没有 AI 代写代码的情况下，如何从需求开始独立完成本项目。重点不是复制现有代码，而是掌握正确的开发顺序、验证方法和排错方法。

## 1. 先把需求写成可以验证的规则

目标只有一个：找到当前同时满足以下条件的 A 股：

- 换手率 10%～30%
- 今日主力资金净流入 > 100,000,000 元
- 归母净利润同比增长率 ≥ 30%
- 营业总收入同比增长率 ≥ 30%

先明确单位、边界和 AND/OR。这里 `10%～30%` 包含 10 和 30；资金流必须严格大于 1 亿；两个增长率包含 30；四个条件是 AND。

## 2. 设计最小架构

不要一开始做复杂系统。最小架构：

```text
浏览器
   ↓ HTTP
Nginx / Frontend
   ↓ /api
FastAPI Backend
   ↓
Data Provider
   ├── 实时行情/资金流
   └── 财务数据
   ↓
pandas merge + filter
```

Provider 层非常重要。业务筛选代码不应该知道东方财富/AkShare 的具体字段，这样以后换数据源只需要修改 Provider。

## 3. 创建项目

```bash
mkdir a-share-realtime-screener
cd a-share-realtime-screener
git init
mkdir -p backend/app/providers backend/tests frontend docs
```

先完成后端，后端真正返回正确结果之后再做前端。

## 4. 建 Python 环境

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi 'uvicorn[standard]' pandas pydantic PyYAML pytest httpx akshare curl_cffi
```

把确认可工作的依赖写进 `requirements.txt`。

## 5. 第一件事不是写业务代码，而是验证数据源

先用最小 Python 脚本测试每一个数据源。每次只测试一个接口，并打印 HTTP 状态、记录数量和前几条数据。

实时数据至少要确认：股票代码、名称、价格、涨跌幅、换手率、今日主力净流入。当前实现使用东方财富 clist 字段：

```text
f12 = 股票代码
f14 = 股票名称
f2  = 最新价
f3  = 涨跌幅
f8  = 换手率
f62 = 今日主力净流入金额
```

财报数据确认 AkShare `stock_yjbb_em(date=报告期)` 能返回：`股票代码`、`净利润-同比增长`、`营业总收入-同比增长`。

### 为什么必须先单独测试接口

本项目开发中遇到过典型问题：普通网站可访问，但东方财富某些实时节点会返回 `RemoteDisconnected`；小请求曾经成功，随后同一节点又可能主动断开。这个问题不是 pandas、FastAPI 或前端造成的。

排错时必须分层：

```text
Docker 是否联网？
        ↓
目标域名是否能连接？
        ↓
具体 API 是否响应？
        ↓
请求参数是否正确？
        ↓
返回字段是否正确？
        ↓
业务筛选是否正确？
```

不要看到页面报错就同时修改 Docker、前端和筛选算法。

## 6. 实现 Provider

定义统一接口：

```python
class StockDataProvider:
    def get_realtime_quotes(self): ...
    def get_realtime_money_flow(self): ...
    def get_financial_growth(self): ...
```

对外统一输出：

```text
quotes:
code, name, price, pct_change, turnover_rate

flows:
code, net_inflow_cny

financials:
code, net_profit_yoy, revenue_yoy
```

所有股票代码规范成 6 位字符串，例如 `1` → `000001`。不要把股票代码存成整数。

## 7. 优化实时请求

价格、涨跌幅、换手率和 `f62` 可以来自同一份 clist 响应，因此应该建立一个实时 snapshot，再让 `get_realtime_quotes()` 和 `get_realtime_money_flow()` 从同一 snapshot 取字段，而不是把市场下载两遍。

默认规则只需要换手率 ≥10% 的股票，因此可以按换手率降序读取，在确认后续数据已经低于下限时停止分页。这个优化必须建立在排序和停止条件确实可靠的前提下，不能为了省请求而遗漏候选股票。

公开实时接口需要：合理 timeout、有限次数 retry、节点/路径 fallback、请求节流。不要无限重试，否则上游故障会把 API 请求长期挂死。

## 8. 财报报告期

不能简单使用“当前季度”。例如 9 月初二季度报告已经披露完成，但三季报尚未完整披露。

项目按法定披露时间选择最近完整季度，并对财报缓存 6 小时。日期边界必须写单元测试，避免跨季度时悄悄使用错误报告期。

## 9. 实现筛选器

先合并三类数据：

```python
df = quotes.merge(flows, on='code', how='inner')
df = df.merge(financials, on='code', how='inner')
```

然后把所有参与比较的字段转换为 numeric，再执行：

```python
matched = df[
    df['turnover_rate'].between(10, 30, inclusive='both')
    & (df['net_inflow_cny'] > 100_000_000)
    & (df['net_profit_yoy'] >= 30)
    & (df['revenue_yoy'] >= 30)
]
```

先让这段逻辑完全正确，再做 Web API。

## 10. 先写测试再接真实页面

至少构造几只假股票：一只四项全部满足；一只资金流只有 1 亿（必须失败）；一只换手率 30（应通过换手率条件）；一只利润 29.99（失败）；一只营收 29.99（失败）。

运行：

```bash
python -m pytest -q
```

测试的价值是以后换数据源、重构 Provider 时，能够证明核心选股规则没有被改坏。

## 11. 建 FastAPI

最少只需要：

```text
GET /api/health
GET /api/rules
GET /api/stocks
```

`/api/stocks` 调用筛选器并返回 JSON。先用 curl 测试：

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/stocks
```

API 正确以后才进入前端开发。

## 12. 前端

前端只承担展示和输入筛选参数，不复制后端筛选逻辑。核心页面需要：规则输入、立即刷新、结果表格、最后成功刷新时间、错误提示。

定时刷新时，如果上一轮 API 请求还没完成，不要再启动第二轮相同请求。

## 13. Docker 化

分别为 backend/frontend 写 Dockerfile，再用 `docker-compose.yml` 组合。Nginx 对外暴露一个端口并把 `/api` 转发给 backend。

验证顺序：

```bash
docker compose up --build -d
docker compose ps
curl http://127.0.0.1:8080/api/health
curl http://127.0.0.1:8080/api/stocks
```

只有这四步正常，才算部署成功。

## 14. Git 和 CI

每完成一个可验证的小阶段就提交：

```bash
git add .
git commit -m 'feat: implement stock screening'
git push
```

CI 至少运行后端 `pytest` 和前端 production build。CI 不应该依赖实时公开数据接口，否则上游临时故障会让你的代码在没有问题时也显示红灯。

## 15. 从 0 开发时推荐的完整顺序

```text
需求和字段定义
→ 找数据源
→ 用独立脚本验证每个接口
→ Provider/字段标准化
→ 写假数据单元测试
→ 实现四条件筛选
→ 验证真实数据
→ FastAPI
→ curl 测 API
→ 前端
→ Docker
→ CI
→ 文档
→ 长时间运行观察数据源稳定性
```

如果某一步失败，只修这一层。比如实时接口失败时，不应该先改前端；Docker 能访问百度不代表目标行情 API 一定可用；健康检查成功也不代表实时数据源一定健康。

## 16. 如何判断项目真的完成

不是“页面能打开”就完成。至少要同时满足：

- 单元测试全部通过
- Docker backend healthy
- 实时 snapshot 能返回合理数量和字段
- `f62` 数值单位确认是人民币元
- 财报接口能取得当前应使用报告期
- `/api/stocks` 能完成四条件筛选
- 没有符合股票时正确返回空数组，而不是报错
- 数据源故障时返回清楚的错误，而不是假数据
- 前端能区分“0 个符合结果”和“数据源失败”
- README 与实际代码一致

## 17. 后续如果换正式数据源

保持 `StockDataProvider` 接口不变，新建另一个 Provider 即可。筛选器、API 和前端原则上不需要重写。这就是把“数据获取”和“业务规则”分层的主要价值。
