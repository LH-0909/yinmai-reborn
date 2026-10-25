# 印脉重生 · HarmonyOS NEXT ArkTS Stage Starter

这是一个面向真实后端的 HarmonyOS NEXT（Stage 模型）客户端 starter，使用 ArkTS / ArkUI / ArkWeb。它**不是**一个已经编译、签名、上架或在真机上验证过的成品。

> **交付状态（诚实声明）**
> - 本交付物生成环境未检测到 DevEco Studio、HarmonyOS SDK、`hvigorw` 或 `hdc`，因此本工程**尚未编译、尚未签名、尚未在模拟器或真机运行**。
> - 本次检查时 `http://127.0.0.1:8000` 与 `http://127.0.0.1:5173` 均未监听，因此**没有做真实联调**。
> - 已做的验证仅限：JSON/JSON5 语法解析、路径与资源引用检查、权限与 Web 桥静态检查、REST 路径与源码对照。详见文末“本次验证”。
> - 任何界面状态都来自真实 HTTP 请求；没有内置“假成功”、模拟印谱或伪造 AI 结果。

## 1. 功能边界

### 已实现的原生能力

- 原生首页：调用真实 `GET /api/health`，显示数据库状态、后端 AI 状态原样 JSON、印谱/产物数量。
- 原生印谱库：调用真实 `GET /api/seals`，展示真实 `title`、`filename`、`created_at`、`source_kind`。
- 真实原图：把后端返回的 `original_url` 解析为实际图片 URL，用 ArkUI `Image` 加载。
  - 当前后端返回相对路径 `/api/files/{artifact_id}`，客户端以 API 根地址拼接。
  - 若后端未来返回绝对 `http(s)` URL，也会直接使用。
- 原生详情页：点击印谱卡片后调用真实 `GET /api/seals/{id}`，展示同一对象、原图与产物 URL 清单。
- 原生设置页：可编辑 API 根地址与 Web 工作台地址，保存到 Preferences（`@kit.ArkData`），重进应用仍生效。
- ArkWeb 工作台：加载真实 Web 前端，明确标注“嵌入网页，不是原生 AI”。
- 失败状态：连接失败、HTTP 非 2xx、JSON 结构错误、图片加载失败都会显示错误，不会伪造成功。

### 明确未实现

- 没有原生拍照/相册导入、原生图像修复、原生 AI 推理、原生 3D 视口或 STL 渲染。
- 没有原生上传、删除、重命名、处理或重建操作；这些仍由 Web 工作台承担。
- 没有账号、鉴权、多用户、离线缓存或数据同步。
- 没有把 Web 页面操作包装成原生能力，也没有注册 JavaScript Proxy / 任意 JS 桥。

## 2. 目录结构

```text
harmonyos/
├─ AppScope/
│  ├─ app.json5
│  └─ resources/base/
│     ├─ element/string.json
│     └─ media/app_icon.png
├─ entry/
│  ├─ build-profile.json5
│  ├─ hvigorfile.ts
│  ├─ oh-package.json5
│  ├─ obfuscation-rules.txt
│  └─ src/main/
│     ├─ module.json5
│     ├─ ets/
│     │  ├─ entryability/EntryAbility.ets
│     │  ├─ pages/Index.ets
│     │  ├─ pages/HomePage.ets
│     │  ├─ pages/SealDetail.ets
│     │  ├─ pages/SettingsPage.ets
│     │  ├─ pages/WorkbenchPage.ets
│     │  ├─ components/SealCard.ets
│     │  ├─ common/{Format,Theme,UrlUtils}.ets
│     │  ├─ model/Models.ets
│     │  └─ service/{ApiClient,SettingsRepository}.ets
│     └─ resources/base/
│        ├─ element/{color,string}.json
│        ├─ media/startIcon.png
│        └─ profile/{main_pages,network_config}.json
├─ hvigor/hvigor-config.json5
├─ build-profile.json5
├─ hvigorfile.ts
├─ oh-package.json5
└─ README.md
```

## 3. 后端与网络约定

### 3.1 REST 契约

客户端实际请求：

| 页面 | 方法 | 路径 | 用途 |
|---|---|---|---|
| 首页 | GET | `/api/health` | `database`、`ai`、`counts` |
| 首页 | GET | `/api/seals` | 印谱数组 |
| 详情页 | GET | `/api/seals/{id}` | 单个印谱对象 |

代码按以下结构解析（后端现有额外字段如 `sha256`、`database_engine` 会被保留或安全忽略）：

```json
{
  "database": "connected",
  "ai": {},
  "counts": { "seals": 0, "artifacts": 0 }
}
```

```json
[
  {
    "id": "uuid",
    "title": "印谱名",
    "filename": "upload.png",
    "created_at": "2026-01-01T00:00:00+00:00",
    "source_kind": "user_upload",
    "original_url": "/api/files/{artifact_id}",
    "artifacts": [
      {
        "id": "artifact_id",
        "kind": "original",
        "url": "/api/files/{artifact_id}",
        "metadata": {}
      }
    ]
  }
]
```

`original_url` 为空或加载失败时，卡片显示失败占位，不会悄悄换成内置图。

### 3.2 设备 localhost 问题（必须阅读）

手机/真机上的 `127.0.0.1` 指向**手机自身**，不是运行后端和 Web 的电脑。默认值保留为：

- API：`http://127.0.0.1:8000`
- Web：`http://127.0.0.1:5173`

它们只作为本机回环示例。真机必须改成电脑在同一局域网内的 IPv4，例如：

- API：`http://192.168.1.23:8000`
- Web：`http://192.168.1.23:5173`

两台设备必须同一 Wi-Fi；Windows 防火墙需允许 8000 和 5173；后端与 Vite 都要监听 `0.0.0.0`，不能只监听 `127.0.0.1`。部分模拟器可能用 `10.0.2.2` 映射电脑，需按实际模拟器网络验证。

查找电脑 IPv4（Windows）：

```powershell
ipconfig
```

启动后端时监听所有网卡（在后端项目目录、按项目现有环境执行）：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

启动 Web（在前端项目目录、按项目现有依赖执行）：

```bash
pnpm dev --host 0.0.0.0
```

后端连接真实 MySQL，缺失数据库时不会自动回退到 SQLite/mock；启动失败属于预期行为。

### 3.3 CORS 额外注意

现有后端 CORS 白名单只包含 `http://127.0.0.1:5173` 与 `http://localhost:5173`。如果 Web 前端从设备以 `http://<局域网IP>:5173` 打开，并且页面内使用**绝对 API 地址**请求 8000 端口，浏览器会因 Origin 是局域网地址而被 CORS 拦截。

两种解决方向（任选其一，均需在后端/前端侧另行处理后重新验证）：

1. Web 页面使用相对 `/api`，由 Vite 开发代理转发到 `127.0.0.1:8000`（同源，无 CORS）；
2. 后端 CORS 明确增加实际的 `http://<电脑局域网IP>:5173` Origin。

本 starter 不修改后端，也不绕过浏览器同源策略。

## 4. 导入、编译与签名

### 4.1 环境建议

- DevEco Studio 5.0 或兼容版本。
- HarmonyOS NEXT SDK API 12（工程 `compatibleSdkVersion` 为 `5.0.0(12)`）。
- hvigor 配置使用 `5.0.2`，见 `hvigor/hvigor-config.json5`。
- 目标设备：phone / tablet。

如果本机安装的是其他 SDK/hvigor 版本，让 DevEco 完成 SDK 同步，并按 IDE 提示把 `build-profile.json5` 的 `compatibleSdkVersion` 与 `hvigor/hvigor-config.json5` 的版本调整为本机实际版本；不要在不确认版本的情况下照抄。

### 4.2 导入

1. 打开 DevEco Studio。
2. `File > Open`，选择本目录 `outputs/yinmai-reborn/harmonyos`（不是仓库根目录）。
3. 等待 `ohpm` / hvigor 同步。首次导入会生成 `oh_modules`、`.hvigor`、`local.properties` 等本机文件。
4. 在 `File > Project Structure > Project` 中确认 SDK 与 `compatibleSdkVersion`。
5. 若 IDE 报资源或 API 版本不匹配，先解决版本问题，不要直接关闭检查。

本交付未附带 `hvigorw` / `hvigorw.bat` 包装器、`local.properties` 或本机 SDK 路径；这些由 DevEco 在导入/同步时生成。README 不声称命令行构建在本环境可用。

### 4.3 构建

在 DevEco Studio 中：

1. 选择 `entry` 模块与 `default` 产品。
2. `Build > Build Hap(s)/APP(s) > Build Hap(s)`。
3. 成功产物通常位于 `entry/build/default/outputs/default/`（以 IDE 实际输出为准）。

命令行构建需先具备 DevEco 生成的 hvigor 包装器与可用的 SDK。本环境没有这些前置条件，未执行构建。

### 4.4 签名

1. 连接真机或启动模拟器。
2. `File > Project Structure > Project > Signing Configs`。
3. 勾选自动签名（通常需要登录华为开发者账号并由 DevEco 生成调试证书）。
4. 不要把自动生成的证书、私钥、profile 或密码提交到仓库；`.gitignore` 已忽略常见签名产物。

本工程不包含任何证书、私钥、口令或签名配置。没有签名时不能把“构建成功”当作“可安装”。

## 5. 设备验证步骤

1. 电脑启动真实 MySQL、后端（8000）和 Web（5173），确认二者监听 `0.0.0.0`。
2. 在电脑浏览器验证：
   - `http://127.0.0.1:8000/api/health` 返回 `database: connected`；
   - `http://127.0.0.1:8000/api/seals` 返回真实数组；
   - `http://127.0.0.1:5173` 可打开。
3. 手机与电脑同一 Wi-Fi；`hdc list targets` 能看到设备。
4. 安装并启动应用，进入“设置”，填写电脑局域网 IP 的 API 与 Web 地址，保存。
5. 回到“首页”，点击“刷新”：
   - 只有真实 `/api/health` 成功且返回 `database: "connected"` 时才显示“数据库已连接”；
   - 印谱数量与列表来自 `/api/seals`；
   - 原图应来自 `/api/files/...`；
   - 可对比电脑浏览器与后端访问日志、数据库计数。
6. 点击任一张印谱卡片，确认详情来自 `GET /api/seals/{id}`。
7. 切到“工作台”，确认顶部明确标注 ArkWeb 嵌入；真实上传/修复/AI 操作应在网页中完成。
8. 反向验证：
   - 停掉后端，刷新首页，应显示连接失败，不能保留“已连接”假状态；
   - 填错 IP，应显示失败；
   - 让 API 返回非 2xx，应显示 HTTP 状态；
   - 使原图 URL 不可用，应显示原图加载失败。

## 6. 安全说明

- `module.json5` 仅声明 `ohos.permission.INTERNET`，没有位置、相机、麦克风、存储等权限。
- ArkWeb 开启 JavaScript 仅为运行真实 Vue 前端；**没有** `registerJavaScriptProxy` 或任意原生桥。
- `fileAccess(false)`、`geolocationAccess(false)`、`mixedMode(MixedMode.None)`。
- 没有覆盖 SSL 错误回调，没有信任无效证书，没有关闭同源策略。
- `network_config.json` 为本地开发后端显式允许 HTTP 明文流量。它不关闭 HTTPS 校验证书，但会允许明文流量，因此**只适合开发/局域网演示**。正式部署必须改为 HTTPS、收紧或移除该配置。
- 设置只保存两个地址，不保存账号、口令、Token 或数据库凭据。

## 7. 已知限制与后续原生任务

1. **未编译、未签名、未真机验证**：本环境缺少 DevEco/SDK/hvigor/hdc；不能声称可运行。
2. **无真实联调**：检查时 8000/5173 未监听，无法验证实际返回、图片与 Web 加载。
3. **原生 AI/3D 未实现**：工作台是 ArkWeb 嵌入的真实网页，不是原生能力。
4. **原生上传/处理未实现**：上传、修复、重建、AI 调用仍留在 Web。
5. **CORS 风险**：见 3.3；需要前端代理或后端放开实际 LAN Origin。
6. **明文 HTTP**：开发配置允许 cleartext；生产必须改用 HTTPS。
7. **列表无分页**：后端当前最多返回 300 条，原生页一次性 `ForEach`；数据量大时需要 LazyForEach/分页。
8. **原图 URL 假设**：相对 `original_url` 按 API 根地址拼接；若图片由另一个域名提供，需改成显式媒体根地址。
9. **Preferences 非加密**：只存非敏感地址；不要扩展为存凭据。
10. **UI 未做设备矩阵验证**：手机/平板、深浅色、字体缩放均未实测。
11. **版本差异**：API 12 与 hvigor 5.0.2 的兼容性需用目标 DevEco 实际编译确认；新版本可能需要迁移。

建议的后续原生任务（按优先级）：

- 在目标 DevEco 中完成首次编译，修复 SDK/ArkTS 兼容问题；
- 用真实后端做首页、详情、Web 工作台联调并留存日志；
- 增加原生上传与处理任务状态（只在后端真实支持后）；
- 评估原生 3D/STL 渲染能力，不从 Web 伪造；
- 增加分页、下拉刷新、离线失败提示与可访问性；
- 正式环境改用 HTTPS，移除开发期 cleartext 配置。

## 8. 本次验证

已在生成环境执行：

- 对全部 `.json` / `.json5` 做严格 JSON 解析检查；
- 检查 `module.json5` 只声明 INTERNET 权限；
- 检查未出现 `registerJavaScriptProxy`、`onSslErrorEventReceive`、明文口令或签名材料；
- 对照真实后端源码确认健康检查、列表、详情路径与 `original_url` 相对路径行为；
- 检查页面 profile 包含 `pages/Index` 与 `pages/SealDetail`；
- 检查启动图标/应用图标为有效 PNG。

**未执行**：DevEco 同步、ArkTS 编译、HAP 构建、签名、安装、真机/模拟器运行、真实 API 请求。因此本 README 不把“静态检查通过”表述为“工程已可运行”。
