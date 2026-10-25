# 古印裁切相关 GitHub 原始仓库调研

> 调研时间：2026-10-19（UTC）。范围：古印/篆书裁切、OCR、文档增强、可训练修复。
> 方法：只读公开仓库的 README、LICENSE、代码路径、文件树和发布链接；固定到调研时的 commit SHA。没有 clone、没有安装依赖、没有运行仓库代码、没有下载或加载权重、没有读取或上传 `D:/LH/raw_crops` 图片。
> 本文的“可用”仅指“公开文件存在且路径可核验”，不等于“已在 8GB RTX 4060 Ti 上跑通”，也不等于“在本项目数据上有效”。
> 证据等级：标“实测/文件树/代码”的为本次核验；标“估计/未测”的为工程判断；未标注的 README 数字仅作背景，不是我们的测量值。

## 0. 结论摘要

1. **没有任何一个被检查的仓库，能直接提供可信的“古玺/篆书印章”OCR 或修复权重。** 现代圆形公章与古玺篆书是两类不同的视觉/文字问题，不能混用。
2. 最接近“可训练修复”的是 **NAFNet**（MIT，通用配对图像修复）；它没有文档/印章先验，必须用我们自己的配对数据重训，当前没有这样的数据。
3. **DocDiff** 有 MIT 代码、仓库内权重和 1597 枚红印+二值掩膜数据集，但其印章权重是**去印章**方向；把 `seal_*` 权重当“修复印章”会抹掉笔画。它的掩膜数据只能作为分割/评估参考，且数据许可未知。
4. **PaddleOCR** 有现代公章文本检测/识别流水线（Apache-2.0 代码），支持弯曲印章文字；但训练/文档场景是合同、发票等现代印章，不是古篆。
5. 当前最该做的不是接模型，而是：清理 `._` 旁文件、按页分组做防泄漏划分、人工标注一个小规模古印测试集、先量化现有 OpenCV 红印掩膜。没有文字标签或完整修复真值时，不宣称OCR或真实缺损修复效果；可以定义独立的合成噪声实验，以原始裁图为目标，并明确其限制。

## 1. 必须守住的边界

- **现代公章 ≠ 古玺篆书。** 本报告把 PaddleOCR、TrOCR-Seal 明确标为“现代印章”参考；它们不构成古篆识别证据。
- **DocDiff 的印章能力是“去除”。** README 写的是文档去水印/去印章，数据集写的是“印章合成、印章消除”，权重命名为 `seal_denoiser.pth` / `seal_init.pth`。这些权重不能用于“保留印章笔画”的修复。可借鉴的是其残差扩散结构、红印+掩膜数据组织方式，而不是现成权重。
- **论文/README 数字不是我们的测量值。** DocEnTR 的 PSNR、NAFNet 的 GoPro/SIDD、PaddleOCR 的 Hmean、TrOCR-Seal 的 acc，都是作者在其数据上的声明；本报告未在任何本项目数据上复现。
- **缺失许可按 unknown 处理。** 仓库没有 LICENSE、数据没有单独条款、权重没有单独声明，都不等于“可以商用/可再分发”。

## 2. 本机环境核对（Codex独立复核后更新）

两套环境同时存在，最初简报描述的是后端环境，Harness检查的是默认Anaconda；均有实际依据。

| 环境 | 实测 | 用途 |
|---|---|---|
| 后端 `work/venv` | Python3.12、torch2.14.1+cpu | 已运行的FastAPI/OpenCV/可选TorchScript推理 |
| 默认Anaconda | Python3.8.5、torch1.13.1+cu116、CUDA可用 | 既有本机GPU依赖，没有修改其全局安装 |
| 隔离 `work/gpu-training` | 继承既有GPU包、CUDA11.6、RTX4060Ti | 实际完成400步小型CNN实验 |
| 模型目录 | 新增自训 `models/experimental/rgb-denoiser-v1.torchscript.pt` | 合成高斯噪声去除，尚未启用业务AI |
| 跨环境检查 | 同一导出在后端torch2.14.1加载，`[1,3,256,256]`数值探针最大误差0 | 仅验证该导出的加载与数值兼容，不外推第三方模型 |

训练与服务无需强行使用同一版本。应固定各自版本并逐个导出验证兼容性。详细记录在 `GPU_TRAINING.md`、`evidence/gpu-denoiser-v1/`。

已有修复插件输入为RGB0–1的`[1,3,256,256]`，识别插件只支持单字`[1,C]`；整印OCR仍需独立实现。现有业务处理仍以OpenCV为主，不能把本轮小型去噪实验称作真实缺笔恢复。

## 3. 选型总表（7 个入选 + 1 个明确排除）

| 仓库 | 角色 | CODE 许可 | 权重 | 数据 | 8GB 适配 | 结论 |
|---|---|---|---|---|---|---|
| [DocDiff](https://github.com/Royalvice/DocDiff) | 残差扩散文档增强；红印+掩膜数据 | MIT | 仓库内 4 个 `.pth` | 1597 红印+掩膜，Google Drive，许可 unknown | 推理应可；训练未测 | **方向相反**，只借结构/数据组织，不用印章权重 |
| [DocEnTR](https://github.com/dali92002/DocEnTR) | ViT 文档二值化/增强 | CC BY-NC 4.0 | Google Drive，部分缺失 | DIBCOSETS，独立许可 | 推理可；训练需减 batch | **二值掩膜候选，不能直接当RGB修复**；非商用 |
| [NAFNet](https://github.com/megvii-research/NAFNet) | 通用配对图像修复 | MIT + BasicSR Apache-2.0 | Google Drive/百度网盘 | 外部 GoPro/SIDD 等 | 推理可；width32 训练可试 | **最现实的可训练修复底座**，但需自有配对数据 |
| [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) | 现代公章检测/识别流水线 | Apache-2.0 | 百度模型库，许可未单独声明 | 不附带 | 可（CPU 也可） | 现代印章可用；**古篆无证据** |
| [TrOCR-Seal-Recognition](https://github.com/Gmgge/TrOCR-Seal-Recognition) | 现代公章端到端 OCR | **无 LICENSE** | 百度/Google Drive，ONNX | 网页抓取+付费 API 标注+ICDAR | 推理可；训练需减 batch | **许可阻断**，只能做技术参考 |
| [character-Evolution-Dataset (EVOBC)](https://github.com/RomanticGodVAN/character-Evolution-Dataset) | 甲骨/金文/篆书字形演化数据 | 无代码；数据 CC BY-NC-SA 4.0 | 无 | 元数据在仓库，图像在 HuggingFace | 数据可；训练不适用 | **仅数据参考**，非商用+相同方式共享 |
| [Chronicles-OCR](https://github.com/VirtualLUOUCAS/Chronicles-OCR) | 七体字跨时代 VLM 评测基准 | Apache-2.0 | 无 | HuggingFace/ModelScope，research-only | 7B VLLM **不适合** 8GiB | **仅评测参考**，不是实现来源 |
| [Art-of-Chinese-Seal-Engraving](https://github.com/jingrong-zhang/Art-of-Chinese-Seal-Engraving) | 印章篆刻叙事看板 | Apache-2.0 | 无 | 上海图书馆开放数据 | 不适用 | **排除**：Dash 演示，无 OCR/修复模型 |

## 4. 逐仓库核验

### 4.1 DocDiff — 代码与数据都真实，但“印章”是去除方向

- 仓库：<https://github.com/Royalvice/DocDiff>
- 固定提交：`f422a3af10657eeabeca90f2e862d88c72725845`（2024-08-22，`main`）
- 关键证据：[README.md](https://github.com/Royalvice/DocDiff/blob/f422a3af10657eeabeca90f2e862d88c72725845/README.md)、[conf.yml](https://github.com/Royalvice/DocDiff/blob/f422a3af10657eeabeca90f2e862d88c72725845/conf.yml)。
- 实际可用：
  - 代码：`main.py`、`model/DocDiff.py`、`src/trainer.py`、`schedule/diffusionSample.py`、`conf.yml`。
  - 权重：仓库内 `checksave/denoiser.pth`、`init.pth`、`seal_denoiser.pth`、`seal_init.pth`，各约 16.2–16.8 MB（文件树可核验，未加载）。
  - 数据：README 给出 1597 枚中文红印 + 对应二值掩膜的 Google Drive 链接；**不在仓库内**。
- 许可证据：
  - 代码：MIT，`LICENSE`（Copyright 2023 Zongyuan Yang）<https://github.com/Royalvice/DocDiff/blob/f422a3af10657eeabeca90f2e862d88c72725845/LICENSE>
  - 权重：仓库内 `.pth` 没有单独许可条款；只能确认“文件随 MIT 仓库发布”，**权重许可本身未单独声明**。
  - 数据：README 仅说明大部分来自 ICDAR 2023 Seal Title、少数内部图片；**没有数据许可**。不能把 MIT 代码许可外推到数据。
- 适配 8GB：
  - `conf.yml` 默认 `IMAGE_SIZE=[128,128]`、`BATCH_SIZE=32`、`TIMESTEPS=100`、`MODEL_CHANNELS=32`。README 声称 128×128、batch 64 训练约 12GB（作者声明，未复现）。
  - 推理在 8GiB 上大概率可行；训练在 8GiB 上是否可行**未测**。输入边长需为 8 的倍数（模型下采样 3 次）。
- 实际限制：
  - **印章权重是去印章/去水印模型**；对“保留并修复红印”是反方向。
  - 数据许可不明，不能直接用于产品训练或再分发。
  - 128×128 训练分辨率对细笔画/小印可能不足；扩散 100 步推理比单步 CNN 慢。
- 可借用 / 不可用：
  - 可借用：残差扩散 + 粗预测器结构；红印/掩膜配对的组织方式；`NATIVE_RESOLUTION` 思路。
  - 不可用：`seal_*` 权重做修复；其数据做商用训练；把其“去印章”结果当作“修复”。

### 4.2 DocEnTR — 可训练，但输出是黑白二值图

- 仓库：<https://github.com/dali92002/DocEnTR>
- 固定提交：`004159e10f69f2b33f5800eeba4175d6f93cb17a`（2025-01-17，`main`）
- 关键证据：[predict.py](https://github.com/dali92002/DocEnTR/blob/004159e10f69f2b33f5800eeba4175d6f93cb17a/predict.py)、[models/binae.py](https://github.com/dali92002/DocEnTR/blob/004159e10f69f2b33f5800eeba4175d6f93cb17a/models/binae.py)。
- 实际可用：
  - 代码：`train.py`、`test.py`、`predict.py`、`models/binae.py`、`process_dibco.py`、`demo.ipynb`。
  - 权重：README Model Zoo 提供 DIBCO 2011/2017/H-DIBCO 2012/2018 的 Base/Large 权重 Google Drive 链接；其中 DIBCO 2011 两项标为 `Unavailable`。**未下载/未加载**。
  - 数据：DIBCOSETS 整合包 Google Drive；README 明确“这些数据集有自己的许可，不在本仓库许可之下”。
- 许可证据：
  - 代码：**CC BY-NC 4.0**（Attribution-NonCommercial 4.0）<https://github.com/dali92002/DocEnTR/blob/004159e10f69f2b33f5800eeba4175d6f93cb17a/LICENSE>
  - 提交信息明确写着 “The License is change to not allow commercial use of the repository.”（2025-01-17）。
  - 数据：README 的 “⚠️ Data License” 明确独立许可；**具体条款未在仓库内给出**。
  - 权重：无单独条款；不能假设可商用。
- 适配 8GB：
  - `predict.py` 以 256×256 切块；Base 为 ViT-Base/8×8 patch，Large 为 ViT-Large/16×16。
  - 推理单块可跑；README 训练示例 `batch_size=32` 在 8GiB 上很可能不够，需要 2–4 + 梯度累积（估计，未测）。
- 实际限制：
  - `predict.py` 最后执行 `(clean_image > 0.5) * 255`，**输出二值黑白图**；不能直接当RGB保色修复结果。可单独研究是否适合生成掩膜，再从原图保留颜色，效果尚未验证。
  - 方向是文档二值化/去噪，不是印章笔画补全。
  - 依赖较旧：`torch==1.10.0`、`vit_pytorch==0.24.3`、Python 3.8.12；与当前后端依赖不一致。
- 可借用 / 不可用：
  - 可借用：ViT 编解码 + patch 切分/拼接、DIBCO 评测流程。
  - 不可用：把二值化结果当修复输出；把其 PSNR 当我们的指标；商用（CC BY-NC）。

### 4.3 NAFNet — 最现实的可训练修复底座，但不是印章专用

- 仓库：<https://github.com/megvii-research/NAFNet>
- 固定提交：`2b4af71ebe098a92a75910c233a3965a3e93ede4`（2024-03-28，`main`）
- 关键证据：[NAFNet-width32 训练配置](https://github.com/megvii-research/NAFNet/blob/2b4af71ebe098a92a75910c233a3965a3e93ede4/options/train/GoPro/NAFNet-width32.yml)、[readme.md](https://github.com/megvii-research/NAFNet/blob/2b4af71ebe098a92a75910c233a3965a3e93ede4/readme.md)。
- 实际可用：
  - 代码：`basicsr/`、`options/train|test/`、`predict.py`、`basicsr/demo.py`。
  - 权重：README 给出 NAFNet-GoPro/SIDD/REDS、NAFSSR、Baseline 的 Google Drive/百度网盘链接；**未下载/未加载**。
  - 数据：GoPro/SIDD/REDS 等均需外部下载，仓库不附带；各自有数据集条款。
- 许可证据：
  - `LICENSE` 同时含 NAFNet 的 MIT（Copyright 2022 megvii-model）与 BasicSR 的 Apache-2.0 <https://github.com/megvii-research/NAFNet/blob/2b4af71ebe098a92a75910c233a3965a3e93ede4/LICENSE>。
  - 权重：无单独条款；不能假设权重与代码完全同许可。
- 适配 8GB：
  - 推理 256×256、width32 应可；width64 更重。
  - 训练配置 `NAFNet-width32` 为 256 crop、`batch_size_per_gpu=4`、`num_gpu=8`；单卡 8GiB 需要降 batch/宽度或梯度累积，**未测**。
- 实际限制：
  - 通用自然图像修复，没有文档/印章先验；GoPro/SIDD权重在古印上的效果尚未验证，不能据此宣称有效。
  - 必须有配对（退化图/干净图）才能训练；当前没有找到配对真值。
  - 对“细红笔画”是否比传统方法更好，必须在我们自己的测试集上测。
- 可借用 / 不可用：
  - 可借用：NAFBlock/NAFNet 结构、width32 轻量配置、PSNR/SSIM 训练与评测管线；TorchScript 需自行写 wrapper（仓库未提供现成导出脚本，未验证）。
  - 不可用：直接拿 GoPro/SIDD 权重宣称修复古印；用无完整真值的数据宣称真实缺损修复有效。

### 4.4 PaddleOCR — 现代公章流水线，代码许可清楚，权重许可未单独核验

- 仓库：<https://github.com/PaddlePaddle/PaddleOCR>
- 固定提交：`dab3fe35379033fdcb2d0e9572fac0b36c9a9ebf`（`main`，调研时）
- 关键证据：[seal_recognition.en.md](https://github.com/PaddlePaddle/PaddleOCR/blob/dab3fe35379033fdcb2d0e9572fac0b36c9a9ebf/docs/version3.x/pipeline_usage/seal_recognition.en.md)、[seal_text_detection.en.md](https://github.com/PaddlePaddle/PaddleOCR/blob/dab3fe35379033fdcb2d0e9572fac0b36c9a9ebf/docs/version3.x/module_usage/seal_text_detection.en.md)。
- 实际可用：
  - 代码：完整 PaddleOCR 3.x；有专门的 `seal_recognition` 流水线和 `seal_text_detection` 模块。
  - 模型：`PP-OCRv4_server_seal_det`（109 MB）、`PP-OCRv4_mobile_seal_det`（约 4.6–4.7 MB，两份文档略有差异）；识别侧 PP-OCRv5 server/mobile（81/16 MB）、PP-OCRv4 server/mobile/doc（173/10.5/182 MB）。下载链接为 `paddle-model-ecology.bj.bcebos.com`。
  - 数据：不附带训练数据。
- 许可证据：
  - 代码：Apache-2.0 <https://github.com/PaddlePaddle/PaddleOCR/blob/dab3fe35379033fdcb2d0e9572fac0b36c9a9ebf/LICENSE>
  - 权重：仓库/该文档没有单独声明权重许可；本次未能访问 HuggingFace 模型卡（网络阻塞），因此**权重许可 unknown**，不能假定 Apache-2.0 自动覆盖模型文件。
- 能力边界（文档明确）：
  - 面向合同、发票、仓库单据等**现代印章**；支持弯曲印章文字、方向矫正、版面中的 `seal` 区域。
  - 检测模块文档明确其性能测试集是“500 张圆形印章的自建内部数据集”，输出是多边形文本框，不是红印像素掩膜。
  - 识别模型是 PP-OCRv5 现代中文/繁体/日文/英文识别；**没有古篆/古玺训练说明**。古篆字形不属于其常规字符/排版分布，不能假设可识别。
- 适配 8GB：
  - 推理很轻（mobile 检测 4.7 MB + mobile 识别 16 MB），CPU 也可；GPU 需 PaddlePaddle GPU 版，与现有 PyTorch/TorchScript 插件不是同一运行时。
  - 8GiB 足够推理；训练另说。
- 实际限制：
  - 引入 Paddle 运行时，不能直接塞进现有 TorchScript 插件；应做独立 sidecar/HTTP 服务。
  - 现代公章 ≠ 古玺；其 `seal` 版面框也不是像素级红印掩膜。
  - 模型许可未核验。
- 可借用 / 不可用：
  - 可借用：现代印章的检测→矫正→识别流水线设计；`seal` 版面类别的工程做法；弯曲文本处理思路。
  - 不可用：直接作为古篆 OCR；把其 Hmean 当我们的准确率；在未核验权重许可前打包分发。

### 4.5 TrOCR-Seal-Recognition — 有完整训练/ONNX 流程，但没有许可证

- 仓库：<https://github.com/Gmgge/TrOCR-Seal-Recognition>
- 固定提交：`315cbbe749c4151d740daeb96412ac4decabfea3`（`main`，调研时）
- 关键证据：[README.md](https://github.com/Gmgge/TrOCR-Seal-Recognition/blob/315cbbe749c4151d740daeb96412ac4decabfea3/README.md)、[DataSet.md](https://github.com/Gmgge/TrOCR-Seal-Recognition/blob/315cbbe749c4151d740daeb96412ac4decabfea3/DataSet.md)、[requirements.txt](https://github.com/Gmgge/TrOCR-Seal-Recognition/blob/315cbbe749c4151d740daeb96412ac4decabfea3/requirements.txt)。
- 实际可用：
  - 代码：`train.py`、`eval.py`、`onnx_test.py`、`tool/`（数据集字典、初始化、评估）。
  - 权重：README 提供百度网盘/Google Drive 的 TrOCR 预训练与印章 ONNX 模型；**未下载/未加载**。
  - 数据：README/DataSet.md 提供网页抓取的真实圆形印章、ICDAR 2023 Seal Title、PaddlePaddle 社区生成数据等链接；**仓库不附带数据**。
- 许可证据：
  - **没有 LICENSE 文件**（`315cbbe` 下 raw `LICENSE` 返回 404）→ 默认“保留所有权利”，**不能复用/分发**。
  - 数据：无数据许可；README 说明 `seal-ocr` 训练数据来自“互联网爬取，标签由付费 API 识别加人工验证”，来源与标注合规性均有风险。
- 能力边界：
  - 现代圆形公章，水平公司名 + 可选的弧形文字；README 明确真实数据不足时效果不佳。
  - 不是古篆/古玺识别；输入是整枚现代印章图，输出一行文本。
- 适配 8GB：
  - TrOCR 约 3.3 亿参数；fp32 权重约 1.3 GB，推理可；训练命令 `per_device_train_batch_size=8`（作者用 3090），8GiB 需 batch 1–2/梯度累积或 LoRA（估计，未测）。
  - 依赖 `transformers==4.29.2`（2023），与当前环境可能冲突。
- 可借用 / 不可用：
  - 可借用：TrOCR 微调 + 自定义字典 + ONNX 导出的工程路径；置信度过滤。
  - 不可用：无许可代码/权重；现代公章数据；抓取+付费 API 标签作为古印监督。

### 4.6 character-Evolution-Dataset (EVOBC) — 有篆书字形，但只是数据

- 仓库：<https://github.com/RomanticGodVAN/character-Evolution-Dataset>
- 固定提交：`1a3951bd41988e19aef88bdbb601ca5b1068deac`（`main`，调研时）
- 关键证据：[README.md](https://github.com/RomanticGodVAN/character-Evolution-Dataset/blob/1a3951bd41988e19aef88bdbb601ca5b1068deac/README.md)、[LICENSE](https://github.com/RomanticGodVAN/character-Evolution-Dataset/blob/1a3951bd41988e19aef88bdbb601ca5b1068deac/LICENSE)。
- 实际可用：
  - 仓库内：`Key&Value.json`（约 277 KB，ID→中文标签）、`List_of_EVOBC.json`（约 23 MB 路径清单）、`Statistics.xlsx`、`CITATION.cff`。
  - 图像：不在仓库，README 指向 HuggingFace `HaisuGuan/EVOBC`；**未访问/未下载**。
  - 代码：README 待办明确 “Release the data processing code” 未完成 → **无处理/训练代码**。
- 许可证据：
  - 数据：CC BY-NC-SA 4.0，`LICENSE` 明确 SPDX `CC-BY-NC-SA-4.0` <https://github.com/RomanticGodVAN/character-Evolution-Dataset/blob/1a3951bd41988e19aef88bdbb601ca5b1068deac/LICENSE>
  - 代码：仓库没有代码许可可谈。
- 能力边界：
  - 甲骨文演化数据集，含 OBC/BI/**SS（篆书）**/SAC/WSC/CS 六类字形；提供单字 ID 标签，不是整印图像，也不是红印掩膜/配对修复数据。
  - 非商用 + 相同方式共享；若产品含商业属性，不能直接用。
- 适配 8GB：数据本身与显存无关；可用于字形分类/字典辅助，但不能直接训练整印 OCR。
- 可借用 / 不可用：
  - 可借用：篆书单字样本与字符标签，用于字形字典/分类预训练（须先确认 NC-SA 可用于项目性质）。
  - 不可用：作为印章检测/修复数据；作为商用训练集；当作“古印 OCR 数据集”。

### 4.7 Chronicles-OCR — 评测基准，不是实现来源

- 仓库：<https://github.com/VirtualLUOUCAS/Chronicles-OCR>
- 固定提交：`9373f7a53b8d6ccbddbf73a07f60ac2b23bbefea`（`main`，调研时）
- 关键证据：[README.md 的 License 段](https://github.com/VirtualLUOUCAS/Chronicles-OCR/blob/9373f7a53b8d6ccbddbf73a07f60ac2b23bbefea/README.md#license)、[Opensource/infer.py](https://github.com/VirtualLUOUCAS/Chronicles-OCR/blob/9373f7a53b8d6ccbddbf73a07f60ac2b23bbefea/Opensource/infer.py)。
- 实际可用：
  - 代码：`Opensource/infer.py`、`judge.py`、`summarize.py`、`prompts/`、`judges/`，通过 OpenAI 兼容 API 或本地 vLLM 调用 VLM。
  - 数据：2800 图、七体字（含篆书），HuggingFace/ModelScope；**仓库不附带图像**。
  - 权重：**没有**；依赖外部 VLM。
- 许可证据：
  - 代码：Apache-2.0，`LICENSE` <https://github.com/VirtualLUOUCAS/Chronicles-OCR/blob/9373f7a53b8d6ccbddbf73a07f60ac2b23bbefea/LICENSE>
  - 数据：README 末尾写 “This benchmark is released for **research purposes only**.” → 不是标准开源许可，商用/再分发不明确。
- 适配 8GB：
  - README 示例使用 7B VLM + vLLM；fp16 7B 权重本身约 14 GB，超过 8 GiB，**按文档配置不可行**（显存估算，未实测）。
  - 即使换 2B 模型，也只是评测，不是训练。
- 实际限制：
  - 榜上是作者/提交者的评测结果，不是我们的数据；不能引用为古印识别准确率。
  - 任务是 VLM 的 spotting/recognition/parsing/classification，不是红印分割或笔画修复。
  - 数据 research-only。
- 可借用 / 不可用：
  - 可借用：七体字评测任务定义、IoU/ Exact-match / NED 指标、人工校验流程。
  - 不可用：作为训练数据/权重来源；在 8GiB 上按 7B 配置部署；商用。

### 4.8 明确排除：Art-of-Chinese-Seal-Engraving

- 仓库：<https://github.com/jingrong-zhang/Art-of-Chinese-Seal-Engraving>
- 固定提交：`41b283b6cc9aa478026e8dfcd9b9dc9059bed31a`（2023-01-16，`main`）
- 关键证据：[README.md](https://github.com/jingrong-zhang/Art-of-Chinese-Seal-Engraving/blob/41b283b6cc9aa478026e8dfcd9b9dc9059bed31a/README.md)。
- 许可：Apache-2.0，`LICENSE.md` <https://github.com/jingrong-zhang/Art-of-Chinese-Seal-Engraving/blob/41b283b6cc9aa478026e8dfcd9b9dc9059bed31a/LICENSE.md>
- 内容：上海图书馆开放数据竞赛的 Dash/Plotly 叙事看板 + 截图 + `app.py`；README 没有 OCR、检测、修复或训练代码/权重。
- 结论：**排除**。它是数据可视化/叙事演示，不是实现来源；其数据源（上海图书馆）条款也未在仓库中说明。

## 5. 建议集成顺序（按当前项目实际约束）

> 前提：`backend/app/ai.py` 的修复插件是固定 256×256 TorchScript；识别插件是单字分类 `[1,C]`。任何模型接入都必须遵守这个契约，或者明确新增独立服务，不能假装“已接入”。建议 Vue/FastAPI/MySQL 业务层保持现状；新增 Paddle 服务时作为独立 sidecar 由后端代理，鉴权/审计链路需显式设计，不能假设自动复用。

### P0 — 记录各环境并检查导出兼容（已完成小型实验）
- 本机GPU训练与后端CPU推理分别固定依赖，现有模型已通过跨环境数值探针；并未运行Docker。
- 参见第2节和GPU训练文档。第三方模型仍须单独测量，不外推显存与兼容性。

### P1 — 数据审计与人工测试集（无模型）
- 只读扫描 `tzsf_yt_p0001_01.png` 这类命名，忽略 `._*` 旁文件；按 `tzsf_yt` + `pNNNN` 页号分组，**按页划分 train/val/test**，避免同页裁切泄漏。
- 按任务简报，现有素材为 PNG-only 裁切，尚未找到标签/配对干净图；本次未读取图像，不能确认其数量、重复或内容。若审计结果仍无标签，先人工标注，**不得生成伪标签**。
- 当前没有标签/配对真值：先人工标注 50–100 枚（红印掩膜 + 可见字转录 + 是否为古篆/残损），双人复核；不得用模型输出反填标签。
- 不读取、不移动、不改名 `D:/LH/raw_crops`。

### P2 — 红印掩膜基线（OpenCV，非 AI）
- 在 P1 测试集上量化现有 `processing.py` 的 HSV 红印掩膜：IoU、召回、断笔率；再考虑 Lab/HSV 自适应阈值 + 形态学闭运算。
- 把“印章区域框”（检测）与“红印像素掩膜”（分割）分开记录；PaddleOCR 的 `seal` 框不能当像素掩膜。
- DocDiff 的 1597 掩膜只能在**获得数据许可后**作为外部评测/预训练参考，不能直接分发或商用。

### P3 — 可训练修复（有配对数据后才做）
- 首选 **NAFNet-width32**：256×256 配对训练，导出 TorchScript 固定 256 输入，接入 `RESTORE_MODEL_PATH`；先影子模式，不覆盖原图。
- 若坚持扩散路线，可参考 DocDiff 结构重训一个“保留印章”方向的模型；**不得**使用其 `seal_*` 去印章权重。
- 对真实缺损任务，没有完整图对照时不能宣称PSNR/SSIM或历史复原能力。可独立训练合成退化任务，但必须说明原裁图仍有损伤，指标仅针对添加的退化；本轮已完成此实验，业务修复插件继续明确不可用。

### P4 — OCR（现代与古篆分开）
- 现代公章：PaddleOCR `seal_recognition` 作为独立 Paddle 服务试点，输出必须人工复核；先确认权重许可，再决定是否随产品分发。
- 古篆/古玺：本轮未核验到可直接使用且效果可信的权重。需要自建“单字/多字序列”标注集与字符表，再考虑CRNN/TrOCR序列模型；当前单字分类插件不足以做整印转录。
- 不得把 EVOBC（NC-SA）或 TrOCR-Seal（无许可）直接用于商用训练；不得用 DocDiff 掩膜生成 OCR 标签。

### P5 — 评测与溯源
- 固定测试集按页隔离；指标至少：掩膜 IoU、字符错误率 CER、整印 exact match、修复 PSNR/SSIM（仅有配对真值时）。
- 记录模型 SHA256、训练数据版本、字典版本、人工复核状态；沿用现有 `ai_inference`/`human_review_required` 溯源字段。
- 任何论文数字都只作为背景，不作为本项目验收值。

### P6 — 产品化门禁
- 只有 P2–P5 的指标达到项目方预先设定的阈值，才把“AI 修复/识别”从 503 改为可用；UI 明确标注“AI 辅助，需人工复核”。
- 许可未清的权重/数据不得进入 Docker 镜像或发布包；CC BY-NC / NC-SA / research-only 内容只能留在研究环境。

## 6. 未核验项与访问阻塞

- **范围限制**：本报告只对上述 8 个仓库做了文件级核验，不是全 GitHub 穷举；搜索中出现的其他仓库未纳入本次结论。
- **权重未下载/未加载**：DocDiff 仓库内 `.pth` 只核验了文件树与大小；DocEnTR/NAFNet/PaddleOCR/TrOCR 的权重只核验了 README 链接，没有验证文件可下载、可加载、SHA256 或推理结果。
- **HuggingFace 本次访问失败**：无法核验 PaddleOCR 模型卡/权重许可，也无法核验 EVOBC/Chronicles 数据卡细节；相关权重/数据许可标为 unknown。
- **Google Drive/百度网盘未访问**：DocDiff 1597 印章数据、DocEnTR/NAFNet/TrOCR 权重的实际可用性未验证。
- **GitHub API 限流**：共享出口 IP 的 core API 被限流；改用公开 raw/atom/代理读取，commit SHA 已固定。`github.com` 直连曾间歇失败，raw 经代理成功。
- **未运行任何仓库代码、未安装包、未做显存测量**；8GB 结论是配置/参数量层面的估算，不是实测。
- **未读取 `D:/LH/raw_crops`**：标签是否存在、配对真值是否存在，仅依据任务简报；本次没有验证图像内容、数量或重复情况。
- **没有古篆 OCR 的可信开源实现**：本次检查的 7 个入选仓库中，PaddleOCR/TrOCR 仅覆盖现代公章；EVOBC/Chronicles 只提供数据/评测。若控制方要求“古篆 OCR”，需要另立数据与模型任务。

## 7. 变更文件

- `docs/GITHUB_RESEARCH.md`（本文件）
- `docs/github-sources.json`（机器可读来源清单）

未修改任何其他文件；未改动 `D:/LH/raw_crops`；未安装包、未 clone、未运行仓库代码、未上传图片、未访问凭据。


## 8. 复核说明

本报告由已鉴权的DeepSeek Harness完成仓库调研，Codex随后复核主要原始页面并更新第2节、二值化用途与合成退化实验边界。Harness没有读取训练图片；Codex在本地只读审计并训练。调研时未下载第三方权重，此后新增的是本项目自己训练的实验权重。第6节“未做模型/显存测试”指第三方仓库，不能据此否认本项目GPU实验。仓库许可记录是文件级证据，缺失条款保留为未核验，不推断额外授权。
