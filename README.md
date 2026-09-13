# A股实时条件选股器

前后端分离的 A 股实时条件筛选项目，聚焦一个核心功能：实时显示当前同时满足全部条件的股票。

## 当前状态

核心功能已经完成，可使用 Docker 在本机或服务器部署。GitHub Actions 会自动运行后端测试和前端生产构建。

> 数据来自 AkShare 聚合的东方财富公开接口，属于实时/准实时快照，不是交易所 Level-2 逐笔行情。上游接口的延迟和稳定性不由本项目控制。

## 默认筛选规则

四个条件必须同时满足：

1. 换手率：10%～30%
2. 当日主力资金净流入：> 1 亿元
3. 归母净利润同比增长率：≥ 30%
4. 营业总收入同比增长率：≥ 30%

默认阈值配置在 `backend/config.yaml`。前端可以临时调整筛选阈值并立即查询，不会改写服务器默认配置。

## 快速部署

环境要求：Git、Docker Engine（或 Docker Desktop）和 Docker Compose v2。

```bash
git clone https://github.com/luolidong/a-share-realtime-screener.git
cd a-share-realtime-screener
docker compose up --build -d
```

浏览器打开：

```text
http://127.0.0.1:8080
```

验证服务：

```bash
docker compose ps
curl http://127.0.0.1:8080/api/health
```

完整的端口修改、更新、日志和故障排查步骤见 [部署说明](docs/DEPLOYMENT.md)。

## 核心功能

- 获取沪深京 A 股实时/准实时行情和换手率
- 获取当日主力资金净流入
- 获取最近完整报告期的净利润同比和营收同比
- 对四个条件执行 AND 联合筛选
- 页面每 15 秒重新获取盘中数据并刷新结果
- 上一轮请求未完成时跳过重复刷新，避免并发压垮数据源
- 股票不再符合任一条件时，在下一次成功刷新中自动移出
- 显示最后成功刷新时间
- 财报数据缓存 6 小时，盘中行情和资金流不缓存
- Docker 后端健康检查与一键启动

## API

- `GET /api/health`：健康检查和财报缓存状态
- `GET /api/rules`：读取默认筛选规则
- `GET /api/stocks?limit=100`：按默认规则实时筛选
- `GET /api/stocks?...规则参数...`：按页面提交的临时条件实时筛选
- `GET /docs`：FastAPI Swagger 文档

支持的筛选参数：`turnover_min`、`turnover_max`、`net_inflow_min_cny`、`net_profit_yoy_min`、`revenue_yoy_min`。

## 数据刷新与来源

每次筛选都重新获取最新价、涨跌幅、换手率和今日主力资金净流入。财报增长数据缓存 6 小时。系统按北京时间和法定披露期限选择最近已完整披露的季度。

当前数据接口：

- `stock_zh_a_spot_em`：沪深京 A 股实时行情和换手率
- `stock_individual_fund_flow_rank(indicator="今日")`：当日主力资金净流入
- `stock_yjbb_em`：最近完整报告期的净利润同比和营业总收入同比

## 测试

```bash
cd backend
python -m pytest -q
```

测试覆盖四条件 AND 筛选、临时规则覆盖、规则合法性、报告期边界和股票代码规范化。
