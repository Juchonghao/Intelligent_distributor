import os
import yaml
import shutil
import tempfile
import uvicorn
import json
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from nat.builder.workflow_builder import WorkflowBuilder
from nat.data_models.config import Config
from nat.runtime.loader import PluginTypes, discover_and_register_plugins

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("应用启动事件 (lifespan)...")
    try:
        discover_and_register_plugins(PluginTypes.ALL)
        print("所有插件加载完毕。")

        CONFIG_PATH = "intelligent_distributor/src/intelligent_distributor/configs/config.yml"
        with open(CONFIG_PATH, "r") as f:
            config_dict = yaml.safe_load(f)

        config_obj = Config(**config_dict)
        builder_context_manager = WorkflowBuilder.from_config(config_obj)

        async with builder_context_manager as builder:
            print("AI代理构建器 (Builder) 已成功创建并准备就绪。")
            app.state.builder = builder
            yield

    except Exception as e:
        print(f"错误：AI代理在启动时初始化失败: {e}")
        app.state.builder = None
        yield

    print("应用关闭事件 (lifespan)...")


app = FastAPI(title="智能视频分发代理 API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.post("/api/analyze")
async def analyze_video_endpoint(request: Request, video: UploadFile = File(...)):
    builder = request.app.state.builder
    if not builder:
        raise HTTPException(status_code=500, detail="AI代理未能初始化，请检查启动日志。")

    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(video.filename)[1]) as tmp_file:
            shutil.copyfileobj(video.file, tmp_file)
            temp_file_path = tmp_file.name

        video_analyzer_tool = builder.get_function("video_analyzer")
        print(f"直接获取函数对象: {video_analyzer_tool}")

        input_args = {"video_file_path": temp_file_path}
        result_chunks = await video_analyzer_tool.ainvoke(input_args)
        print(f"收到工具的直接返回结果 (分块): {result_chunks}")

        # --- 这是最终的、正确的修正 ---
        # 1. 检查返回的是否是列表
        if not isinstance(result_chunks, list):
             return {"raw_result": "Agent did not return a valid list."}

        # 2. 拼接所有文本片段
        full_raw_text = "".join(chunk.get("text", "") for chunk in result_chunks if isinstance(chunk, dict))
        print(f"拼接后的完整文本: {full_raw_text}")

        try:
            # 3. 对拼接后的完整文本进行清理和解析
            if '```json' in full_raw_text:
                cleaned_text = full_raw_text.split('```json\n', 1)[1].rsplit('\n```', 1)[0]
            else:
                cleaned_text = full_raw_text

            analysis_json = json.loads(cleaned_text)
            return analysis_json
        except (json.JSONDecodeError, IndexError, TypeError):
            print(f"JSON解析失败, full_raw_text was: {full_raw_text}")
            return {"raw_result": result_chunks}

    except Exception as e:
        import traceback
        print(f"处理请求时发生错误: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            print(f"临时文件已删除: {temp_file_path}")


@app.get("/")
def read_root():
    return {"status": "智能视频分发代理API正在运行"}

