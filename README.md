# A股实时条件选股器

根据实时行情、资金流和最新财务数据自动筛选符合条件的 A 股股票。

## 当前默认规则

- 换手率：10% ~ 30%
- 实时/当日主力资金净流入：> 1 亿元
- 归母净利润同比增长率：>= 30%
- 营业总收入同比增长率：>= 30%

所有阈值都可以在 `config.yaml` 中修改。

## 数据源

第一版使用 AkShare 聚合公开数据：

- A 股实时行情：用于价格、涨跌幅、换手率
- 个股资金流排行：用于主力净流入
- 东方财富业绩报表：用于归母净利润同比、营业总收入同比

> 注意：公开免费数据通常属于准实时数据，延迟和可用性由上游数据源决定。如果后续需要交易级低延迟数据，可新增付费数据 Provider，不需要修改筛选引擎。

## 安装

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

## 运行 Web 看板

```bash
streamlit run app.py
```

打开终端显示的本地地址即可使用。

## 命令行扫描

```bash
python -m src.cli
```

## 配置

`config.yaml`：

```yaml
rules:
  turnover_min: 10
  turnover_max: 30
  net_inflow_min_cny: 100000000
  net_profit_yoy_min: 30
  revenue_yoy_min: 30
```

## 项目结构

```text
.
├── app.py
├── config.yaml
├── requirements.txt
├── src/
│   ├── cli.py
│   ├── config.py
│   ├── models.py
│   ├── screener.py
│   └── providers/
│       ├── base.py
│       └── akshare_provider.py
└── tests/
    └── test_screener.py
```

## 下一阶段

- 缓存财报数据，避免每次盘中刷新重复下载
- 定时自动刷新和扫描历史记录
- 增加行业、概念、市值、量比、涨停等条件
- 支持自选规则组合与保存
- 增加数据源健康检查和备用 Provider
- 支持 Telegram/邮件/微信等命中提醒
