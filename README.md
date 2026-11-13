# 晴课 课堂情绪检查器

面向软件工程实践的课堂反馈系统，含学生、教师、管理员浏览器界面，分层后端和独立 AI 视频采样程序。

## 演示视频

[下载演示视频 MP4](docs/demo/emoji-feedback-demo.mp4)（约 6 分 33 秒，中文字幕，操作部分为 1.25 倍速，已剪去原版开头 20 秒）。演示包括创建课程与课堂、安排学生、提交反馈、教师看板、多条件统计和 CSV 导出。约 4 分 15 秒起说明 AI 实现流程、本机摄像头实测、FER2013 评测方法与结果，以及当前缺少真实教室部署与验证条件的范围限制。[查看视频中的 AI 验证证据](docs/demo/evidence/README.md)。

先阅读 [完整项目计划书](docs/项目计划书.md) 和 [需求与设计](docs/需求与设计.md)。执行进度及真实验收边界见 [测试报告](docs/测试报告.md)。

## 本地运行
需要 Python 3.15.2。Windows PowerShell，在本目录执行：
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m scripts.seed --demo
.\start.ps1
```

请确保上述 `python` 指向 Python 3.15.2。本机的独立解释器位于
`$env:LOCALAPPDATA\Programs\PythonProject3152\tools\python.exe`；若系统没有配置 Python，可用
`& "$env:LOCALAPPDATA\Programs\PythonProject3152\tools\python.exe" -m venv .venv` 创建环境。
初始化命令会输出随机演示密码，账号为 admin、teacher、student、student2。不会自动覆盖已有账号。演示数据是人工合成数据，记录标识 DEMO_SYNTHETIC；课堂有效期为初始化后的12小时。过期后由管理员创建新课堂并安排学生。

访问 http://127.0.0.1:8000 ，API 文档 http://127.0.0.1:8000/docs 。本地默认 SQLite 自动创建 emoji.db；正式部署配置 DATABASE_URL 使用 PostgreSQL。数据库和密钥不进入 Git。

本机首次初始化的随机密码另存于被 Git 忽略的 `logs/本地演示账号.txt`。其他机器运行初始化命令会生成自己的密码。

## 测试
```powershell
.\.venv\Scripts\python.exe -m pytest -q
node --check web/app.js
```
浏览器回归需 Playwright 与 Chromium/Edge，设置 DEMO_PASSWORD、必要时设置 PLAYWRIGHT_PATH（模块路径）和 BROWSER_PATH（浏览器可执行文件路径），先启动本地服务，再运行：
```powershell
node tests/browser-smoke.cjs
node tests/browser-race.cjs
node tests/browser-account-race.cjs
```
浏览器测试会在演示课堂添加一条真实测试反馈。测试图像和导出文件位于 artifacts（不提交仓库）。

## 目录
backend：数据库模型、认证、数据访问、业务规则和 HTTP 接口。
web：无构建步骤的模块化 JavaScript 客户端。
ai：独立视频分析程序，依赖与主系统隔离。
tests：接口、安全、AI 协议、浏览器测试。
scripts：演示初始化与 OpenAPI/SQL 导出。
docs：计划、需求设计、部署手册、测试报告与答辩材料。

## 当前边界
已实现课堂反馈业务、角色权限、统计、CSV、浏览器工作台和 AI 视频采样入库。已完成真实摄像头短时采集、模型推理及匿名入库验证，并使用 FER2013 的 7,178 张测试图像进行分类评测，实验范围与结果见测试报告。PostgreSQL 容器启动和多人负载仍需验证。AI 服务默认不保存媒体，也不做人脸身份识别。当前历史接口提供 limit/offset，页面显示最新200条；CSV 可导出筛选下全部记录。看板用五秒轮询，未实现 WebSocket。
