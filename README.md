# A股实时条件选股器

前后端分离的 A 股实时条件筛选项目，聚焦一个核心功能：实时显示当前同时满足全部条件的股票。

- 后端：FastAPI + AkShare
- 前端：React + Vite
- 部署：Docker Compose + Nginx
- CI：GitHub Actions 自动测试后端并构建前端

## 默认筛选规则

四个条件必须同时满足：

1. 换手率：10%～30%
2. 当日主力资金净流入：> 1 亿元
3. 归母净利润同比增长率：≥ 30%
4. 营业总收入同比增长率：≥ 30%

默认阈值配置在 `backend/config.yaml`。前端可以临时调整筛选阈值并立即查询，不会改写服务器默认配置。

## 核心功能

- 获取 A 股实时/准实时行情和换手率
- 获取当日主力资金净流入
- 获取最近完整报告期的净利润同比和营收同比
- 对四个条件执行 AND 联合筛选
- 页面每 15 秒重新获取盘中数据并刷新结果
- 股票不再符合任一条件时，在下一次刷新中自动移出
- 显示数据最后刷新时间
- 财报数据缓存 6 小时，盘中行情和资金流不缓存
- 支持 Docker Compose 一键启动

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
│   │   ├── test_rules.py
│   │   └── test_provider.py
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

## 启动

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

Docker 模式下，Nginx 会把 `/api/*` 自动代理到 FastAPI 后端。

## API

- `GET /api/health`：健康检查和财报缓存状态
- `GET /api/rules`：读取默认筛选规则
- `GET /api/stocks?limit=100`：按默认规则实时筛选
- `GET /api/stocks?...规则参数...`：按页面提交的临时条件实时筛选
- `GET /docs`：FastAPI Swagger 文档

支持的筛选参数：`turnover_min`、`turnover_max`、`net_inflow_min_cny`、`net_profit_yoy_min`、`revenue_yoy_min`。

## 数据刷新

每次请求都重新获取以下盘中数据：

- 最新价
- 涨跌幅
- 换手率
- 今日主力资金净流入

财报增长数据不会在盘中持续变化，因此缓存 6 小时。系统按北京时间和法定披露期限选取最近已经完整披露的季度，避免因过早切换到尚未披露齐全的新报告期而大量漏选股票。页面默认每 15 秒请求一次完整筛选结果。

## 数据来源

当前使用 AkShare 聚合的东方财富公开数据：

- `stock_zh_a_spot_em`：A 股实时/准实时行情和换手率
- `stock_individual_fund_flow_rank(indicator="今日")`：当日主力资金净流入
- `stock_yjbb_em`：最近完整报告期的净利润同比和营业总收入同比

免费公开数据的实际延迟和稳定性取决于上游接口。数据源已封装在 `providers/`，更换数据源时不需要重写筛选逻辑或前端。

## 测试

```bash
cd backend
python -m pytest -q
```

测试覆盖四条件 AND 筛选、临时规则覆盖、规则合法性、报告期边界以及股票代码规范化。
