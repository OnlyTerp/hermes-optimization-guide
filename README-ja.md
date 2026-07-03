# Hermes 最適化ガイド（日本語ショート版）

> [英語版はこちら](./README.md) · このページは入口の要約。本文の章は英語のまま。 · 最終同期：2026-07-03

[NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)（**v0.18.0 “The Judgment Release”（v2026.7.1）** まで反映。Mixture-of-Agents のファーストクラスモデル化、エビデンスに基づくタスク検証、ネイティブデスクトップアプリ、NVIDIA ローカルハードウェアを含む）向けの実戦ガイド + インストール可能な成果物（Skills・設定テンプレ・インフラスクリプト）。

## ワンコマンドで起動

```bash
# 新しい Debian 12 / Ubuntu 24.04 VPS で実行
curl -sSL https://raw.githubusercontent.com/OnlyTerp/hermes-optimization-guide/main/scripts/vps-bootstrap.sh | sudo bash
```

もしくは [docs/quickstart.md](./docs/quickstart.md)（5 分で Telegram Bot）を参照。

## v0.17 / v0.18 の新機能ハイライト

**v0.18.0 “Judgment”**（[part26](./part26-moa-verification.md)）：

- **Mixture-of-Agents がファーストクラスのモデルに** — 各 MoA プリセットが `moa` プロバイダ配下の選択可能な仮想モデルになり、参照モデルごとの推論がラベル付きブロックで表示、アグリゲータの回答はライブでストリーミング。`/moa` はワンショットのショートカットに
- **エージェントが作業を証明する** — コーディングタスクの検証エビデンス（成功を主張するのではなく、プロジェクトのチェックを実際に実行）、`/goal` の完了コントラクト、`/goal wait <pid>`、`pre_verify` フック
- **`/learn` + `/journey` による自己改善** — ディレクトリ / URL / ワークフローから再利用可能なスキルを抽出し、学習内容をタイムラインで閲覧・編集・削除。デスクトップには操作できるメモリグラフを追加
- **バックグラウンドのサブエージェント・ファンアウト** — `delegate_task` が並列バックグラウンドサブエージェントを起動し、全完了後に 1 ターンへ集約。チャットはブロックされない
- **デスクトップがコーディングコックピットに** — プロファイルごとの Projects（サイドバー、コーディングレール、レビューペイン、worktree 管理）、マルチターミナルパネル、チャット内 PR 風 diff
- **チーム運用** — ゲートウェイの scale-to-zero（ドレイン協調つき）、`/etc/hermes` による管理者固定スコープ、1 ゲートウェイでのマルチプロファイル多重化、cron 継続実行
- **Google Vertex AI プロバイダ**（OAuth2 トークン自動発行・更新）。Gemini-CLI OAuth プロバイダは削除 — 移行ガイドは [part9](./part9-custom-models.md)

**v0.17.0 “Reach”**（[part15](./part15-new-platforms.md) ほか）：

- **iMessage via Photon Spectrum、Mac 不要** — `hermes photon login` で青い吹き出しへ。公式 WhatsApp Business Cloud API アダプタと Raft エージェントネットワークチャネルも追加
- **バックグラウンドサブエージェント** — `delegate_task(background=true)` が即座にハンドルを返し、完了時に結果が会話へ戻る
- **デスクトップアプリの大幅強化** — キーバインド再設定、ネイティブ OS 通知、サブエージェントのウォッチウィンドウ、VS Code Marketplace テーマ、リサイズ可能なターミナルペイン
- **ダッシュボードの成熟** — ブラウザ内のフルプロファイルビルダー（モデル + Skills + MCP）、刷新された Skills Hub（プレビュー + セキュリティスキャン）、強化されたダッシュボード認証
- **`image_generate` が画像編集に対応**（image-to-image）。Automation Blueprints が生の cron 構文をガイド付きフォームに置き換え。`memory` ツールにアトミックなバッチ操作を追加
- **Telegram リッチメッセージ**（Bot API 10.1、デフォルト有効）、MCP elicitation（ツール実行中にどのサーフェスでも問い合わせ可能）

## 主なコンテンツ

- **27 章の本文**（`part1`〜`part26` + この README） — v0.18 MoA / 検証 / `/learn`、v0.17 iMessage（Photon）、v0.16 デスクトップアプリ、NVIDIA / DGX Spark ローカル実行、マルチエージェント Swarm、`/undo`、あいまい検索モデルピッカー、Grok OAuth、`hermes proxy`、Kanban、`/goal`、Checkpoints v2、Curator、TUI、プラグイン、LightRAG、Telegram、MCP、セキュリティ、可観測性、リモートサンドボックス
- **13 個のインストール可能 Skill**（`skills/`） — 監査、バックアップ、依存スキャン、コストレポート、Telegram トリアージ、PR レビュー、受信トレイ整理、Hermes 週報、スパムフィルタ、会議準備 など
- **5 つのプロダクション設定テンプレ**（`templates/config/`） — minimum / telegram-bot / production / cost-optimized / security-hardened
- **インフラ一式**（`templates/compose/`, `templates/caddy/`, `templates/systemd/`, `scripts/`） — Langfuse セルフホスト、Caddy リバースプロキシ、systemd 強化、VPS ブートストラップ
- **Mermaid アーキテクチャ図**（`diagrams/`）
- **再現可能なベンチマーク**（`benchmarks/`） — 13 モデル × 5 タスク、手法込み
- **エコシステム目録**（[`ECOSYSTEM.md`](./ECOSYSTEM.md)） — MCP サーバ、コーディングエージェント、ダッシュボード拡張
- **対話式設定ウィザード**（[`docs/wizard/`](./docs/wizard/)） — ブラウザ内で `config.yaml` を生成

## 読む順番の目安

1. 最速で Telegram Bot を動かしたい → [docs/quickstart.md](./docs/quickstart.md)
2. アーキテクチャを把握したい → [diagrams/architecture.md](./diagrams/architecture.md)
3. コストを下げたい → [part20-observability.md](./part20-observability.md) の "Cost-routing playbook"
4. 本番運用したい → [docs/reference-architectures/](./docs/reference-architectures/) から近いものを選ぶ
5. 公開エンドポイント → [part19-security-playbook.md](./part19-security-playbook.md) を必ず読む
6. ターミナルではなく GUI が欲しい → [part24-desktop-app.md](./part24-desktop-app.md)（Hermes デスクトップアプリ）
7. 自分の GPU でローカル実行したい → [part25-nvidia-local.md](./part25-nvidia-local.md)（RTX / DGX Spark）
8. 複数フロンティアモデルの合議 + 検証可能な完了が欲しい → [part26-moa-verification.md](./part26-moa-verification.md)（MoA、`/goal` 完了コントラクト、`/learn`）

## ライセンス・貢献

MIT。Issue / PR 歓迎。[CONTRIBUTING.md](./CONTRIBUTING.md) を参照。
