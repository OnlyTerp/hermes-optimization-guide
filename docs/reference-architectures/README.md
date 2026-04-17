# Reference Architectures

Four opinionated "steal this" blueprints — each includes every file you need to run it, every cost line-item, every scaling ceiling, and the honest tradeoffs.

| Blueprint | Good for | Cost/mo | Scale ceiling |
|---|---|---:|---|
| [Homelab](./homelab.md) | On your own hardware, fully private | ~$0 (electricity) + keys | Single user, best privacy |
| [Solo Developer](./solo-developer.md) | VPS + daily-driver phone bot | ~$5 infra + $20–60 LLM | You + personal projects |
| [Small Agency](./small-agency.md) | 2–6 devs, multiple clients | ~$25 infra + $200–800 LLM | A few teams sharing |
| [Road Warrior](./road-warrior.md) | Phone drives beefy cloud box | ~$5 always-on + $0–50 on-demand | Anywhere with cell |

All four use the files under [`templates/`](../../templates/) and [`skills/`](../../skills/) — they differ in *which ones* and *where they run*. Pick the closest, then edit.
