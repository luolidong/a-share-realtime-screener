# A股实时条件选股器

前后端分离的 A 股实时条件筛选项目。

- 后端：FastAPI + AkShare
- 前端：React + Vite
- 历史记录：SQLite
- 部署：Docker Compose + Nginx
- CI：GitHub Actions 自动测试后端并构建前端

## 默认筛选规则

四个条件同时满足：

1. 换手率：10% ~ 30%
2. 当日主力资金净流入：> 1 亿元
3. 归母净利润同比增长率：>= 30%
4. 营业总收入同比增长率：>= 30%

默认阈值配置在 `backend/config.yaml`。前端页面可以临时修改全部筛选阈值并立即重新查询，不会改写服务器上的默认配置。

## 当前功能

- A 股实时/准实时行情扫描
- 当日主力资金净流入动态筛选
- 最新财报净利润同比、营收同比筛选
- 四条件 AND 联合过滤
- 前端动态修改筛选参数
- 页面盘中每 15 秒刷新实时行情和资金流
- 后台扫描器按默认规则每 15 秒扫描一次，关闭网页后仍持续运行
- 后台仅在北京时间工作日 09:30–11:30、13:00–15:00 自动扫描
- 自动记录股票 `ENTER`（进入条件）和 `EXIT`（离开条件）事件
- SQLite 保存当前命中、扫描运行记录和进入/离开历史
- Docker volume 持久化 SQLite 数据，容器重启不丢历史
- 财务数据内存缓存 6 小时，避免盘中反复请求
- 前端显示后台扫描状态和最近进入/离开记录
- Docker Compose 一键启动前后端
- GitHub Actions 自动运行 `pytest` 和前端构建

## 项目结构

```text
.
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── scanner.py
│   │   ├── storage.py
│   │   ├── config.py
│   │   ├── models.py
│   │   ├── screener.py
│   │   └── providers/
│   │       ├── base.py
│   │       └── akshare_provider.py
│   ├── tests/
│   │   ├── test_screener.py
│   │   ├── test_rules.py
│   │   ├── test_scanner.py
│   │   └── test_storage.py
│   ├── config.yaml
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── nginx.conf
│   ├── Dockerfile
│   ├── index.html
│   └── package.json
├── .github/workflows/ci.yml
├── docker-compose.yml
└── .gitignore
```

## 一键 Docker 启动

在项目根目录执行：

```bash
docker compose up --build -d
```

浏览器打开：

```text
http://127.0.0.1:8080
```

停止：

```bash
docker compose down
```

Docker 模式下 Nginx 会把 `/api/*` 自动代理到 FastAPI 后端。历史数据库保存到 Docker named volume `screener_data`。

## API

- `GET /api/health`：健康检查、财报缓存和扫描器状态
- `GET /api/rules`：默认筛选规则
- `GET /api/stocks?limit=100`：实时按默认规则筛选
- `GET /api/stocks?...规则参数...`：按临时规则实时筛选
- `GET /api/scanner/status`：后台扫描器、交易时段和最近扫描状态
- `GET /api/scanner/active`：后台默认规则当前命中的股票
- `GET /api/scanner/events?limit=100`：最近 ENTER / EXIT 历史
- `POST /api/scanner/scan-now`：手工立即执行一次后台规则扫描
- `GET /docs`：FastAPI Swagger 文档

支持的实时筛选参数：`turnover_min`、`turnover_max`、`net_inflow_min_cny`、`net_profit_yoy_min`、`revenue_yoy_min`。

## 数据刷新策略

盘中变化快的数据不缓存：

- 最新价
- 涨跌幅
- 换手率
- 今日主力资金净流入

这些字段每次扫描都会重新从上游获取。若某股票资金净流入从 1.2 亿元降到 0.8 亿元，下一次扫描就会从命中集合移除并记录 `EXIT`；重新超过阈值后会再次记录 `ENTER`。

财报增长数据不会盘中持续变化，因此缓存 6 小时，以降低上游压力。

## 数据来源

第一版使用 AkShare 聚合的东方财富公开数据：

- `stock_zh_a_spot_em`：A 股实时/准实时行情、换手率
- `stock_individual_fund_flow_rank(indicator="今日")`：当日主力资金净流入
- `stock_yjbb_em`：最新季报/年报的净利润同比和营业总收入同比

免费公开数据的实际刷新延迟和稳定性取决于上游接口。当前架构已经把数据源封装在 `providers/` 中，后续接入券商、Level-2 或付费低延迟行情时不需要重写筛选逻辑和前端。

## 测试

```bash
cd backend
pytest -q
```

当前测试覆盖四条件 AND 筛选、临时规则覆盖、规则合法性、A 股交易时段以及 SQLite ENTER/EXIT 持久化。

## 下一阶段

1. 新进入条件股票的实时浏览器/SSE 提醒
2. 统计每次 ENTER 后 5/15/30/60 分钟及收盘收益，验证筛选条件有效性
3. 增加资金净流入变化速度、连续净流入等动态指标
4. 增加市值、量比、行业、概念、涨停次数等规则
5. 增加备用数据源和付费实时行情 Provider
