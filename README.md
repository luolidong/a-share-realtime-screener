# A股实时条件选股器

前后端分离的 A 股实时条件筛选项目。

- 后端：FastAPI + AkShare
- 前端：React + Vite
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
- 当日主力资金净流入筛选
- 最新财报净利润同比、营收同比筛选
- 四条件 AND 联合过滤
- 前端动态修改筛选参数
- 每 60 秒自动刷新
- 手动立即刷新
- 财务数据内存缓存 6 小时，避免盘中反复请求
- `/api/health` 显示财报缓存状态
- Docker Compose 一键启动前后端
- GitHub Actions 自动运行 `pytest` 和前端构建

## 项目结构

```text
.
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models.py
│   │   ├── screener.py
│   │   └── providers/
│   │       ├── base.py
│   │       └── akshare_provider.py
│   ├── tests/
│   │   ├── test_screener.py
│   │   └── test_rules.py
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

Docker 模式下 Nginx 会把 `/api/*` 自动代理到 FastAPI 后端。

## 本地开发：后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

接口：

- `GET /api/health`：健康检查 + 财报缓存状态
- `GET /api/rules`：默认筛选规则
- `GET /api/stocks?limit=100`：按默认规则筛选
- `GET /api/stocks?...规则参数...`：按前端传入的临时规则筛选
- `GET /docs`：FastAPI Swagger 文档

支持的规则参数：

- `turnover_min`
- `turnover_max`
- `net_inflow_min_cny`
- `net_profit_yoy_min`
- `revenue_yoy_min`

例如：

```text
/api/stocks?turnover_min=10&turnover_max=30&net_inflow_min_cny=100000000&net_profit_yoy_min=30&revenue_yoy_min=30
```

## 本地开发：前端

另开一个终端：

```bash
cd frontend
npm install
npm run dev
```

浏览器打开：

```text
http://127.0.0.1:5173
```

本地开发默认访问 `http://127.0.0.1:8000`。如需修改后端地址：

```bash
VITE_API_BASE=http://127.0.0.1:8000 npm run dev
```

## 数据来源

第一版使用 AkShare 聚合的东方财富公开数据：

- `stock_zh_a_spot_em`：A 股实时/准实时行情、换手率
- `stock_individual_fund_flow_rank(indicator="今日")`：当日主力资金净流入
- `stock_yjbb_em`：最新季报/年报的净利润同比和营业总收入同比

免费公开数据的实际刷新延迟和稳定性取决于上游接口。当前架构已经把数据源封装在 `providers/` 中，后续接入付费低延迟行情时不需要重写筛选逻辑和前端。

## 测试

```bash
cd backend
pytest -q
```

当前测试覆盖：

- 四个条件必须同时满足的 AND 筛选逻辑
- 前端传入规则覆盖默认值
- 换手率最小值大于最大值时返回非法参数

## 下一阶段

1. 保存每次扫描结果，形成历史命中记录
2. 新股票首次进入筛选结果时实时提醒
3. 增加市值、量比、行业、概念、涨停次数等规则
4. 增加排序、搜索、分页与导出 CSV
5. SSE/WebSocket 推送新命中股票
6. 增加备用数据源和付费实时行情 Provider
7. 为扫描任务加入交易时段调度、重试和数据源健康监控
