# Hermes 优化指南（中文简版）

> [English 完整版](./README.md) · 本页是入口摘要，章节正文仍为英文。

实用指南 + 可安装制品（Skills、配置模板、基础设施脚本），针对 [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)（v0.10.0+）。

## 一键起步

```bash
# 新建 Debian 12 / Ubuntu 24.04 VPS 上运行
curl -sSL https://raw.githubusercontent.com/OnlyTerp/hermes-optimization-guide/main/scripts/vps-bootstrap.sh | bash
```

或阅读 [docs/quickstart.md](./docs/quickstart.md)（5 分钟 Telegram 机器人）。

## 内容一览

- **21 章中文正文**（见 `part1` 到 `part21`） — LightRAG、Telegram、MCP、安全、可观测性、远程沙箱
- **13 个可安装 Skill**（`skills/`） — 审计、备份、依赖扫描、成本报告、Telegram 分类、PR 审查、收件箱分类、Hermes 周报、垃圾过滤、会议准备 等
- **5 套生产配置模板**（`templates/config/`） — minimum / telegram-bot / production / cost-optimized / security-hardened
- **基础设施**（`templates/compose/`, `templates/caddy/`, `templates/systemd/`, `scripts/`） — Langfuse 自托管、Caddy 反代、systemd 硬化、VPS 引导脚本
- **Mermaid 架构图**（`diagrams/`）
- **可复现基准测试**（`benchmarks/`） — 12 个模型 × 5 个任务，含方法论
- **生态目录**（[`ECOSYSTEM.md`](./ECOSYSTEM.md)） — MCP 服务器、编码代理、仪表板插件
- **交互式配置向导**（[`docs/wizard/`](./docs/wizard/)） — 浏览器内生成 `config.yaml`

## 推荐阅读顺序

1. 想最快跑通 Telegram 机器人 → [docs/quickstart.md](./docs/quickstart.md)
2. 想了解架构 → [diagrams/architecture.md](./diagrams/architecture.md)
3. 想省钱 → [part20-observability.md](./part20-observability.md) 的 "Cost-routing playbook"
4. 想上生产 → [docs/reference-architectures/](./docs/reference-architectures/) 选一个最接近的
5. 用户面公开部署 → [part19-security-playbook.md](./part19-security-playbook.md) 必看

## 许可与贡献

MIT。欢迎 Issue / PR，详见 [CONTRIBUTING.md](./CONTRIBUTING.md)。
