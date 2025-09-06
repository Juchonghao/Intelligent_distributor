智能视频分发代理 - 项目技术文档
1. 项目简介
   智能视频分发代理 (Intelligent Video Distribution Agent) 是一个基于 AI 技术的自动化内容分发解决方案。该系统能够接收用户上传的视频文件，通过多模态大语言模型进行深度分析，自动生成适配不同社交媒体平台的标题、描述和标签，并推荐最适合的分发平台。此外，它还集成了 AI 驱动的视频封面生成和多平台自动化登录、上传功能，旨在将繁琐的视频发布流程简化为一键式操作。

2. 技术栈与架构
   2.1 核心技术栈
   AI 代理框架: NVIDIA NeMo Agent Toolkit - 作为项目的基石，负责所有 AI 工具的定义、注册、管理和执行。

后端服务: FastAPI - 提供高性能的异步 API 接口，作为前后端交互的桥梁，并负责调用 NeMo Agent 工作流。

前端框架: React & https://reactbits.dev/ 框架，构建现代化、响应式的用户交互界面。

核心依赖:

ffmpeg-python: 用于处理视频，包括提取关键帧、添加封面等。

Dashscope, Openai, Gemini: 用于调用大语言模型 API。

playwright: 用于实现平台自动化登录的浏览器模拟。

uvicorn: ASGI 服务器，用于运行 FastAPI 应用。

2.2 系统架构
本系统采用前后端分离的微服务架构，其核心交互流程如下：

前端 (React): 用户通过浏览器与系统交互，上传视频并发起任务。

主后端 (FastAPI Server): 作为总控制器，接收前端请求，并调用 NeMo Agent Toolkit 的工作流和工具。

NeMo Agent Toolkit:

工作流 (Workflow): intelligent_distributor 工作流负责执行核心的视频分析任务。

MCP 工具服务 (MCP Tool Servers): 多个独立的微服务，分别处理特定任务（如B站登录、小红书上传、封面生成），由主后端按需调用。

外部服务: 包括各大视频平台（B站、小红书）和 AI 模型提供商（通义千问, OpenAI, Gemini Nano banana）。

智能视频分发代理的架构流程图
3. 主要功能模块
   3.1 视频分析代理 (video_analyzer)
   技术: NeMo Agent Workflow

功能: 接收视频文件路径，调用多模态通义千问多模态 VLM 分析视频内容，生成 JSON 格式的结构化数据，包括推荐标题、描述、标签，以及针对不同平台（B站、小红书、抖音）的发布建议和适配度评分。

3.2 AI 视频封面生成工具 (video_thumbnail_generation)
技术: NeMo Agent MCP Tool, FFmpeg, AI Image Models (中文版使用通义千问，英文版使用 Nano Banana)

功能:

从视频指定时间戳提取一帧高质量关键帧。

调用 AI 图像模型对关键帧进行美化，优化构图与色彩，为添加文字做准备。

使用 FFmpeg 的 drawtext 滤镜将 AI 生成的标题精确地叠加在美化后的封面上。

将最终生成的封面图与原视频合并，生成一个带封面的新视频文件。

3.3 多平台登录与上传工具
技术: NeMo Agent MCP Tools, Playwright, bilibili-api-python

模块:

bilibili_login & xiaohongshu_login: 启动 Playwright 控制的浏览器，用户通过扫描二维码完成登录，程序自动捕获并保存 Cookies。

bilibili_upload_video & xiaohongshu_upload_video: 使用已保存的 Cookies，调用相应平台的 API 或通过浏览器自动化完成视频上传。

3.4 前后端 API (intelligent_distributor_server.py)
技术: FastAPI

主要接口:

/api/analyze: 接收视频，调用 video_analyzer 代理，返回分析结果。

/api/login: 接收平台名称，触发对应的登录 MCP 工具。

/api/generate_thumbnail: 接收视频和元数据，调用封面生成工具，返回带封面的新视频文件。

/api/upload: 接收视频和元数据，调用指定平台的上传 MCP 工具。

4. 安装与部署指南
   步骤 1: 环境准备
   安装 Python 环境: 推荐使用 uv 创建虚拟环境。

uv venv --seed .venv
source .venv/bin/activate


安装 FFmpeg: 视频处理的核心依赖。

macOS: brew install ffmpeg

Linux (Ubuntu/Debian): sudo apt update && sudo apt install ffmpeg

步骤 2: 安装项目依赖
# 安装 Web 后端服务
uv pip install fastapi "uvicorn[standard]"

# 安装 AI 模型 SDK
uv pip install dashscope openai

# 安装视频封面生成工具的依赖
uv pip install ffmpeg-python requests

# 安装 B 站和小红书工具的依赖
uv pip install playwright "bilibili-api-python>=17.0.0"
playwright install # 下载浏览器核心


步骤 3: 配置 API Keys
在终端中设置所需模型的 API Key 环境变量：

# 阿里通义千问 API Key (用于视频分析和中文封面美化)
export DASHSCOPE_API_KEY='sk-xxxxxx'

# (可选) 用于英文封面美化的 API Key
export OPENROUTER_API_KEY='sk-xxxxxx'


步骤 4: 安装并注册 NeMo Agent 工具
进入 NeMo-Agent-Toolkit 项目根目录，逐一安装并注册所有自定义工作流和工具。

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


步骤 5: 启动所有服务
需要开启多个终端窗口来分别启动各项服务。

终端 1: 启动 Bilibili MCP 服务

nat mcp --config_file bilibili_mcp/src/bilibili_mcp/configs/config.yml --port 9902


终端 2: 启动小红书 MCP 服务

nat mcp --config_file xiaohongshu_mcp/src/xiaohongshu_mcp/configs/config.yml --port 9901


终端 3: 启动视频封面生成 MCP 服务

nat mcp --config_file video_thumbnail_mcp/src/video_thumbnail_mcp/configs/config.yml --port 9903


终端 4: 启动主后端 FastAPI 服务

uvicorn intelligent_distributor_server:app --reload --port 8000


终端 5: 启动前端开发服务器

cd intelligent_distributor_frontend
npm install
npm run dev


服务全部启动后，浏览器会自动打开 http://localhost:5173 (或类似地址)，即可开始使用。

5. 使用流程
   登录平台: 在前端界面上，点击 "登入B站" 或 "登入小红书" 按钮。服务器端会弹出浏览器窗口，请按提示扫描二维码完成登录。

上传分析: 将视频文件拖拽或点击上传至网页。系统会自动调用后端 /api/analyze 接口。

查看结果: AI 分析完成后，界面会展示推荐的标题、描述、标签以及各平台的分发建议。

生成封面: （可选）点击 "一键生成封面" 按钮。系统将根据 AI 推荐的标题，在视频关键帧上生成精美封面，并更新视频预览。

一键上传: 在平台推荐卡片上，点击 "上传至 B站" (或小红书) 按钮，即可将带封面的视频和 AI 生成的文案自动发布到对应平台。

下一步计划：
接入海外的视频渠道
AI分析各频道最佳发布时间，并自动调用分发API分发