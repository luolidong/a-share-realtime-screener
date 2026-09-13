# 部署说明

## 1. 环境要求

推荐使用 Docker 部署。需要：

- Git
- Docker Engine 24 或更高版本
- Docker Compose v2
- 能访问 GitHub、Python 软件包源、npm 软件包源以及东方财富数据接口的网络

Windows 和 macOS 可以安装 Docker Desktop；Linux 可以安装 Docker Engine 与 Compose 插件。

## 2. 下载项目

```bash
git clone https://github.com/luolidong/a-share-realtime-screener.git
cd a-share-realtime-screener
```

仓库是私有仓库时，需要先登录 GitHub，或使用已有权限的 SSH 地址克隆。

## 3. 启动

使用默认端口 8080：

```bash
docker compose up --build -d
```

浏览器打开：

```text
http://127.0.0.1:8080
```

局域网内其他设备访问：

```text
http://部署电脑的局域网IP:8080
```

如果 8080 已被占用，可以指定其他端口：

```bash
APP_PORT=8090 docker compose up --build -d
```

然后打开 `http://127.0.0.1:8090`。

## 4. 验证是否正常

查看容器状态：

```bash
docker compose ps
```

`backend` 应显示 `healthy`，`frontend` 应显示 `Up`。

检查后端健康状态：

```bash
curl http://127.0.0.1:8080/api/health
```

正常响应示例：

```json
{
  "status": "ok",
  "financial_cache": {
    "period": null,
    "cached_at": null,
    "ttl_seconds": 21600,
    "ready": false
  }
}
```

首次打开页面后，系统会拉取财报数据，此后 `ready` 会变为 `true`。首轮全市场查询通常比后续刷新更慢。

## 5. 日常操作

查看实时日志：

```bash
docker compose logs -f --tail=100
```

只看后端日志：

```bash
docker compose logs -f --tail=100 backend
```

停止：

```bash
docker compose down
```

重新启动：

```bash
docker compose restart
```

更新到最新代码并重建：

```bash
git pull
docker compose up --build -d
```

## 6. 修改默认条件

编辑 `backend/config.yaml`：

```yaml
rules:
  turnover_min: 10
  turnover_max: 30
  net_inflow_min_cny: 100000000
  net_profit_yoy_min: 30
  revenue_yoy_min: 30
```

修改后重建后端：

```bash
docker compose up --build -d backend
```

页面中的条件调整只影响当前浏览器查询，不会写回配置文件。

## 7. 实际使用说明

- 页面每 15 秒请求一次实时筛选结果。
- 若上一轮查询尚未结束，系统会跳过本轮，避免重复请求压垮免费数据源。
- 行情、换手率和当日主力资金净流入每次重新获取。
- 财报增长率缓存 6 小时。
- 免费公开接口属于实时/准实时快照，不是交易所 Level-2 逐笔行情。
- 非交易时间看到的是上一个交易时点或收盘数据。
- 东方财富接口短暂不可用时，页面会显示错误；无需重装，稍后点击“立即刷新”即可。

## 8. 常见问题

### 页面无法打开

执行：

```bash
docker compose ps
docker compose logs --tail=100
```

确认 8080 端口未被其他程序占用；被占用时使用 `APP_PORT=8090` 启动。

### 页面显示“数据源暂不可用”

查看后端日志：

```bash
docker compose logs --tail=100 backend
```

通常是上游接口暂时超时或部署机器无法访问东方财富。先确认网络，然后稍后刷新。

### 修改代码后页面没有变化

重新构建镜像：

```bash
docker compose up --build -d
```

必要时在浏览器中强制刷新页面。
