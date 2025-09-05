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

def encode_image_to_base64(image_path):
    """读取图片文件并返回其 Base64 编码的字符串。"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def download_image(url: str, save_path: str) -> bool:
    """
    從給定的 URL 下載圖片並儲存到本地。

    :param url: 圖片的 URL
    :param save_path: 儲存圖片的本地路徑
    :return: 成功返回 True，失敗返回 False
    """
    print(f"--- 正在從 URL 下載圖片: {url[:80]}... ---")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # 確保請求成功

        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"✅ 圖片下載成功，已儲存為: {save_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ 下載圖片時發生錯誤: {e}")
        return False

def extract_frame_at_timestamp(video_path, timestamp, output_path):
    """
    在指定的時間戳提取一幀畫面。
    :param video_path: 影片路徑
    :param timestamp: "HH:MM:SS.ms" 格式的時間戳字串
    :param output_path: 圖片儲存路徑
    """
    try:
        (
            ffmpeg
            .input(video_path, ss=timestamp)
            .output(output_path, vframes=1, q=':v 2')
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        logger.info(f"成功在 {timestamp} 提取幀，並儲存為 {output_path}")
    except ffmpeg.Error as e:
        logger.error(f"FFmpeg 提取幀時出錯:{e.stderr.decode()}")

def get_video_resolution(video_path: str) -> tuple[int, int] | None:
    """使用 ffprobe 自動偵測影片的寬和高。"""
    try:
        # ffprobe -v quiet -print_format json -show_streams your_video.mp4
        probe = ffmpeg.probe(video_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        if video_stream:
            width = int(video_stream['width'])
            height = int(video_stream['height'])
            logger.info(f"偵測到影片解析度: {width}x{height}")
            return width, height
        else:
            logger.error("❌ 錯誤：在影片中找不到視訊流。")
            return None
    except ffmpeg.Error as e:
        logger.error(f"❌ FFmpeg 執行時發生錯誤: {e.stderr.decode()}")
    except Exception as e:
        logger.error(f"❌ 發生未知錯誤: {e}")


def add_cover_to_video(cover_path: str, video_path: str, output_path: str, duration: int = 2) -> bool:
    """
    將一張封面圖添加到影片開頭。

    :param cover_path: 封面圖片路徑
    :param video_path: 原始影片路徑
    :param output_path: 最終輸出影片的路徑
    :param duration: 封面圖片顯示的時長（秒）
    """
    logger.debug("\n" + "=" * 50)
    logger.debug("🎬 開始將封面拼接到影片開頭...")
    logger.debug(f"  - 封面: {cover_path}")
    logger.debug(f"  - 影片: {video_path}")
    logger.debug(f"  - 封面時長: {duration} 秒")
    logger.debug("=" * 50)

    resolution = get_video_resolution(video_path)
    if not resolution:
        logger.error("無法繼續拼接，因為無法獲取影片解析度。")
        return False

    width, height = resolution

    try:
        # 定義輸入流
        cover_stream = ffmpeg.input(cover_path, loop=1, t=duration)
        video_stream = ffmpeg.input(video_path)

        # 預處理封面和影片
        processed_cover = (
            cover_stream.video
            .filter('scale', width, height, force_original_aspect_ratio='decrease')
            .filter('pad', width, height, -1, -1, color='black')
            .filter('format', 'yuv420p')
            .filter('setsar', 1)
        )
        processed_video = video_stream.video.filter('format', 'yuv420p').filter('setsar', 1)

        # 拼接視訊流
        concatenated_video = ffmpeg.concat(processed_cover, processed_video, v=1, a=0).node

        # 從原始影片中獲取音訊流
        main_audio = video_stream.audio

        # 執行並輸出
        stream = ffmpeg.output(
            concatenated_video[0],  # 拼接後的視訊節點
            main_audio,  # 原始影片的音訊節點
            output_path,
            **{'c:v': 'libx264', 'c:a': 'aac', 'movflags': '+faststart'}
        )

        logger.info("正在執行 FFmpeg 拼接指令...")
        # .run() 會自動生成並執行與上面指令類似的命令
        stream.run(overwrite_output=True)

        logger.info(f"🎉 拼接成功！最終影片已儲存為: {output_path}")
        return True
    except ffmpeg.Error as e:
        logger.error(f"❌ FFmpeg 執行時發生錯誤: {e.stderr.decode()}")
        return False
    except Exception as e:
        logger.error(f"❌ 發生未知錯誤: {e}")
        return False

def zh_ai_process_video_thumbnail(img_path: str, prompt: str, model_name: str) -> bool:
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        logger.warning("找不到用来进行中文图像编辑的模型 DASHSCOPE_API_KEY 环境变量。默认使用原始帧")
        return False
    mime_type, _ = mimetypes.guess_type(img_path)
    base64_image = encode_image_to_base64(img_path)
    image_data=f"data:{mime_type};base64,{base64_image}"

    messages = [
        {
            "role": "user",
            "content": [
                {"image": image_data},
                {"text": prompt}
            ]
        }
    ]

    logger.info(f"--- 正在调用 AI 模型 {model_name} 进行封面生成，这可能需要一些时间... ---")

    response = MultiModalConversation.call(
        api_key=api_key,
        model=model_name,
        messages=messages,
        result_format='message',
        stream=False,
        watermark=True,
        negative_prompt=""
    )

    if response.status_code == 200:
        # 解析 DashScope 的回傳結果
        content = response.output.choices[0].message.content
        image_url = content[0]['image']

        # 下載圖片
        if download_image(image_url, img_path):
            logger.info(f"🎉 封面改造成功，保存在: {img_path}")
            return True
        else:
            return False  # 下載失敗
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
    content_list.append({
        "type": "image_url",
        "image_url": {
            "url": f"data:image/png;base64,{base64_image}"
        }
    })

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    logger.info(f"--- 正在调用 AI 模型 {model_name} 进行封面生成，这可能需要一些时间... ---")

    try:

        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": content_list
                }
            ],
            # 对于图像生成任务，可能需要更高的 token 上限
            max_tokens=4096
        )

        response_data = completion.model_dump()

        image_url_string = response_data.get('choices', [{}])[0] \
            .get('message', {}) \
            .get('images', [{}])[0] \
            .get('image_url', {}) \
            .get('url')

        if image_url_string and image_url_string.startswith('data:image/png;base64,'):
            # Strip the prefix to get the pure Base64 data
            base64_data = image_url_string.replace('data:image/png;base64,', '')

            logger.debug("✅ 成功定位到 Base64 data. 正在保存...")
            image_data = base64.b64decode(base64_data)

            with open(img_path, 'wb') as f:
                f.write(image_data)

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

        # --- 步驟 2: 提取關鍵幀 ---
        extract_frame_at_timestamp(video_path, timestamp, keyframe_path)

        if not os.path.exists(keyframe_path):
            logger.error(f"關鍵幀提取失敗，無法找到檔案：{keyframe_path}。返回原始影片路徑。")
            return video_path

        # --- 步驟 3: 檢查標題，決定是否需要呼叫 AI ---
        if not title:
            logger.info("標題為空，無需 AI 處理。準備直接使用提取的關鍵幀作為封面。")
            ai_processed_cover_path = keyframe_path

        else:
            # --- 步驟 4: 如果有標題，則呼叫 AI 進行封面生成 ---
            logger.info(f"標題為 '{title}'，語言為 '{language}'，準備呼叫 AI 進行封面改造...")

            # 優化後的 Prompt，只傳送一張圖
            prompt_text = f"""
                        你是一位顶尖的封面设计师。请使用我提供的这张图片作为基础，将以下文字标题创意地、清晰地融入画面中，生成一张吸引人的视频封面。
                        要嵌入的标题是: "{title}"
                        """

            ai_process_success = False
            if language.lower() == 'zh':
                ai_process_success = zh_ai_process_video_thumbnail(
                    img_path=keyframe_path,
                    prompt=prompt_text,
                    model_name=tool_config.zh_image_edit_model
                )
            elif language.lower() == 'en':
                # 在 en_ai_process_video_thumbnail 函式內部加入偵錯 print
                ai_process_success = en_ai_process_video_thumbnail(
                    img_path=keyframe_path,
                    prompt=prompt_text,
                    model_name=tool_config.en_image_edit_model
                )
            else:
                logger.warning(f"未知的語言類型 '{language}'，將不會呼叫 AI。")

            if ai_process_success:
                logger.info("AI 封面改造成功。")
                ai_processed_cover_path = keyframe_path  # 圖片被原地修改
            else:
                logger.warning("AI 封面改造失敗，將使用原始提取的關鍵幀。")
                ai_processed_cover_path = keyframe_path

        # --- 步驟 5: 將最終的封面（AI改造後或原始的）拼接到影片開頭 ---
        logger.info("準備將最終封面合成到影片...")
        file_root, file_ext = os.path.splitext(video_path)
        new_video_path = f"{file_root}_ai{file_ext}"

        add_cover_success = add_cover_to_video(ai_processed_cover_path, video_path, new_video_path)

        if add_cover_success:
            logger.info(f"影片合成成功，返回新影片路徑: {new_video_path}")
            return new_video_path
        else:
            logger.error("影片合成失敗，返回原始影片路徑。")
            return video_path

    yield FunctionInfo.from_fn(
        _video_thumbnail_generation,
        description=("这是视频封面生成和改造工具，返回新生成的视频路径（如果处理失败，则返回原路径）"
                     "该工具需要输入视频路径信息、封面所在的时间戳，以及需要在封面上添加的文字信息和文字语言类型（可选）"))