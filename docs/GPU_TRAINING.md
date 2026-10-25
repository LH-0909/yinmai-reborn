# GPU训练实测与复现

RTX4060Ti 8GB可以训练。本轮在CUDA上实际完成400次前向、反向传播和Adam更新，没有回退CPU；模型包含11,739个参数。此小型基线与大型扩散模型、大模型的显存需求不能直接类比。

## 环境与隔离

- 显卡：NVIDIA GeForce RTX4060Ti，驱动610.88，设备cuda:0。
- 训练：`C:/Users/pc/Documents/Codex/2026-10-19/referenced-chatgpt-conversation-this-is-an/work/gpu-training/Scripts/python.exe`，Python3.8.5、torch1.13.1+cu116、CUDA11.6。
- 该独立虚拟环境通过`--system-site-packages`复用本机已有Anaconda GPU库，没有改动全局包。现有后端仍用独立Python3.12/torch2.14.1+cpu。
- 曾尝试下载新的CUDA版大体积安装包，网络超时，没有用未完成安装冒充成功；随后发现并实测既有GPU环境。
- 不是要求其他机器安装这个旧版本；新机器应依据官方PyTorch安装页面选择与自身驱动匹配的CUDA构建，并独立安装、记录版本。

## 实际实验

| 项目 | 实测 |
|---|---|
| 目标 | 去除新增的合成高斯噪声；目标图仍是原始有损扫描 |
| 训练池 / 验证 / 测试 | 2,048 / 128 / 128，来源页隔离并核验原文件SHA256 |
| 输入 | 等比例缩放到96px方框，白色补边；指标排除补边 |
| 噪声 | RGB标准差0.08，裁切至0–1，仅图像内容区域 |
| 模型 | 4层残差CNN，宽度24，未使用外部权重 |
| 批大小 / 更新次数 | 16 / 400 |
| 训练与阶段验证耗时 | 6.03秒；不含读图、导出和后续检查 |
| 峰值PyTorch分配 / 预留显存 | 398.90 / 416.00MiB；不是整机GPU总占用 |
| 测试输入PSNR | 22.98dB |
| 测试输出PSNR | 31.50dB |
| 提升 | 8.52dB，仅合成噪声基准 |

训练以验证MSE选择权重，最后一次性评估保留测试集。单一噪声强度、小样本、单种子；尚未比较传统滤波或其他网络，也未做真实噪声、缺笔、OCR或历史真实性评测。原图里已有的残损一直存在，不能把这些数值写成古印修复准确率。

## 导出与后端兼容

权重：`models/experimental/rgb-denoiser-v1.torchscript.pt`，SHA256 `b30a7fa8595e4f84fc67905aba78d28d482257530a17727b13fb235aaf3b8db3`，旁边JSON记录任务边界、数据、环境与指标。TorchScript导出在后端torch2.14.1+cpu加载成功，数值探针输入`[1,3,256,256]`、输出同形、有限且0–1；与训练环境CPU参考的最大差值0。证据：`evidence/gpu-denoiser-v1/backend-runtime.json`。这只验证此模型的运行兼容性。

没有设置`RESTORE_MODEL_PATH`；正式深度修复与古篆识别仍未完成。随后已新增独立增强实验室，通过`/enhance`实际运行此权重并保留溯源；它不补缺笔。详见ANNOTATION_LAB.md。训练记录中的`api_model_enabled=false`保留导出当时的状态，当前实验服务状态另有部署证据。

## 复现命令

在项目目录执行，训练脚本要求CUDA；不可用会明确报错。原始图片路径从审计清单读取，变更时哈希校验失败。

```powershell
& 'C:/Users/pc/Documents/Codex/2026-10-19/referenced-chatgpt-conversation-this-is-an/work/gpu-training/Scripts/python.exe' backend/training/train_denoiser.py --audit data/raw-crops-audit --out evidence/gpu-denoiser-v1 --model models/experimental/rgb-denoiser-v1.torchscript.pt
```

默认参数就是本轮实测400步/2048张/batch16/96px/seed19。重复执行会覆盖同名实验输出，需保留旧结果时更换`--out`与`--model`。`selection.json`记录实际选用文件及哈希；`metrics.json`含逐阶段损失、独立测试指标与实测显存；`synthetic-noise-comparison.png`依次为原始有损目标、合成噪声、网络结果、4倍绝对误差。

CPU跨环境检查可分别在两个环境运行`backend/training/verify_export.py`；先用训练环境加`--write-reference`生成数值参考，再用后端环境比较。参考仅为数字探针，不是图片真值。

下一步是标注古篆释文/掩膜、收集或定义可验证的缺损对照，再训练对应任务；8GB可以先试小批次、轻量网络与梯度累积，其他网络的显存上限要逐个实测。

最新新增一键入口及完整轮数训练。2026-10-20已在同机实际训练全部11,144张一轮（697步），验证1,167、测试1,333；详情见HOW_TO_TRAIN.md与evidence/latest-training-run.json。旧400步基线与回放证据原样保留，不覆盖其权重或网页当前模型。
