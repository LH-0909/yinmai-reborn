# 原始图像副本与去噪实验输入

**这些图片仍是未经字形与印风整理的原始素材。包内train/validation/test名称来自程序的去噪实验分组，不代表用户已划分或已完成字体训练数据整理。** 篆刻风格生成的数据准备状态见[DATA_READINESS.md](DATA_READINESS.md)。

之前的源码包确实没有附原始训练PNG，只包含清单和预览。本轮已补充独立数据目录、训练图片浏览器，以及含代码和真实图片的完整压缩包。

- `yinmai-reborn-full-with-images.zip`：解压后项目内含`training-data/`，共13,646张原始PNG，另含实际训练/测试输入、目标、掩膜与模型输出。
- `yinmai-training-data.zip`：只包含图像与清单，供已有项目单独使用。
- 旧`yinmai-reborn-delivery.zip`仍是较小的纯代码包，没有原始训练全集，避免将两种包混淆。

## 图像位置与浏览

完整包的项目目录下：

```text
training-data/
  index.html                       双击即可查看实际图片
  images/train/                    11,144张
  images/validation/               1,167张
  images/test/                     1,333张
  images/excluded/                 2张过小图片
  manifests/                      相对路径训练清单
  used-inputs/train-step-0001/      首批16张真实训练输入回放
  used-inputs/fixed-test-128/       固定测试输入、目标、掩膜、输出
  真实训练输入对照.png
```

浏览器默认展示训练组，可搜索文件名/来源页、翻页、只看实际GPU基线使用的图片，或切换首批输入/目标对照。不是只展示100张验证候选；标注页的100张候选依然作为独立的人工工作集。

训练过程逐批即时生成合成噪声，之前没有落盘的“输入图文件夹”。本轮在同一CUDA环境回放首批输入，并验证第1步MSE与原记录完全相同；固定128张测试的PSNR也完全一致。保存的PNG便于查看，精确float32数组保存在NPZ中。没有把其他图片冒称为实际训练输入。

## 直接使用

完整包解压后，未配置外部素材路径时，后端会自动读取项目`training-data/images`和配套候选清单。数据库/运行依赖仍按README配置。若使用单独图像包，在`.env`填写`TRAINING_CORPUS_PATH=<解压目录>/images`和`ANNOTATION_SEED_PATH=<解压目录>/annotation-seed.csv`，重启后端。

训练脚本支持清单相对路径，例如在项目目录执行：

```powershell
python backend/training/train_denoiser.py --audit training-data/manifests --out evidence/new-gpu-run --model models/experimental/new-run.pt
```

需要CUDA版PyTorch。原始裁图按来源页隔离为训练、验证和测试，不自动混组。2张过小图片保留在excluded，不用于训练。

这些是用户原始裁图及已核验的合成噪声实验输入；没有人工释文，也没有完整无损修复真值。不能把原始有损裁图目标当作历史完整印文。本包只在本机生成，没有上传图片到Harness、GitHub或其他外部服务。
