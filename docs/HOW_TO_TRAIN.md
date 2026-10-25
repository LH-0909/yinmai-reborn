# 去噪实验的训练方式与一键入口

**范围更正：以下目录与数据划分由程序为去噪实验生成。用户提供的仍是未整理的原始图片，它们不是已经完成释文、单字框和印风核对的字体训练集。学习篆刻风格并生成指定汉字，应先按[素材准备状态](DATA_READINESS.md)整理，再使用[字体训练入口](FONT_STYLE_TRAINING.md)。**

当前真正实现的训练方式是**合成退化的监督去噪**：原裁图作为有损目标，在线添加标准差0.08的高斯噪声作为输入，训练轻量残差CNN去除新增噪声。损失为排除白色补边的RGB均方误差，优化器Adam，学习率0.001。训练/验证/测试按来源页隔离，验证MSE选择权重，保留测试仅作最终评估。

没有释文和无损配对图，因此当前没有古篆OCR训练、真实缺笔补全训练或大模型微调。去噪目标仍保留原图已有的残损，指标不能称为历史修复准确率。

## Windows一键训练

解压含图片的完整包，在项目目录双击`Start-GPU-Training.cmd`。默认用2,048张训练池、128张验证、128张测试、batch16、5轮。启动器自动检测CUDA环境、定位随包图片和相对路径清单，逐轮打乱且完整遍历训练池；没有CUDA会明确失败，不悄悄回退CPU。

也可在项目目录使用PowerShell：

```powershell
# 快速检查入口：20步，64张训练池
powershell -ExecutionPolicy Bypass -File scripts/train-gpu.ps1 -Smoke

# 全部11,144张训练图像，每轮每张至少访问一次
powershell -ExecutionPolicy Bypass -File scripts/train-gpu.ps1 -FullDataset -Epochs 5 -Batch 16

# 自选步数 / 批量；步数和完整轮数二选一
powershell -ExecutionPolicy Bypass -File scripts/train-gpu.ps1 -Steps 1000 -Batch 8
```

若自动检测不到CUDA环境，可加`-Python '你的CUDA环境/Scripts/python.exe'`；单独解压图片包时可加`-DataDir '图片包解压目录'`。启动器只检查已有环境，不改动系统Python或自动安装大体积依赖。

## 输出与查看

每次训练创建新运行目录`evidence/gpu-runs/<运行ID>/`，保存参数、实时日志、损失历史、数据选用清单、测试指标和实际对照PNG。模型导出到`models/experimental/runs/<运行ID>.torchscript.pt`。`evidence/latest-training-run.json`指向最新一次成功训练。

`train_unique_images_seen`记录实际访问的不同训练图像数，不能把“载入训练池”说成“每张都训练过”。完整轮模式会检查全覆盖。旧400步基线保留原有有放回抽样，已核验的首批回放和指标不会被新运行覆盖。

新模型不会自动替换网页去噪模型，更不会启用古篆OCR或缺笔恢复。需要先审阅同一保留集效果与细笔画表现，再决定是否更新实验推理权重。


## 已完成的一键入口实测

2026-10-20，在RTX4060Ti上通过同一个PowerShell入口运行`-FullDataset -Epochs 1 -Batch 16`：训练11,144张、验证1,167张、测试1,333张。共697步，记录确认11,144张不同训练图像全部被访问一次。峰值PyTorch分配显存约2,345MiB。

保留测试集只针对新增噪声：输入PSNR约23.00dB，模型输出约31.86dB。这次测试集比旧128张基线更大，不能将两个数值直接比较来宣称模型优劣。新导出在后端CPU环境通过同形状数值探针；没有自动替换网页模型。

完整日志、数据选用清单、对照图与指标见evidence/latest-training-run.json指向的运行目录。
