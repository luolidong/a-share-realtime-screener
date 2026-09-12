# A股实时条件选股器

前后端分离的 A 股实时条件筛选项目。

- 后端：FastAPI + AkShare
- 前端：React + Vite
- 当前目标：根据盘中行情、主力资金流和最新财务增长数据筛选股票

## 当前默认筛选规则

四个条件同时满足：

1. 换手率：10% ~ 30%
2. 当日主力资金净流入：> 1 亿元
3. 归母净利润同比增长率：>= 30%
4. 营业总收入同比增长率：>= 30%

筛选阈值统一配置在 `backend/config.yaml`。

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
│   │   └── test_screener.py
│   ├── config.yaml
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── index.html
│   └── package.json
└── .gitignore
```

## 后端启动

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

接口：

- `GET /api/health`：健康检查
- `GET /api/rules`：当前筛选规则
- `GET /api/stocks?limit=100`：返回符合全部条件的股票
- `GET /docs`：FastAPI Swagger 文档

## 前端启动

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

前端默认访问：

```text
http://127.0.0.1:8000
```

如需修改后端地址，可设置：

```bash
VITE_API_BASE=http://127.0.0.1:8000 npm run dev
```

## 数据来源

第一版使用 AkShare 聚合的东方财富公开数据：

- `stock_zh_a_spot_em`：A 股实时/准实时行情、换手率
- `stock_individual_fund_flow_rank(indicator="今日")`：当日主力资金净流入
- `stock_yjbb_em`：最新季报/年报的净利润同比和营业总收入同比

免费公开数据的实际刷新延迟和稳定性取决于上游接口，因此当前架构将数据源封装在 `providers/` 中。后续如果接入付费实时源，只需新增 Provider，不需要重写筛选逻辑和前端。

## 测试

```bash
cd backend
pytest -q
```

目前测试覆盖四个条件必须同时满足的 AND 筛选逻辑。

## 下一阶段

- 财报数据缓存，避免盘中反复请求
- Redis/本地缓存与数据更新时间展示
- 自动定时扫描和历史命中记录
- 前端可编辑筛选条件
- 市值、量比、行业、概念、涨停次数等扩展规则
- WebSocket/SSE 推送新命中股票
- 多数据源容错与付费实时行情 Provider
- Docker Compose 一键启动前后端
- GitHub Actions 自动测试与前端构建
