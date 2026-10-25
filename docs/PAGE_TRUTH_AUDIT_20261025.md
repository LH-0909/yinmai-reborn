# 逐页真实性核对与取舍建议 · 2026-10-25

> 起因：用户认为“只有有据知识图谱、印谱数据库、文化溯源有用，其余都是假的，可以删”。
> 本文回答两件事：**哪些页真的没有效果**、**删到什么程度会伤到赛题硬指标**。
> 本轮只出清单，不改代码、不删页面。

## 判定标准

不看观感，只问三个问题：

1. 打开时是否从后端拿到真实数据（MySQL 或 `data/` 目录）。
2. 操作后是否真的写库、调用模型或产出文件（STL、图像、记录）。
3. 宣称的能力是否真的存在（模型是否 `configured`，权重是否可用）。

三者都成立记为「真」，只有展示与文案、或能力明确不可用记为「假」，链路真但宣称能力未到位记为「半真」。

## 总表：19 条路由

| # | 路由 | 组件 | 真实来源 | 判定 |
|---|---|---|---|---|
| 1 | `/` | `museum/Home.vue` | `/api/heritage/overview`、`/api/studio/state` | 真 |
| 2 | `/catalog` | `museum/Catalog.vue` | `/api/heritage/catalogue`，125 条 | 真 |
| 3 | `/catalog/:slug` | `museum/Detail.vue` | 同上，含 125 张馆藏主图 | 真 |
| 4 | `/culture` | `museum/Culture.vue` | `/api/heritage/*`、`/api/knowledge` | 真 |
| 5 | `/graph` | `graph/GraphPage.vue` | `/api/graph`，555 节点 / 1013 关系 | 真 |
| 6 | `/workspace` | `pages/Home.vue` | `/api/seals`、`/api/events` | 半真（默认参考态） |
| 7 | `/upload` | `pages/Upload.vue` | `POST /api/seals` 真落库 | 真 |
| 8 | `/recognition` | `pages/Process.vue` | `/api/seals/{id}/process`、`/ai` | 半真（OpenCV≠AI 识别） |
| 9 | `/restoration` | `pages/Process.vue` | 同上，产出 `repair` 版本 | 半真（无修复模型） |
| 10 | `/reconstruction` | `pages/Reconstruct.vue` | `POST /api/seals/{id}/reconstruct` 真出 STL | 真 |
| 11 | `/manufacture` | `pages/Manufacture.vue` | `POST /api/seals/{id}/records` 真写库 | 真 |
| 12 | `/knowledge` | `pages/Knowledge.vue` | `/api/knowledge`，4 条有出处 | 真（内容薄） |
| 13 | `/projects` | `pages/Projects.vue` | `/api/seals`，10 个印谱 / 28 个产物 | 真（内容薄） |
| 14 | `/account` | `museum/Account.vue` | `/api/studio/favorites`、`/profile` | 真（收藏为 0） |
| 15 | `/customize` | `museum/Customize.vue` | `POST /api/studio/compose`、`/designs` | 半真（无篆刻风格模型） |
| 16 | `/lab` | `pages/Lab.vue` | `/api/lab/status` 真有权重 | 实验（已自标） |
| 17 | `/experience` | `museum/Experience.vue` | **无任何后端调用** | **假** |
| 18 | `/assistant` | `pages/Assistant.vue` | 有 `/api/chat` 但模型未配置 | **假** |
| 19 | `/font` | `pages/FontLab.vue` | `/api/font/status` 明确无风格模型 | **假** |

合计：真 11、半真 4、自标实验 1（`/lab`，有其权重，单独计数）、假 3，共 19。

## 三个假页的实证

### 交互体验 `/experience`

- `museum/Experience.vue` 全文 13 行，只有 5 张概念卡和一个 `show()` 弹窗，没有任何 `api()` / `fetch()`。
- 点击后弹窗文案写死为「当前展厅画面来自您提供的视觉参考」（`Experience.vue:5`），没有 AR、没有 3D 场景、没有语音。
- 入口有三处：`museum/MuseumShell.vue:12` 侧栏「交互体验」、`museum/Home.vue:18` 首页第四张卡、`main.ts:6` 路由表。

### AI 文化助手 `/assistant`

- `backend/app/main.py:454`：没有模型 key 时直接返回 503「文化助手尚未接入可用的大模型账户；没有生成AI回答」。
- `GET /api/health` 实测：`ai.culture.configured = false`、`state = unavailable`。
- 页面本身是诚实的（不编造回答），但对评委就是一条走不通的路。

### 印谱字形风格工坊 `/font`

- `GET /api/font/status` 实测：`seal_model_available: false`、`font_file_export_available: false`。
- 唯一模型 `noto-pipeline-demo` 标注 `demo_only: true`，是宋体栅格化流程验证（816 字，前景 IoU 0.559），不是篆刻风格。
- 训练数据侧只有 4 个待归类框、0 个已核对汉字（`styles[0]`），离“输入汉字生成篆刻字形”还差人工标注与训练。
- 入口：`WorkspaceShell.vue:34` 两处链接、`museum/Account.vue:14`、`museum/Dialogs.vue:34`。

## 四个半真页的问题（不是假的，是没做到自己宣称的水平）

| 页面 | 宣称 | 实际 | 证据 |
|---|---|---|---|
| `/workspace` | 处理工作台 | 默认选中「界面参考（不可处理）」，按钮灰 | `WorkspaceShell.vue:33` 的 `__reference__` 选项 |
| `/recognition` | AI 智能识别 | OpenCV 图像处理，产出 `extract`，不是古篆 OCR | `README.md` 自述、`health.ai.recognition.configured=false` |
| `/restoration` | AI 古印修复 | 无 TorchScript 修复权重，只有 OpenCV `repair` | `health.ai.restoration.configured=false`，reason「未提供经训练的TorchScript权重」 |
| `/customize` | 个性定制 | 真做规范字排版并落库，但没有篆刻风格模型 | `museum/state.ts:18` 提示「此结果没有使用篆刻风格模型」 |

这四条是**“看起来假”的主因**：真实链路被默认参考态和灰按钮挡住了，AI 能力又确实没接上。

## 关键风险：删工作台会打掉赛题硬指标

赛题（2026「华为杯」辽宁省 ICT 大赛附件 3，见 `docs/PROGRESS.md:7`）的要求与当前证据：

| 要求 | 现状 | 证据 |
|---|---|---|
| 纯软件须有交互界面 | 满足 | 19 条路由、桌面与手机截图 |
| 核心数据须在真实数据库存取 | 满足 | MySQL 8.4：125 条馆藏、555 节点、10 个印谱、28 个产物、7 个方案 |
| **必须实际接入 AI 模型** | **未满足** | `health` 中 recognition / restoration / culture 三处 `configured:false`；字体风格模型 `seal_model_available:false` |
| 鼓励 HarmonyOS | 有源码，未编译签名 | `harmonyos/`，README 自述「未编译、未签名、未上机」 |

结论：**图谱、目录、文化三页只证明“数据真”，证明不了“系统能干活”**。`/upload → /recognition → /restoration → /reconstruction → /manufacture` 这条链是全站唯一能证明「真实落库 + 可制造」的部分（真 STL、真制作记录），把它一起删掉，答辩时「AI 在哪里、制造在哪里」无法回答。

## 建议

按代价从小到大，三档任选：

**A 档（最小，约 5 个文件）**：只删三个假页。
- 删 `museum/Experience.vue`、`pages/Assistant.vue`、`pages/FontLab.vue`
- 清 `main.ts:6` 三条路由、`MuseumShell.vue:12` 导航、`Home.vue:18` 第四张卡、`WorkspaceShell.vue:17/25/34/35`、`App.vue:4`、`Account.vue:14`、`Dialogs.vue:34`

**B 档（推荐，A + 两个文件）**：再把工作台默认态改成真实印谱，去掉 `__reference__` 默认选中，让上传、STL、制作记录一进去就能点。

**C 档（B + 补硬指标）**：把「AI 智能识别 / AI 修复」按实际能力改名，或接入一个真的 TorchScript 修复/识别权重；否则「必须实际接入 AI 模型」这条始终空着，删页面不解决。

## 复核与回滚

- 复核命令：`Invoke-RestMethod http://127.0.0.1:8001/api/health`、`/api/heritage/overview`、`/api/graph`、`/api/knowledge`、`/api/font/status`、`/api/lab/status`。
- 当前服务：Web `127.0.0.1:5173`、API `127.0.0.1:8001`、MySQL `127.0.0.1:13306`，`database=connected`。
- 本地已有初始提交 `e97418b`（1130 文件），任何删除都可以用 `git checkout -- .` 或 `git revert` 找回。
- 本轮未修改任何源码，未删除任何文件。
