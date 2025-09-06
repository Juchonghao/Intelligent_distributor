import os
import time
import base64
import logging
import ffmpeg
import requests
import mimetypes

from nat.builder.builder import Builder
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.function import FunctionBaseConfig

from openai import OpenAI
from dashscope import MultiModalConversation

logger = logging.getLogger(__name__)


class VideoThumbnailConfig(FunctionBaseConfig, name="video_thumbnail_generation"):
    save_path:str = ".data/video_thumbnail.png"
    zh_image_edit_model: str = "qwen-image-edit"
    en_image_edit_model: str = "google/gemini-2.5-flash-image-preview"

# --- Helper functions ---
def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def download_image(url: str, save_path: str) -> bool:
    print(f"--- 正在從 URL 下載圖片: {url[:80]}... ---")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"✅ 圖片下載成功，已儲存為: {save_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ 下載圖片時發生錯誤: {e}")
        return False

def extract_frame_at_timestamp(video_path, timestamp, output_path):
    try:
        (
            ffmpeg
            .input(video_path, ss=timestamp)
            .output(output_path, vframes=1, qscale=2)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        logger.info(f"成功在 {timestamp} 提取幀，並儲存為 {output_path}")
    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else "N/A"
        logger.error(f"FFmpeg 提取幀時出錯: {stderr}")

# [REVISED] Simpler function to get the video's STORED resolution.
def get_video_resolution(video_path: str) -> tuple[int, int] | None:
    """Gets the stored width and height of the video, ignoring rotation."""
    try:
        probe = ffmpeg.probe(video_path)
        video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
        if video_stream:
            width = int(video_stream['width'])
            height = int(video_stream['height'])
            logger.info(f"偵測到影片儲存解析度: {width}x{height}")
            return width, height
        else:
            logger.error("❌ 錯誤：在影片中找不到視訊流。")
            return None
    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else "N/A"
        logger.error(f"❌ FFmpeg 執行時發生錯誤: {stderr}")
        return None

# [REVISED] Rewritten to use the more robust 'overlay' filter
def add_cover_to_video(cover_path: str, video_path: str, output_path: str, duration: int = 2) -> bool:
    """Adds a cover to the beginning of a video using the overlay filter."""
    logger.debug("\n" + "=" * 50)
    logger.debug("🎬 使用 overlay 策略將封面合成到影片...")

    resolution = get_video_resolution(video_path)
    if not resolution:
        logger.error("無法繼續，因為無法獲取影片解析度。")
        return False
    width, height = resolution

    try:
        # Define the two inputs
        main_video = ffmpeg.input(video_path)
        cover_image = ffmpeg.input(cover_path)

        # Prepare the cover by scaling it to the video's stored resolution
        scaled_cover = cover_image.video.filter('scale', width, height)

        # Overlay the scaled cover on top of the main video
        # The 'enable' option makes it only appear for the specified duration
        overlaid_video = main_video.video.overlay(
            scaled_cover,
            enable=f'between(t,0,{duration})'
        )

        # Combine the new video stream with the original audio stream
        stream = ffmpeg.output(
            overlaid_video,
            main_video.audio,
            output_path,
            **{'c:v': 'libx264', 'c:a': 'aac', 'movflags': '+faststart'}
        )

        logger.info("正在執行 FFmpeg overlay 指令...")
        stream.run(overwrite_output=True, quiet=True)

        logger.info(f"🎉 影片合成成功！最終影片已儲存為: {output_path}")
        return True
    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else "N/A"
        logger.error(f"❌ FFmpeg 執行時發生錯誤: {stderr}")
        return False
    except Exception as e:
        logger.error(f"❌ 發生未知錯誤: {e}")
        return False

# ... AI functions (zh_ai_process_video_thumbnail, en_ai_process_video_thumbnail) remain unchanged ...
def zh_ai_process_video_thumbnail(img_path: str, prompt: str, model_name: str) -> bool:
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        logger.warning("找不到用来进行中文图像编辑的模型 DASHSCOPE_API_KEY 环境变量。默认使用原始帧")
        return False
    mime_type, _ = mimetypes.guess_type(img_path)
    base64_image = encode_image_to_base64(img_path)
    image_data=f"data:{mime_type};base64,{base64_image}"

    messages = [ { "role": "user", "content": [ {"image": image_data}, {"text": prompt} ] } ]
    logger.info(f"--- 正在调用 AI 模型 {model_name} 进行封面生成，这可能需要一些时间... ---")
    response = MultiModalConversation.call( model=model_name, messages=messages)

    if response.status_code == 200:
        content = response.output.choices[0].message.content
        image_url = content[0]['image']
        if download_image(image_url, img_path):
            logger.info(f"🎉 封面改造成功，保存在: {img_path}")
            return True
        else:
            return False
    else:
        logger.error(f"❌ DashScope API 錯誤: HTTP {response.status_code}, Code: {response.code}, Msg: {response.message}")
        return False

def en_ai_process_video_thumbnail(img_path: str, prompt: str, model_name: str) ->bool:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.warning("找不到用来进行中文图像编辑的模型 OPENROUTER_API_KEY 环境变量。默认使用原始帧")
        return False

    content_list = [{"type": "text", "text": prompt}]
    base64_image = encode_image_to_base64(img_path)
    content_list.append({ "type": "image_url", "image_url": { "url": f"data:image/png;base64,{base64_image}" } })
    client = OpenAI( base_url="https://openrouter.ai/api/v1", api_key=api_key,)
    logger.info(f"--- 正在调用 AI 模型 {model_name} 进行封面生成，这可能需要一些时间... ---")

    try:
        completion = client.chat.completions.create( model=model_name, messages=[ { "role": "user", "content": content_list } ], max_tokens=4096 )
        response_data = completion.model_dump()
        image_url_string = response_data.get('choices', [{}])[0].get('message', {}).get('images', [{}])[0].get('image_url', {}).get('url')
        if image_url_string and image_url_string.startswith('data:image/png;base64,'):
            base64_data = image_url_string.replace('data:image/png;base64,', '')
            logger.debug("✅ 成功定位到 Base64 data. 正在保存...")
            image_data = base64.b64decode(base64_data)
            with open(img_path, 'wb') as f: f.write(image_data)
            logger.info(f"🎉 封面改造成功，保存在: {img_path}")
            return True
        else:
            logger.error(f"❌ 封面改造失败")
            return False
    except Exception as e:
        print(f"调用 API 时发生错误: {e}")
        return False

@register_function(config_type=VideoThumbnailConfig)
async def video_thumbnail_generation(tool_config: VideoThumbnailConfig, builder: Builder):
    async def _video_thumbnail_generation(video_path: str, timestamp: str, title: str = None, language: str = 'zh') -> str:
        base_output_path = f"{tool_config.save_path}_{int(time.time())}"
        keyframe_path = f"{base_output_path}_keyframe.png"
        extract_frame_at_timestamp(video_path, timestamp, keyframe_path)

        if not os.path.exists(keyframe_path):
            logger.error(f"關鍵幀提取失敗，無法找到檔案：{keyframe_path}。返回原始影片路徑。")
            return video_path

        ai_processed_cover_path = keyframe_path
        if title:
            logger.info(f"標題為 '{title}'，語言為 '{language}'，準備呼叫 AI 進行封面改造...")
            prompt_text = f'你是一位顶尖的封面设计师。请使用我提供的这张图片作为基础，将以下文字标题创意地、清晰地融入画面中，生成一张吸引人的视频封面。\n要嵌入的标题是: "{title}"'
            ai_process_success = False
            if language.lower() == 'zh':
                ai_process_success = zh_ai_process_video_thumbnail(
                    img_path=keyframe_path, prompt=prompt_text, model_name=tool_config.zh_image_edit_model
                )
            elif language.lower() == 'en':
                ai_process_success = en_ai_process_video_thumbnail(
                    img_path=keyframe_path, prompt=prompt_text, model_name=tool_config.en_image_edit_model
                )
            if ai_process_success:
                logger.info("AI 封面改造成功。")
            else:
                logger.warning("AI 封面改造失敗或未執行，將使用原始提取的關鍵幀。")

        file_root, file_ext = os.path.splitext(video_path)
        new_video_path = f"{file_root}_ai{file_ext}"
        if add_cover_to_video(ai_processed_cover_path, video_path, new_video_path):
            return new_video_path
        else:
            return video_path

    yield FunctionInfo.from_fn(
        _video_thumbnail_generation,
        description=("这是视频封面生成和改造工具，返回新生成的视频路径（如果处理失败，则返回原路径）"
                     "该工具需要输入视频路径信息、封面所在的时间戳，以及需要在封面上添加的文字信息和文字语言类型（可选）"))