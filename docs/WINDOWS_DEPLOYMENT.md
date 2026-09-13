# Windows 部署指南

本文介绍如何在 Windows 10 / Windows 11 上部署本项目。推荐使用 Docker Desktop + WSL2 后端，这是当前最省事、最接近 Linux 服务器环境的方式。

## 1. 推荐环境

建议使用：

- Windows 10 22H2 或 Windows 11
- Git for Windows
- Docker Desktop
- WSL2
- PowerShell 7 或 Windows Terminal

不建议直接在 Windows 原生 Python/Node 环境里分别运行前后端，除非你明确需要本地开发模式。生产/日常使用优先 Docker。

## 2. 安装 WSL2

以管理员身份打开 PowerShell：

```powershell
wsl --install
```

安装完成后重启电脑。

检查：

```powershell
wsl --status
wsl -l -v
```

如果默认版本不是 2：

```powershell
wsl --set-default-version 2
```

## 3. 安装 Docker Desktop

安装 Docker Desktop 后，打开 Settings，确认：

- General 中启用 `Use the WSL 2 based engine`
- Resources / WSL Integration 中启用你的 Linux 发行版

检查：

```powershell
docker version
docker compose version
```

两个命令都能正常输出版本信息才继续。

## 4. 安装 Git

安装 Git for Windows 后检查：

```powershell
git --version
```

如果仓库是私有仓库，建议提前登录 GitHub CLI、配置 SSH，或者使用有权限的 HTTPS 凭据。

## 5. 下载项目

在 PowerShell 中：

```powershell
git clone https://github.com/luolidong/a-share-realtime-screener.git
cd a-share-realtime-screener
```

私有仓库如果 HTTPS 克隆失败，请改用你已配置权限的 SSH 地址。

## 6. 启动项目

```powershell
docker compose up --build -d
```

查看状态：

```powershell
docker compose ps
```

正常情况下：

- `backend` 为 `healthy`
- `frontend` 为 `Up`

浏览器打开：

```text
http://127.0.0.1:8080
```

当前项目是手动查询模式。页面打开后不会每 15 秒自动刷新；需要数据时点击“立即查询”或“按当前条件查询”。

## 7. 验证后端

PowerShell：

```powershell
curl.exe http://127.0.0.1:8080/api/health
curl.exe http://127.0.0.1:8080/api/stocks
```

注意：PowerShell 里的 `curl` 可能是 `Invoke-WebRequest` 的别名，因此这里推荐明确使用 `curl.exe`。

如果 `/api/stocks` 返回：

```json
[]
```

表示当前没有股票同时满足全部条件，不是程序错误。

## 8. 验证实时 Provider

```powershell
docker compose exec backend python -c "from app.providers.akshare_provider import AkShareProvider; p=AkShareProvider(); q=p.get_realtime_quotes(); print('quotes', len(q)); print(q.head()); f=p.get_realtime_money_flow(); print('flows', len(f)); print(f.head())"
```

正常情况下应看到股票代码、名称、价格、换手率和资金流数据。

当前实现会构造满足最低换手率候选范围的实时快照，因此返回数量不要求等于全部 A 股数量。

## 9. 修改端口

默认是 8080。

PowerShell 临时设置端口：

```powershell
$env:APP_PORT="8090"
docker compose up --build -d
```

然后访问：

```text
http://127.0.0.1:8090
```

关闭当前 PowerShell 后，这个环境变量会失效。

## 10. 更新项目

```powershell
git pull
docker compose up --build -d
```

如果只是重启：

```powershell
docker compose restart
```

停止：

```powershell
docker compose down
```

查看日志：

```powershell
docker compose logs -f --tail=100
```

只看后端：

```powershell
docker compose logs -f --tail=100 backend
```

## 11. Windows 防火墙和局域网访问

本机浏览器访问 `127.0.0.1:8080` 一般不需要额外配置。

如果希望同一局域网里的其他设备访问，需要：

1. 找到 Windows 局域网 IPv4 地址：

```powershell
ipconfig
```

2. 假设地址是 `192.168.1.100`，其他设备访问：

```text
http://192.168.1.100:8080
```

3. 如果无法访问，检查 Windows Defender Firewall 是否允许 Docker Desktop / 8080 端口入站。

不要为了方便直接关闭整个 Windows 防火墙。

## 12. Docker Hub / 镜像拉取超时

如果看到类似：

```text
failed to pull image
TLS handshake timeout
context deadline exceeded
```

通常是 Docker Hub 网络问题，不是项目代码问题。

可以在 Docker Desktop 的 Docker Engine 配置可用镜像源，例如：

```json
{
  "registry-mirrors": [
    "https://docker.1ms.run"
  ]
}
```

保存并重启 Docker Desktop 后再执行：

```powershell
docker compose up --build -d
```

镜像源属于外部服务，是否可用会变化，应按当前网络环境选择。

## 13. 页面显示“数据源暂不可用”

先看后端日志：

```powershell
docker compose logs --tail=100 backend
```

如果是：

```text
RemoteDisconnected('Remote end closed connection without response')
```

通常表示东方财富公开接口主动断开连接，而不是 Windows 本身有问题。

当前项目已经做了多节点/路径 fallback 和浏览器兼容请求方式，但公开接口没有稳定性 SLA。

可以单独测试 Provider：

```powershell
docker compose exec backend python -c "from app.providers.akshare_provider import AkShareProvider; p=AkShareProvider(); print(p.get_realtime_quotes().head())"
```

如果 Provider 失败而 `/api/health` 正常，说明 FastAPI 服务本身没问题，故障在上游数据源。

## 14. WSL2 / Docker 常见问题

### Docker 命令不可用

确认 Docker Desktop 已启动：

```powershell
docker version
```

如果 client 有输出但 server 报错，通常是 Docker Desktop 还没完全启动。

### WSL2 异常

```powershell
wsl --shutdown
```

然后重新打开 Docker Desktop。

### 端口被占用

检查 8080：

```powershell
netstat -ano | findstr :8080
```

有占用时改用其他端口：

```powershell
$env:APP_PORT="8090"
docker compose up --build -d
```

### 修改代码后页面没变化

```powershell
git pull
docker compose up --build -d
```

然后浏览器按 `Ctrl + F5` 强制刷新。

## 15. 推荐的 Windows 使用流程

每天使用时通常只需要：

```text
打开 Docker Desktop
→ 在项目目录执行 docker compose up -d
→ 打开 http://127.0.0.1:8080
→ 需要时点击“立即查询”
```

如果项目已经在运行，通常不需要每天重新 build。

只有代码或依赖发生变化时才执行：

```powershell
docker compose up --build -d
```

## 16. 从零重装时最短步骤

```text
1. 安装 WSL2
2. 安装 Docker Desktop
3. 安装 Git
4. git clone 项目
5. cd 项目目录
6. docker compose up --build -d
7. 打开 http://127.0.0.1:8080
8. 点击“立即查询”
```
