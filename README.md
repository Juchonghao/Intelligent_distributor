# 智能视频分发代理 (Intelligent Video Distribution Agent)

> 一个基于 NVIDIA NeMo Agent Toolkit 构建的 AI 驱动、端到端自动化视频内容分发解决方案。

[**🎬 查看项目 Demo 演示**](https://www.bilibili.com/video/BV1S9aqzXEKs)

---

## 🚀 项目概述

### 项目背景

在当今的创作者经济时代，视频内容已成为信息传播的主流。然而，内容创作者和运营团队普遍面临着效率低下的困境：为不同平台撰写标题、描述，设计吸引人的封面，以及手动登录多个账户进行发布，这些重复性劳动占用了大量本可用于内容创新的时间。

本项目旨在利用 **NVIDIA NeMo Agent Toolkit** 和多模态大语言模型，构建一个一站式的智能视频分发解决方案。通过分析用户上传的视频，系统能自动生成高质量的元数据、AI 封面，并一键发布至B站、小红书等多个平台，将创作者从繁琐的运营工作中解放出来。

### 团队介绍

* **队名**: ThePAI

* **团队理念**: 让创造回归创意，让分发回归智能。

---

## 🎯 核心亮点与用户痛点

### 💢 用户痛点

* **重复劳动耗时**: 为每个视频、每个平台手动撰写标题、描述和标签，过程枯燥且耗费大量时间。

* **跨平台运营复杂**: 不同平台的社区文化和内容偏好各异，难以针对性地优化内容以获得最佳表现。

* **封面制作门槛高**: 设计一张吸引眼球的视频封面通常需要专业的设计技能和软件，对普通创作者构成挑战。

* **分发效率低下**: 手动登录、上传、填写信息至多个平台，流程繁琐，容易出错，且难以规模化。

### ✅ 项目亮点

* **端到端自动化流程**: 从上传原始视频到最终多平台发布，实现了全流程自动化，将数小时的工作压缩至几分钟。

* **AI 智能分析与创作**: 基于多模态大模型（如通义千问、Nano Banana）深度理解视频内容，智能生成与视频风格及平台特性相匹配的标题、描述和标签。

* **智能化封面生成**: 独创的封面生成工具，结合 AI 图像美化与 FFmpeg 精准文字叠加技术，一键生成高质量、高相关性的视频封面。

* **基于 NVIDIA MCP 的微服务架构**: 核心功能（如平台登录、上传、封面生成）被封装为独立的 MCP 微服务，确保了系统的稳定性、模块化和未来高度的可扩展性。

---

## 🛠️ 技术栈与系统架构

### 核心技术栈

* **AI 代理框架**: **NVIDIA NeMo Agent Toolkit** - 作为项目的基石，负责所有 AI 工具的定义、注册、管理和执行。

* **后端服务**: **FastAPI** - 提供高性能的异步 API 接口，作为前后端交互的桥梁。

* **前端框架**: **React** & [**React Bits**](https://reactbits.dev/) - 构建现代化、响应式的用户交互界面。

* **核心依赖**:

  * `ffmpeg-python`: 用于处理视频，包括提取关键帧、添加封面等。

  * `Dashscope`, `Openai`, `Gemini`: 用于调用大语言模型 API。

  * `playwright`: 用于实现平台自动化登录的浏览器模拟。

  * `uvicorn`: ASGI 服务器，用于运行 FastAPI 应用。

### 系统架构

本系统采用前后端分离的微服务架构，其核心交互流程如下：

1. **前端 (React)**: 用户通过浏览器上传视频并发起任务。

2. **主后端 (FastAPI Server)**: 作为总控制器，接收前端请求，并调用 NeMo Agent Toolkit 的工作流和工具。

3. **NeMo Agent Toolkit**:

   * **工作流 (Workflow)**: `intelligent_distributor` 工作流负责执行核心的视频分析任务。

   * **MCP 工具服务 (MCP Tool Servers)**: 多个独立的微服务，分别处理特定任务（如B站登录、小红书上传、封面生成）。

4. **外部服务**: 包括各大视频平台（B站、小红书）和 AI 模型提供商（通义千问, OpenAI, Gemini Nano Banana）。

---

## ⚙️ 主要功能模块详解

### 视频分析代理 (`video_analyzer`)

* **技术**: NeMo Agent Workflow

* **功能**: 接收视频文件路径，调用通义千问多模态VLM分析视频内容，生成 JSON 格式的结构化数据，包括推荐标题、描述、标签，以及针对不同平台（B站、小红书、抖音）的发布建议和适配度评分。

### AI 视频封面生成工具 (`video_thumbnail_generation`)

* **技术**: NeMo Agent MCP Tool, FFmpeg, AI Image Models (中文版使用通义千问，英文版使用 Nano Banana)

* **功能**:

  1. 从视频指定时间戳提取一帧高质量关键帧。

  2. 调用 AI 图像模型对关键帧进行美化，优化构图与色彩。

  3. 使用 FFmpeg 的 `drawtext` 滤镜将标题精确地叠加在美化后的封面上。

  4. 将最终生成的封面图与原视频合并，生成一个带封面的新视频文件。

### 多平台登录与上传工具

* **技术**: NeMo Agent MCP Tools, Playwright, `bilibili-api-python`

* **模块**:

  * `bilibili_login` & `xiaongshu_login`: 启动 Playwright 浏览器，用户通过扫描二维码完成登录，程序自动捕获并保存 Cookies。

  * `bilibili_upload_video` & `xiaongshu_upload_video`: 使用已保存的 Cookies，调用 API 或通过浏览器自动化完成视频上传。

### 前后端 API (`intelligent_distributor_server.py`)

* **技术**: FastAPI

* **主要接口**: `/api/analyze`, `/api/login`, `/api/generate_thumbnail`, `/api/upload`。

---

## 📦 安装与部署指南

### 步骤 1: 环境准备

1. **安装 Python 环境**: 推荐使用 `uv` 创建虚拟环境。

   ```bash
   uv venv --seed .venv
   source .venv/bin/activate

2.  **安装 FFmpeg**:

   * **macOS**: `brew install ffmpeg`

   * **Linux (Ubuntu/Debian)**: `sudo apt update && sudo apt install ffmpeg`

### 步骤 2: 安装项目依赖

```bash
# 安装 Web 后端服务
uv pip install fastapi "uvicorn[standard]"

# 安装 AI 模型 SDK
uv pip install dashscope openai

# 安装视频封面生成工具的依赖
uv pip install ffmpeg-python requests

# 安装 B 站和小红书工具的依赖
uv pip install playwright "bilibili-api-python>=17.0.0"
playwright install # 下载浏览器核心
```

### 步骤 3: 配置 API Keys

在终端中设置所需模型的 API Key 环境变量：

```bash
# 阿里通义千问 API Key (用于视频分析和中文封面美化)
export DASHSCOPE_API_KEY='sk-xxxxxx'

# (可选) 用于英文封面美化的 API Key
export OPENROUTER_API_KEY='sk-xxxxxx'
```

### 步骤 4: 安装并注册 NeMo Agent 工具

进入 `NeMo-Agent-Toolkit` 项目根目录，逐一安装并注册所有自定义工作流和工具。

```bash
# 进入各个工具目录并以可编辑模式安装
cd intelligent_distributor && uv pip install -e . && cd ..
cd bilibili_mcp && uv pip install -e . && cd ..
cd xiaohongshu_mcp && uv pip install -e . && cd ..
cd video_thumbnail_mcp && uv pip install -e . && cd ..

# 使用 nat 命令重新加载所有已安装的工具
nat workflow reinstall intelligent_distributor
nat workflow reinstall bilibili_mcp
nat workflow reinstall xiaohongshu_mcp
nat workflow reinstall video_thumbnail_mcp
```

### 步骤 5: 启动所有服务

> **注意**: 需要开启多个终端窗口来分别启动各项服务。

* **终端 1: 启动 Bilibili MCP 服务**

  ```bash
  nat mcp --config_file bilibili_mcp/src/bilibili_mcp/configs/config.yml --port 9902
  ```

* **终端 2: 启动小红书 MCP 服务**

  ```bash
  nat mcp --config_file xiaohongshu_mcp/src/xiaohongshu_mcp/configs/config.yml --port 9901
  ```

* **终端 3: 启动视频封面生成 MCP 服务**

  ```bash
  nat mcp --config_file video_thumbnail_mcp/src/video_thumbnail_mcp/configs/config.yml --port 9903
  ```

* **终端 4: 启动主后端 FastAPI 服务**

  ```bash
  uvicorn intelligent_distributor_server:app --reload --port 8000
  ```

* **终端 5: 启动前端开发服务器**

  ```bash
  cd intelligent_distributor_frontend
  npm install
  npm run dev
  ```

服务全部启动后，浏览器会自动打开 `http://localhost:5173` (或类似地址)。

-----

## 📈 商业价值与风险

### 市场局势分析

在内容为王的时代，创作者经济和 MCN 机构正以前所未有的速度发展。市场对于能够提升内容生产和分发效率的工具（AIGC aPaaS）存在巨大的需求。我们的产品精准切入这一赛道，为个人创作者、MCN 机构及企业品牌的内容营销团队提供了一个强大的“效率倍增器”。产品目前处于原型验证阶段，未来将面向 To B 和 To C Pro 市场，提供SaaS订阅服务。

### 产品风险评估

1.  **平台接口变更风险**: 社交媒体平台的前端或 API 可能会更新，导致自动化脚本失效，需要持续维护。

2.  **AI 内容质量稳定性**: AI 生成的内容虽然质量较高，但偶尔可能缺乏创意或与热点脱节，仍需用户进行最终审核。

3.  **视频分析准确性**: 对于内容抽象、无明确主题的视频，AI 的分析结果可能存在偏差。

4.  **数据隐私与安全**: 系统需要处理用户的平台凭证（Cookies），必须采用高级别的安全措施确保数据不被泄露。

-----

## 🔮 未来展望

### 功能扩展

* **支持更多平台**: 逐步增加对 YouTube、抖音、快手等主流视频平台的支持。

* **数据分析与反馈闭环**: 追踪视频发布后的表现，将数据反馈给 AI 模型，以优化未来的推荐策略。

* **智能排程发布**: 根据各平台的用户活跃时间，提供最佳发布时间的建议，并支持定时发布。

### 技术升级

* **迁移至 NVIDIA NIMs**: 将计算密集型任务从调用外部 API 迁移至由 **NVIDIA NIMs (NVIDIA Inference Microservices)** 部署的私有化 NeMo 模型，以获得更高的性能、更低的成本和更好的数据隐私保护。

* **GPU 加速视频处理**: 利用 NVIDIA GPU 和相关库（如 Video Codec SDK）加速 FFmpeg 的视频编解码过程。

### 商业模式探索

* **SaaS 订阅模式**: 针对个人创作者和小型团队，提供不同级别的月度/年度订阅服务。

* **企业级解决方案**: 为大型 MCN 机构和品牌提供定制化的私有部署方案和技术支持。

-----

## 🤝 团队贡献

* **前端开发 (王宇)**: 负责 UI/UX 设计与实现，包括粒子背景、渐变色彩、动画过渡等，确保界面美观、现代、交互友好。实现前端完整的功能逻辑，确保用户操作流程顺畅。

* **后端与 AI 代理开发 (Brad, 王宇)**: 设计并实现基于 FastAPI 和 NVIDIA NeMo Agent Toolkit 的后端架构，开发所有核心 Agentic 工作流和 MCP 工具，确保系统稳定、高效、可扩展。

* **测试与优化 (刘凡, 雷蕾, 大仁)**: 负责全面的系统测试，包括功能、性能与安全测试，发现并修复 bug。同时根据用户反馈，持续进行用户体验优化和流程改进。

-----

## ✨ 结论

智能视频分发代理项目成功地将 **NVIDIA NeMo Agent Toolkit** 的强大能力应用于解决内容创作领域的实际痛点。通过其创新的 MCP 微服务架构和端到端的自动化流程，本项目不仅极大地提升了视频分发效率，也为未来构建更复杂的 AI 代理应用生态奠定了坚实的基础。
