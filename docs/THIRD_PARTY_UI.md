# 八页 UI 的素材与依赖来源

八张参考图由用户从本机提供，原件在 `references/20261021/`。原图画作、刷字标题、印章插画、纹样、图标和边框均只用于本项目的视觉复刻；其第三方权利来源未独立核验，不附加可公开商用的授权承诺。

`docs/ui-assets-20261021.json` 记录源图坐标、各个资源的用途、最终 SHA256 与边框映射。47 个面板边框仅包含外缘与角饰，中心透明。表单、筛选、按钮、路由、弹窗、收藏与实际处理结果由代码实现。

Web 字体 Noto Serif SC 使用 SIL Open Font License 1.1，许可见 `frontend/public/assets/museum/NotoSerifSC-OFL.txt`。该文件来自官方 Google Fonts 仓库的字体目录；本轮从已安装的 Noto Serif SC 字体制作 WOFF2，不伪造原 UI 所用字体的身份。

Tabler Icons 与 Three.js 使用 MIT 许可，见本目录的 `licenses/`。GitHub 原始仓库：

- https://github.com/tabler/tabler-icons
- https://github.com/mrdoob/three.js
- https://github.com/google/fonts/tree/main/ofl/notoserifsc

资源重建入口：`python scripts/rebuild_ui_assets.py --source-dir references/20261021`。只读取本机参考图并写入本机资源与生成映射，不请求外部图像服务。

## 三维知识图谱参考 · 2026-10-22

视觉方向与场景技术参考 [cdeust/neural-graph-visualizer](https://github.com/cdeust/neural-graph-visualizer)，包括 `ui/js/core/scene.js`、`ui/js/visual/nodes.js`、`edges.js` 与 `effects.js`。上游MIT许可及署名完整保存在 `licenses/neural-graph-visualizer-MIT.txt`。Vue组件与本项目真实业务数据接线在 `frontend/src/graph/`。上游示例数据、Claude插件和MCP服务未引入。参考原图仅作为QA输入，未作为整页背景冒充界面。

## 印稿研读参考 · 2026-10-23

内容组织参考[中国篆刻：方寸之间大有天地](https://storymaps.arcgis.com/stories/08dbd922e8be475ba88f2f30566ecfe8)公开正文；动态嵌入页面未完整验证。研读交互参考[墨识](https://github.com/Gezelli-z/moshi)的KnowledgeGraph.jsx与graphConfig.js，并改写为Vue组件；MIT许可见`licenses/moshi-MIT.txt`，没有引入其演示识别数据、服务或插件。

新增[Apache ECharts](https://github.com/apache/echarts)6.1.0，使用模块化Graph、Bar与SVG渲染。Apache-2.0许可和NOTICE保留在`licenses/echarts-Apache-2.0.txt`及`licenses/echarts-NOTICE.txt`。传递渲染依赖的许可另存同目录。

14张印稿来自[篆刻印稿数据库](https://yingaoku.cn/)已选择条目，精确页面/图像URL和SHA-256见`frontend/public/assets/seal-previews/manifest.json`。仅作为本机学习研读预览，没有新增公开商用或模型训练授权，不把网页记载当作文物鉴定。

## 官方馆藏照片与钤本 · 2026-10-23

接入故宫博物院3条明确藏品页（233558、233652、233579），每件各一张官方实物照片及钤本，按原页面caption、文物号、节点ID和SHA-256对应。来源清单为`frontend/public/assets/seal-previews/museum-manifest.json`；保留完整图像及原水印，不将网站图片当作开源素材，不新增公开商用或训练授权。它们没有与原14条文献印稿、8张UI构图参考混作“真实馆藏”。
