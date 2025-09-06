import os
import yaml
import shutil
import tempfile
import uvicorn
import json
import asyncio
import traceback
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse


from nat.builder.workflow_builder import WorkflowBuilder
from nat.data_models.config import Config
from nat.runtime.loader import PluginTypes, discover_and_register_plugins

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    應用程式生命週期管理。
    """
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
            print("AI代理构建器 (Builder) 已成功创建并准备就緒。")
            app.state.builder = builder
            yield

    except Exception as e:
        print(f"错误：AI代理在启动时初始化失败: {e}\n{traceback.format_exc()}")
        app.state.builder = None
        yield

    print("应用关闭事件 (lifespan)...")


app = FastAPI(title="智能视频分发代理 API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.post("/api/login")
async def login_to_platform(request: Request, platform: str = Form(...)):
    """
    觸發指定平台的登入工具。
    """
    builder = request.app.state.builder
    if not builder:
        raise HTTPException(status_code=500, detail="AI代理未能初始化。")

    # [修正] 在平台對應表中加入 B 站
    platform_map = {
        "小红书": "xiaohongshu",
        "B站": "bilibili"
    }
    platform_id = platform_map.get(platform)
    if not platform_id:
        raise HTTPException(status_code=400, detail=f"不支持的平台: {platform}")

    tool_name = f"{platform_id}_login"
    print(f"准备调用登入工具: {tool_name}")

    try:
        login_tool = builder.get_function(tool_name)
        # 傳入工具 schema 所需的 dummy 參數
        result = await login_tool.ainvoke({"dummy": "start"})

        if result:
             return {"status": "success", "message": f"登入 {platform} 成功，請檢查伺服器端彈出的瀏覽器視窗完成掃碼。"}
        else:
             return {"status": "pending", "message": "登入流程已啟動但可能需要手動操作。"}

    except Exception as e:
        print(f"登入 {platform} 时发生错误: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"登入 {platform} 失败: {str(e)}")


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
        input_args = {"video_file_path": temp_file_path}
        result_chunks = await video_analyzer_tool.ainvoke(input_args)

        if not isinstance(result_chunks, list):
             return {"raw_result": "Agent did not return a valid list."}

        full_raw_text = "".join(chunk.get("text", "") for chunk in result_chunks if isinstance(chunk, dict))
        print(f"拼接后的完整文本: {full_raw_text}")

        try:
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
        print(f"处理请求时发生错误: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

@app.post("/api/upload")
async def upload_to_platform_endpoint(
    request: Request,
    video: UploadFile = File(...),
    platform: str = Form(...),
    title: Optional[str] = Form(""),
    description: Optional[str] = Form(""),
    tags_json: Optional[str] = Form("[]")
):
    builder = request.app.state.builder
    if not builder:
        raise HTTPException(status_code=500, detail="AI代理未能初始化。")

    platform_map = { "小红书": "xiaohongshu", "B站": "bilibili", "YouTube": "youtube", "抖音": "douyin" }
    platform_id = platform_map.get(platform)
    if not platform_id:
        raise HTTPException(status_code=400, detail=f"不支持的平台: {platform}")

    tool_name = f"{platform_id}_upload_video"
    print(f"准备调用工具: {tool_name}")

    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(video.filename)[1]) as tmp_file:
            shutil.copyfileobj(video.file, tmp_file)
            temp_file_path = tmp_file.name

        upload_tool = builder.get_function(tool_name)
        tags = json.loads(tags_json)
        input_args = {
            "video_path": temp_file_path,
            "title": title,
            "description": description,
            "tags": tags
        }

        print(f"调用工具 '{tool_name}'，参数: {input_args}")
        result = await upload_tool.ainvoke(input_args)
        print(f"工具 '{tool_name}' 返回结果: {result}")

        return {"status": "success", "message": f"视频已成功上传至 {platform}", "details": result}

    except Exception as e:
        print(f"上传至 {platform} 时发生错误: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"上传至 {platform} 失败: {str(e)}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

@app.post("/api/generate_thumbnail")
async def generate_video_thumbnail(
    request: Request,
    video: UploadFile = File(...),
    timestamp: str = Form(...),
    title: Optional[str] = Form(None),
    language: Optional[str] = Form('zh')
):
    builder = request.app.state.builder
    if not builder:
        raise HTTPException(status_code=500, detail="AI代理未能初始化。")

    tool_name = "video_thumbnail_generation"
    print(f"准备调用工具: {tool_name}")

    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(video.filename)[1]) as tmp_file:
            shutil.copyfileobj(video.file, tmp_file)
            temp_file_path = tmp_file.name

        thumbnail_tool = builder.get_function(tool_name)
        input_args = {
            "video_path": temp_file_path,
            "timestamp": timestamp,
            "title": title,
            "language": language
        }

        print(f"调用工具 '{tool_name}'，参数: {input_args}")
        new_video_path = await thumbnail_tool.ainvoke(input_args)
        print(f"工具 '{tool_name}' 返回结果: {new_video_path}")

        if not os.path.exists(new_video_path):
            raise HTTPException(status_code=500, detail="工具执行成功，但未能找到生成的视频文件。")

        # [重要修改] 返回文件本身，而不是 JSON
        # 这允许前端直接接收和预览新视频
        return FileResponse(
            path=new_video_path,
            media_type='video/mp4',
            filename=os.path.basename(new_video_path)
            # 注意：这里我们不再删除临时文件，因为需要将它发送出去。
            # 在生产环境中需要一个独立的任务来清理这些文件。
        )

    except Exception as e:
        print(f"生成封面时发生错误: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"生成封面失败: {str(e)}")

@app.get("/")
def read_root():
    return {"status": "智能视频分发代理API正在运行"}

