# A股实时条件选股器

一个可直接部署使用的 A 股条件筛选工具。需要选股时点击查询，系统获取当前可用行情、主力资金流和最新完整财报数据，返回同时满足全部条件的股票。

> 行情来自东方财富公开接口，财报数据通过 AkShare 获取，属于实时/准实时公开数据，不是交易所 Level-2 逐笔行情。

## 筛选条件

默认同时满足以下四个条件：

1. 换手率：10%～30%
2. 当日主力资金净流入：> 1 亿元
3. 归母净利润同比增长率：≥ 30%
4. 营业总收入同比增长率：≥ 30%

页面支持临时调整条件后重新查询。

## 功能

- 查询沪深京 A 股当前价格、涨跌幅和换手率
- 查询当日主力资金净流入
- 结合最近完整报告期的净利润同比和营业收入同比
- 四个条件同时筛选
- 手动查询，不持续自动刷新
- 显示符合条件的股票及关键指标
- 没有符合条件的股票时正常显示 0 个结果
- Docker 一键部署

## 使用方式

启动系统后，在浏览器打开页面。系统不会持续请求行情；需要查看当前符合条件的股票时点击 **“立即查询”**。

查询时会获取当前可用行情和资金流，并结合财报数据完成筛选。再次点击查询即可取得新的结果。

## 快速部署

### macOS / Linux

需要提前安装 Git、Docker 和 Docker Compose。

```bash
git clone https://github.com/luolidong/a-share-realtime-screener.git
cd a-share-realtime-screener
docker compose up --build -d
```

浏览器打开：

```text
http://127.0.0.1:8080
```

### Windows 10 / 11

推荐使用 Docker Desktop + WSL2。完整安装和部署步骤：

**[Windows 部署指南](docs/WINDOWS_DEPLOYMENT.md)**

安装完成后，在 PowerShell 或 Windows Terminal 中：

```powershell
git clone https://github.com/luolidong/a-share-realtime-screener.git
cd a-share-realtime-screener
docker compose up --build -d
```

然后打开：

```text
http://127.0.0.1:8080
```

## 检查运行状态

```bash
docker compose ps
```

正常情况下：

- `backend`：healthy
- `frontend`：Up

检查服务：

```bash
curl http://127.0.0.1:8080/api/health
```

查询接口：

```bash
curl http://127.0.0.1:8080/api/stocks
```

返回 `[]` 表示当前没有股票同时满足全部条件，并不代表系统出错。

## 更新

以后仓库有新版本时：

```bash
git pull
docker compose up --build -d
```

## 停止和启动

停止：

```bash
docker compose down
```

重新启动：

```bash
docker compose up -d
```

## 默认条件配置

默认条件位于：

```text
backend/config.yaml
```

当前配置：

```yaml
rules:
  turnover_min: 10
  turnover_max: 30
  net_inflow_min_cny: 100000000
  net_profit_yoy_min: 30
  revenue_yoy_min: 30
```

修改默认条件后重新构建：

```bash
docker compose up --build -d
```

## 数据说明

实时查询包括最新价、涨跌幅、换手率和当日主力资金净流入。为了减少公开接口请求，行情和资金流使用同一份查询快照。

财务指标来自最近完整披露报告期。财报数据变化频率低，因此系统会缓存 6 小时，不影响盘中行情查询。

公开数据接口可能因为网络、限流或上游服务临时不可用而查询失败。出现“数据源暂不可用”时可以稍后重新查询。

## 文档

- **[Windows 部署指南](docs/WINDOWS_DEPLOYMENT.md)** — Windows 10/11 从安装 Docker 到运行项目
- **[部署与故障排查](docs/DEPLOYMENT.md)** — 通用部署、更新、日志和常见问题

## API

| 接口 | 用途 |
| --- | --- |
| `GET /api/health` | 服务健康状态 |
| `GET /api/rules` | 当前默认筛选条件 |
| `GET /api/stocks` | 查询当前符合条件的股票 |
| `GET /docs` | API 文档 |

## 注意

本项目用于数据筛选和信息展示，不构成投资建议。公开行情接口不提供交易所级可用性保证，不建议直接用于高频或自动交易。
