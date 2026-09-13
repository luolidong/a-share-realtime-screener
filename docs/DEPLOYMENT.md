# 部署说明

## 1. 环境要求

推荐使用 Docker 部署。需要 Git、Docker Engine 24+（或 Docker Desktop）、Docker Compose v2，以及能够访问 GitHub、Python/npm 软件包源和行情数据源的网络。

## 2. 下载并启动

```bash
git clone https://github.com/luolidong/a-share-realtime-screener.git
cd a-share-realtime-screener
docker compose up --build -d
```

浏览器打开 `http://127.0.0.1:8080`。如果 8080 被占用：

```bash
APP_PORT=8090 docker compose up --build -d
```

## 3. 验证

```bash
docker compose ps
curl http://127.0.0.1:8080/api/health
curl http://127.0.0.1:8080/api/stocks
```

`backend` 应为 `healthy`，`frontend` 应为运行状态。`/api/stocks` 返回 `[]` 代表当前没有股票同时满足条件，不等于数据源故障；HTTP 503 和 `数据源暂不可用` 才表示数据链路失败。

也可以在容器中直接验证实时 Provider：

```bash
docker compose exec backend python -c "from app.providers.akshare_provider import AkShareProvider; p=AkShareProvider(); q=p.get_realtime_quotes(); print('quotes', len(q)); print(q.head()); f=p.get_realtime_money_flow(); print('flows', len(f)); print(f.head())"
```

当前实现会先构造满足最低换手率候选范围的实时快照，因此返回数量不要求等于整个 A 股市场。行情和资金流应来自同一快照，数量通常一致。

## 4. 日常操作

```bash
# 日志
docker compose logs -f --tail=100

# 后端日志
docker compose logs -f --tail=100 backend

# 停止
docker compose down

# 重启
docker compose restart

# 更新代码并重建
git pull
docker compose up --build -d
```

## 5. 修改默认条件

编辑 `backend/config.yaml`：

```yaml
rules:
  turnover_min: 10
  turnover_max: 30
  net_inflow_min_cny: 100000000
  net_profit_yoy_min: 30
  revenue_yoy_min: 30
```

修改后执行：

```bash
docker compose up --build -d
```

## 6. 数据刷新与缓存

实时价格、涨跌幅、换手率和今日主力资金净流入来自同一实时快照，避免重复下载市场数据。财报增长率通过 AkShare 获取并缓存 6 小时。免费公开接口是实时/准实时数据，不是交易所 Level-2；非交易时间通常显示最近交易时点/收盘数据。

## 7. 网络与数据源故障排查

### 页面打不开

```bash
docker compose ps
docker compose logs --tail=100
```

先检查容器和端口。

### backend healthy，但页面显示“数据源暂不可用”

这表示 Web 服务本身活着，但上游数据请求失败。查看：

```bash
docker compose logs --tail=100 backend
```

不要因为 backend `healthy` 就判断行情接口一定正常；健康检查只证明 FastAPI 服务能响应。

### `RemoteDisconnected('Remote end closed connection without response')`

这类错误通常发生在公开行情接口主动关闭连接。项目当前实时 Provider 已使用浏览器兼容请求方式，并配置多个东方财富节点/路径进行 fallback。若仍出现错误，先用 Provider 独立测试命令确认，不要同时修改前端和 Docker。

普通网站能够访问也不能证明行情 API 一定可访问；应直接测试目标 API/Provider。

### Docker 拉取镜像超时

如果所在网络访问 Docker Hub 不稳定，可以在 Docker Desktop/daemon 配置可用 registry mirror。镜像地址属于外部基础设施，应按当前所在网络选择，不要把某个临时镜像硬编码进项目代码。

### 修改代码后页面没变化

```bash
git pull
docker compose up --build -d
```

然后浏览器强制刷新。

## 8. 当前数据源说明

实时部分不再分别调用 AkShare 的全市场行情和资金流函数，而是直接从东方财富 clist 响应取得 `f12/f14/f2/f3/f8/f62`，并复用一份 snapshot。这是为了减少公开接口请求数量并解决部分网络环境下通用节点断开连接的问题。

财报仍使用 AkShare `stock_yjbb_em`。数据源实现集中在 `backend/app/providers/akshare_provider.py`，以后更换数据供应商时应优先新增/替换 Provider，而不是修改筛选器和前端。

## 9. 开发文档

如果需要从零重新开发、理解架构、测试方法和排错顺序，请阅读 `docs/DEVELOPMENT.md`。
