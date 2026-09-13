# A股实时条件选股器

前后端分离的 A 股条件筛选项目，聚焦一个核心功能：在需要时手动查询当前同时满足全部条件的股票。

## 当前状态

核心实时数据链路已经验证可用：Docker 后端能够取得行情、换手率和当日主力资金净流入，并复用同一份实时快照；财报数据继续通过 AkShare 获取。前端已改为**手动查询为主**，不再每 15 秒自动刷新。GitHub Actions 用于自动运行测试和生产构建。

> 数据来自东方财富公开接口及 AkShare，属于实时/准实时快照，不是交易所 Level-2 逐笔行情。公开接口可能发生限流、节点变化或临时不可用，因此不能把它当作券商级行情 SLA。

## 默认筛选规则

四个条件必须同时满足：

1. 换手率：10%～30%
2. 当日主力资金净流入：> 1 亿元
3. 归母净利润同比增长率：≥ 30%
4. 营业总收入同比增长率：≥ 30%

默认阈值配置在 `backend/config.yaml`。前端可以临时调整筛选阈值并立即查询，不会改写服务器默认配置。

## 使用方式

打开页面后只加载默认筛选规则，不会自动拉取股票数据。需要查看当前结果时点击“立即查询”或“按当前条件查询”。

```text
打开页面
  ↓
加载默认规则
  ↓
等待用户操作
  ↓
点击“立即查询”
  ↓
现场拉取当前行情/资金流
  ↓
读取最近完整财报
  ↓
四条件 AND 筛选
  ↓
显示结果
```

这种方式减少了对免费公开行情接口的无意义重复请求，也更符合“需要时拿当前数据”的使用场景。

## 系统是怎么做的

一次筛选分为三步：

1. **实时候选集**：后端直接请求东方财富 clist 接口，同时取得股票代码、名称、价格、涨跌幅、换手率和今日主力净流入。为降低公开接口压力，实时行情和资金流共用同一份短时快照，并优先获取高换手股票；当数据已经低于默认换手率下限时停止继续翻页。
2. **财务数据**：通过 AkShare `stock_yjbb_em` 获取最近完整披露报告期的净利润同比增长和营业总收入同比增长。财报数据缓存 6 小时，因为它不需要每次都重新下载。
3. **AND 筛选**：按股票代码合并实时数据和财报数据，然后同时执行四个条件。任何一个条件不满足，该股票就不会出现在最终结果中。

东方财富部分使用浏览器兼容的 HTTP/TLS 请求方式，并配置多个可用节点/路径进行故障切换，以减少某些网络环境下 `RemoteDisconnected` 的问题。

## 项目结构

```text
a-share-realtime-screener/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI API
│   │   ├── screener.py             # 四条件 AND 筛选
│   │   ├── models.py               # 数据模型/规则
│   │   ├── config.py               # 配置读取
│   │   └── providers/
│   │       └── akshare_provider.py # 实时数据 + 财报数据 Provider
│   ├── tests/                       # 后端自动测试
│   ├── config.yaml                  # 默认筛选阈值
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                        # Web 页面
├── docs/
│   ├── DEPLOYMENT.md                # 部署与故障排查
│   └── DEVELOPMENT.md               # 从 0 开发教程
├── docker-compose.yml
└── README.md
```

## 快速部署

环境要求：Git、Docker Engine（或 Docker Desktop）和 Docker Compose v2。

```bash
git clone https://github.com/luolidong/a-share-realtime-screener.git
cd a-share-realtime-screener
docker compose up --build -d
```

浏览器打开 `http://127.0.0.1:8080`。

验证：

```bash
docker compose ps
curl http://127.0.0.1:8080/api/health
curl http://127.0.0.1:8080/api/stocks
```

完整部署步骤见 `docs/DEPLOYMENT.md`；如果要理解“没有 AI 时如何从 0 自己开发”，见 `docs/DEVELOPMENT.md`。

## 核心功能

- 获取沪深京 A 股实时/准实时价格、涨跌幅和换手率
- 获取当日主力资金净流入
- 实时行情和资金流复用同一快照，减少重复访问数据源
- 获取最近完整报告期净利润同比和营收同比
- 四条件 AND 联合筛选
- 页面手动触发查询，不自动 15 秒刷新
- 查询进行中禁止重复提交，避免并发压垮数据源
- 股票不再满足条件时，在下一次手动查询结果中自动移出
- 财报数据缓存 6 小时
- Docker 一键部署和后端健康检查

## API

- `GET /api/health`：健康检查和财报缓存状态
- `GET /api/rules`：读取默认筛选规则
- `GET /api/stocks?limit=100`：按默认规则筛选
- `GET /api/stocks?...规则参数...`：按临时条件筛选
- `GET /docs`：FastAPI Swagger 文档

支持参数：`turnover_min`、`turnover_max`、`net_inflow_min_cny`、`net_profit_yoy_min`、`revenue_yoy_min`。

## 数据字段

实时快照核心字段：

- `f12` → 股票代码
- `f14` → 股票名称
- `f2` → 最新价
- `f3` → 涨跌幅
- `f8` → 换手率
- `f62` → 今日主力净流入金额（人民币元）

财务字段：

- `股票代码`
- `净利润-同比增长`
- `营业总收入-同比增长`

## 测试

```bash
cd backend
python -m pytest -q
```

测试覆盖四条件 AND 筛选、规则覆盖、规则合法性、报告期边界和股票代码规范化。涉及公开实时接口的测试应与纯单元测试分开：单元测试必须可以在没有外网时运行，实时接口则作为集成/人工验证。

## 开发原则

这个项目最重要的不是页面，而是数据正确性和数据源稳定性。开发顺序应始终是：**先验证数据源 → 统一字段 → 写筛选逻辑和测试 → 做 API → 最后做前端和 Docker**。不要在实时数据尚未验证时先堆页面功能。
