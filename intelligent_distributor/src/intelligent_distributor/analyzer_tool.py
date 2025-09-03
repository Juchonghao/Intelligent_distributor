import os
import json
import logging
import dashscope
from dashscope.api_entities.dashscope_response import Role

from nat.builder.builder import Builder
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.function import FunctionBaseConfig

from typing import AsyncGenerator

logger = logging.getLogger(__name__)

class VideoAnalyzerConfig(FunctionBaseConfig, name="video_analyzer"):
    description: str
    model_name: str = "qwen-vl-max"

@register_function(config_type=VideoAnalyzerConfig)
async def analyze_video(config: VideoAnalyzerConfig, builder: Builder):

    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("错误：找不到 DASHSCOPE_API_KEY 環境變數。")

    # 设置 API Key
    dashscope.api_key = api_key

    async def _inner(video_file_path: str) -> str:
        logger.info(f"开始使用 Dashscope SDK 分析影片: {video_file_path}")

        try:
            local_file_uri = f'file://{video_file_path}'

            prompt_text = (
                "你是一位资深的社交媒体运营专家。请分析我上传的这个视频，从画面风格、视频节奏、"
                "内容主题、时长、横竖屏等维度，判断它最适合发布在哪个平台。请从 B站、YouTube、"
                "小红书、抖音 这四个选项中，给出你的推荐和详细理由，并以一个JSON对象格式输出结果，"
                "包含 'recommendations' 键，其值为一个列表，每个列表项包含 'platform', 'suitability' (从1到5的数字), 和 'reason' 三个键。"
            )

            messages = [{
                'role': Role.USER,
                'content': [
                    {'text': prompt_text},
                    # 直接将本地文件路径传给 SDK
                    {'video': local_file_uri}
                ]
            }]

            response = dashscope.MultiModalConversation.call(
                model=config.model_name,
                messages=messages
            )

            if response.status_code == 200:
                analysis_result = response.output.choices[0].message.content
                logger.info(f"模型分析结果: {analysis_result}")
                return analysis_result
            else:
                error_msg = f"API 请求失败: Code: {response.code}, Message: {response.message}"
                logger.error(error_msg)
                return error_msg

        except Exception as e:
            logger.error(f"影片分析过程中发生错误: {e}")
            return f"分析失败: {e}"

    yield FunctionInfo.from_fn(_inner, description=config.description)
