# Hermes 最適化ガイド（日本語ショート版）

> [英語版はこちら](./README.md) · このページは入口の要約。本文の章は英語のまま。

[NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)（v0.10.0+）向けの実戦ガイド + インストール可能な成果物（Skills・設定テンプレ・インフラスクリプト）。

## ワンコマンドで起動

```bash
# 新しい Debian 12 / Ubuntu 24.04 VPS で実行
curl -sSL https://raw.githubusercontent.com/OnlyTerp/hermes-optimization-guide/main/scripts/vps-bootstrap.sh | sudo bash
```

もしくは [docs/quickstart.md](./docs/quickstart.md)（5 分で Telegram Bot）を参照。

## 主なコンテンツ

- **21 章の本文**（`part1`〜`part21`） — LightRAG、Telegram、MCP、セキュリティ、可観測性、リモートサンドボックス
- **13 個のインストール可能 Skill**（`skills/`） — 監査、バックアップ、依存スキャン、コストレポート、Telegram トリアージ、PR レビュー、受信トレイ整理、Hermes 週報、スパムフィルタ、会議準備 など
- **5 つのプロダクション設定テンプレ**（`templates/config/`） — minimum / telegram-bot / production / cost-optimized / security-hardened
- **インフラ一式**（`templates/compose/`, `templates/caddy/`, `templates/systemd/`, `scripts/`） — Langfuse セルフホスト、Caddy リバースプロキシ、systemd 強化、VPS ブートストラップ
- **Mermaid アーキテクチャ図**（`diagrams/`）
- **再現可能なベンチマーク**（`benchmarks/`） — 12 モデル × 5 タスク、手法込み
- **エコシステム目録**（[`ECOSYSTEM.md`](./ECOSYSTEM.md)） — MCP サーバ、コーディングエージェント、ダッシュボード拡張
- **対話式設定ウィザード**（[`docs/wizard/`](./docs/wizard/)） — ブラウザ内で `config.yaml` を生成

## 読む順番の目安

1. 最速で Telegram Bot を動かしたい → [docs/quickstart.md](./docs/quickstart.md)
2. アーキテクチャを把握したい → [diagrams/architecture.md](./diagrams/architecture.md)
3. コストを下げたい → [part20-observability.md](./part20-observability.md) の "Cost-routing playbook"
4. 本番運用したい → [docs/reference-architectures/](./docs/reference-architectures/) から近いものを選ぶ
5. 公開エンドポイント → [part19-security-playbook.md](./part19-security-playbook.md) を必ず読む

## ライセンス・貢献

MIT。Issue / PR 歓迎。[CONTRIBUTING.md](./CONTRIBUTING.md) を参照。
