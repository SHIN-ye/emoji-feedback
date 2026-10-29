# Emoji Checker Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement task-by-task. User explicitly authorized continuous execution without approval gates.

**Goal:** 可运行、可测试、可演示的课堂情绪系统及完整项目计划。
**Architecture:** 浏览器 MVC，后端 Controller → Service → Repository，独立 AI REST 服务。
**Tech Stack:** JavaScript、FastAPI、SQLAlchemy、PostgreSQL/SQLite、OpenCV/DeepFace。
**Spec:** ../../项目计划书.md

## Global Constraints
全部接口后端授权；至少五类情绪；匿名 AI、不保存原始人脸；管理员注册需邀请码；数据库保存密码哈希和会话摘要；AI 独立令牌；UTC 存储。

## Review Focus
越权读取与统计泄漏；改密和禁用后会话失效；课堂时间/安排生效边界；AI 重试重复及低置信度；CSV 公式和用户内容 XSS。

## Task 1 后端业务闭环
Files: backend/models.py, repository.py, services.py, security.py, schemas.py, main.py; tests/test_api.py。
Interfaces: create_app(database_url, config) -> FastAPI；HTTP 接口遵循项目计划第5节。
- [x] 编写并运行真实临时数据库接口测试：注册拒绝提权、登录改密、权限隔离、课堂安排、提交和历史。
- [x] 实现 ORM 和认证、授权、数据规则、接口；运行 pytest 通过。
- [x] 增加统计、导出和 AI 测试，确认缺失行为失败。
- [x] 实现筛选统计、匿名 AI、事件幂等、CSV 防注入；完整测试通过后提交。

## Task 2 浏览器客户端
Files: web/index.html, style.css, api.js, app.js；tests/browser-smoke.cjs。
Consumes: Task 1 API；Produces: 学生、教师、管理员按角色展示和真实交互。
- [x] 构建登录注册、课堂选择、情绪提交、历史、统计、管理和改密页面。
- [x] 浏览器执行学生提交→教师查看→管理员导出，检查窄屏和空状态。
- [x] 检查 JavaScript 语法及后端回归测试后提交。

## Task 3 AI 与交付文档
Files: ai/worker.py, ai/requirements.txt, tests/test_ai.py, Dockerfile, compose.yaml, scripts/*, docs/*。
Interfaces: make_result(prediction, session_id, threshold) -> dict | None; send_result(url,token,payload) 支持有限重试。
- [x] 先测试情绪映射/阈值/缺失人脸/重试，再实现采样程序。
- [x] 编写启动、初始化、数据库生成脚本与部署配置。
- [x] 编写用户手册、测试报告、实验报告和答辩脚本；生成 OpenAPI 与 SQL。
- [x] 完整测试和独立审查；记录真实摄像头、容器部署及演示录像待验收情况。

## 现场验收待办
- [ ] PostgreSQL 容器实际部署与备份恢复。
- [ ] 安装AI模型依赖并用允许使用的视频/摄像头验证。
- [ ] 人工可用性、负载测量、团队贡献和最终录像。
