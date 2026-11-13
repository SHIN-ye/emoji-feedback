# 视频中的 AI 验证证据

目前未配备安装在教室内的摄像头，也缺少真实课堂部署与验证条件。已完成电脑摄像头采样、模型推理、匿名入库及教师接口核验，并完成 FER2013 公开测试分片的分类评测。本目录保存 2026 年 11 月 12 日实测结果的副本，供演示视频复核。

## 电脑摄像头

- `camera-result.json` 是 `artifacts/ai-camera-20261112-185445/result.json` 的原始副本，包含匿名 AI 记录、教师看板统计和 `passed: true`。
- `camera-worker-excerpt.log` 节选同次测试日志中的 HTTP 返回、分类结果与采样汇总。8 次采样成功入库 1 条，HTTP 返回 200，`accepted=True`。
- `ai/camera_pipe.py` 负责 DirectShow 摄像头采集和内存管道传帧，`ai/worker.py` 负责人脸检测、分类、过滤与提交，`scripts/verify_ai_camera.py` 执行隔离验收并核对教师历史与看板。

复现本机采集方式见 [部署与用户手册](../../部署与用户手册.md) 的“Windows 独立采集方式”。原始画面默认不保存，因此证据为运行日志和结构化验收结果。

## FER2013 分类评测

`fer2013-result.json` 是 `artifacts/fer2013/result.json` 的原始副本，包含模型版本、样本数、逐类召回率、阈值统计、混淆矩阵和数据文件 SHA-256。

数据来自 [Jeneral/fer-2013 的 test 分片](https://huggingface.co/datasets/Jeneral/fer-2013)。使用 DeepFace 0.0.93 对 7,178 张已裁剪人脸分类，4,084 张预测正确，七类准确率 56.90%。阈值 0.60 时保留 6,043 张，保留样本准确率 61.84%。

数据文件 SHA-256 为 `62363a3b17f8623db20afbe7d65a701a8e1431b53e035a09b96b8ef24bbc7700`，已与本机测试 Parquet 重新核对一致。

在 AI 环境安装 `pyarrow==23.0.1` 并下载测试分片后执行以下命令。

```powershell
.\.venv-ai\Scripts\python.exe -m scripts.evaluate_fer2013 artifacts/fer2013/test.parquet --output artifacts/fer2013/result.json
```

预训练模型使用过 FER2013，本次结果用于同数据集基准复核。课堂多人、拍摄距离、光照与持续运行效果仍需实地验证。模型输出为表情分类，需结合学生主动反馈理解。
