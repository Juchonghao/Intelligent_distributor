好的，完全明白。我们省略大段的具体代码，专注于提供一个清晰的、可操作的**设置与运行流程**，作为现有`README.md`的补充或核心部分。

-----

## 🚀 快速运行指南 (Quick Start Guide)

本项目是一个包含前端、后端和AI代理的完整应用。请按照以下步骤启动和运行。

### 1\. 环境与依赖准备

在开始之前，请确保您的基础环境已就绪，并安装本项目所需的特定依赖。

```bash
# 安装阿里通义千问SDK，用于视频分析
uv pip install dashscope

# 安装FastAPI及其Web服务器，用于构建后端接口
uv pip install fastapi "uvicorn[standard]"
```

```bash
# 创建python环境
uv venv --seed .venv 
source .venv/bin/activate
```

### 2\. 关键文件配置

* **`server.py`** (位于项目根目录):
  这是我们的FastAPI后端服务。它负责创建一个 `/api/analyze` 接口，接收前端上传的视频，将其存为临时文件，然后通过调用 `nat run` 命令行来执行AI代理的分析任务，最后将结果返回给前端。

* **`index.html`** (位于项目根目录):
  这是与用户交互的前端界面。它提供了一个文件上传区域，并通过JavaScript将视频发送到后端的 `/api/analyze` 接口，然后将返回的AI分析结果动态地展示在页面上。

### 3\. 配置 API Key

本项目需要调用通义千问模型，请在您的终端中设置API Key环境变量：

```bash
export DASHSCOPE_API_KEY='sk-xxxxxxxxxxxxxxxx'
```

> **提示**: 请将 `sk-xxx...` 替换为您自己的真实API Key。

### 4\. 安装/注册自定义工具

配置完成后，运行以下命令来正式安装并注册您的自定义工作流。这个命令会读取 `pyproject.toml` 中的设置，让 `nat` 框架识别您的工具。

请在 `NeMo-Agent-Toolkit` 的根目录下运行：

```bash
nat workflow reinstall intelligent_distributor
```

看到 `Workflow 'intelligent_distributor' reinstalled successfully.` 即表示成功。

### 添加小红书mcp
```bash
# 要先进行安装
cd xiaohongshu_mcp
uv pip install -e .
cd ..
cd bilibili_mcp
uv pip install -e .
cd ..
cd video_thumbnail_mcp
uv pip install -e .
cd ..

# 注册视频封面处理工具
# 需要先安装ffmpeg
macOS: 使用 Homebrew: brew install ffmpeg
Linux (Ubuntu/Debian): sudo apt update && sudo apt install ffmpeg
uv pip install ffmpeg-python

nat workflow reinstall xiaohongshu_mcp
nat workflow reinstall bilibili_mcp
nat workflow reinstall video_thumbnail_generation


# 注册小红书 mcp服务
nat mcp --config_file xiaohongshu_mcp/src/xiaohongshu_mcp/configs/config.yml \
  --host 0.0.0.0 \
  --port 9901 \
  --name "My MCP Server"\
  --tool_names xiaohongshu_login \
  --tool_names xiaohongshu_check_login_status\
  --tool_names xiaohongshu_upload_video
  
nat mcp --config_file bilibili_mcp/src/bilibili_mcp/configs/config.yml \
  --host 0.0.0.0 \
  --port 9902 \
  --name "My MCP Server"\
  --tool_names bilibili_login \
  --tool_names bilibili_upload_video  

nat mcp --config_file video_thumbnail_mcp/src/video_thumbnail_mcp/configs/config.yml \
  --host 0.0.0.0 \
  --port 9903 \
  --name "My MCP Server"\
  --tool_names video_thumbnail_generation
```

### 本地跑

```bash
nat nat run --config_file intelligent_distributor/src/intelligent_distributor/configs/config.yml --input "請分析这个影片 '[本地视频地址]'，並告訴我它適合發布到哪些平台。"
```
便能看到Video analyzer agent对于视频的分析和平台推荐

### 5\. 启动并运行！

一切就绪！现在您可以启动服务并与之交互。

**a. 启动后端服务**

在 `NeMo-Agent-Toolkit` 根目录下，运行以下命令：

```bash
uvicorn intelligent_distributor_server:app --reload
```

服务将在 `http://127.0.0.1:8000` 启动。

**b. 打开前端界面**

打开**一个新的终端**，同样在 `NeMo-Agent-Toolkit` 根目录下，运行以下命令在浏览器中打开前端页面：

```bash
cd intelligent_distributor_frontend
npm install 
npm run dev

# for macOS
#open intelligent_distributor.html
#
## for Windows
#start intelligent_distributor.html
#
## for Linux
#xdg-open intelligent_distributor.html
```

现在，您可以在打开的网页上上传视频，体验完整的AI分析流程了。