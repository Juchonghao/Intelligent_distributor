import os
import json
import asyncio
import logging
import datetime
from pydantic import ConfigDict

from nat.builder.builder import Builder
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.function import FunctionBaseConfig

from playwright.async_api import async_playwright

# [Final Correction] Using flat imports and removing the non-working 'login' import
from bilibili_api import Credential, sync, video
from bilibili_api import video_uploader  # 新增导入


logger = logging.getLogger(__name__)
COOKIE_FILE = ".data/bilibili_cookies.json"

# --- Config Classes (Unchanged) ---
class BilibiliBaseConfig(FunctionBaseConfig):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    cookie_path: str = COOKIE_FILE

class BilibiliLoginConfig(BilibiliBaseConfig, name="bilibili_login"):
    pass

class BilibiliUploadVideoConfig(BilibiliBaseConfig, name="bilibili_upload_video"):
    pass


# --- Login Function (Reverted to the PROVEN Playwright method) ---
@register_function(config_type=BilibiliLoginConfig)
async def bilibili_login(tool_config: BilibiliLoginConfig, builder: Builder):
    async def _bilibili_login(dummy: str = "start") -> bool:
        playwright = None
        browser = None
        try:
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            page.set_default_timeout(180000)

            logger.info("🌐 Loading Bilibili login page...")
            await page.goto("https://passport.bilibili.com/login", wait_until="networkidle")

            logger.info("🔍 Detecting QR code...")
            await page.get_by_role("img", name="Scan me!").wait_for(timeout=60000)

            logger.info("🖼️ QR code visible. Please scan with the Bilibili app within 3 minutes.")
            logger.info("⏳ Awaiting scan and confirmation...")
            await page.wait_for_url("https://www.bilibili.com/**", timeout=180000, wait_until="domcontentloaded")
            logger.info("✅ Login successful! Redirected to Bilibili homepage.")

            logger.info("🍪 Fetching and saving credential...")
            await asyncio.sleep(3)

            cookies = await context.cookies()
            required_cookies = {'SESSDATA': None, 'bili_jct': None, 'DedeUserID': None}
            for cookie in cookies:
                if cookie['name'] in required_cookies:
                    required_cookies[cookie['name']] = cookie['value']

            if not all(required_cookies.values()):
                missing = [k for k, v in required_cookies.items() if not v]
                logger.error(f"❌ Critical cookie missing: {missing}. Login may not be fully complete.")
                return False

            os.makedirs(os.path.dirname(tool_config.cookie_path), exist_ok=True)
            with open(tool_config.cookie_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'sessdata': required_cookies['SESSDATA'],
                    'bili_jct': required_cookies['bili_jct'],
                    'dedeuserid': required_cookies['DedeUserID'],
                    'timestamp': datetime.datetime.now().isoformat()
                }, f, indent=2)

            logger.info(f"💾 Credential saved to: {os.path.abspath(tool_config.cookie_path)}")
            logger.info("🎉 Login complete. Browser will close in 5 seconds.")
            await asyncio.sleep(5)
            return True
        except Exception as e:
            logger.error(f"💥 An error occurred during login: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            if 'page' in locals() and not page.is_closed():
                try:
                    await page.screenshot(path="login_error.png")
                    logger.info("Saved screenshot of the error to login_error.png")
                except Exception as screenshot_error:
                    logger.error(f"Failed to take screenshot: {screenshot_error}")
            return False
        finally:
            if browser: await browser.close()
            if playwright: await playwright.stop()
            logger.info("🔌 Browser resources have been cleaned up.")

    yield FunctionInfo.from_fn(_bilibili_login, description="Launches the QR Code login process for a Bilibili account.")


@register_function(config_type=BilibiliUploadVideoConfig)
async def bilibili_upload_video(config: BilibiliUploadVideoConfig, builder: Builder):
    async def _inner(video_path: str, title: str, description: str, tags: list = None) -> str:
        try:
            # ========== 前置检查 ==========
            if not os.path.exists(video_path):
                return f"Error: 视频文件不存在 {video_path}"
            if not os.path.exists(config.cookie_path):
                return "Error: Cookie文件不存在"

            # 验证文件格式和大小
            if not video_path.lower().endswith(('.mp4', '.flv')):
                return "Error: 仅支持MP4/FLV格式"
            if os.path.getsize(video_path) > 2 * 1024 * 1024 * 1024:  # 2GB
                return "Error: 视频超过大小限制"

            # ========== 凭证加载 ==========
            with open(config.cookie_path, 'r', encoding='utf-8') as f:
                cookie_data = json.load(f)

            credential = Credential(
                sessdata=cookie_data['sessdata'],
                bili_jct=cookie_data['bili_jct'],
                dedeuserid=cookie_data.get('dedeuserid', '')
            )

            # ========== 上传配置 ==========
            # 使用新版VideoMeta和VideoUploaderPage
            meta = video_uploader.VideoMeta(
                tid=17,  # 分区ID（17=单机游戏，根据实际需要修改）
                title=title,
                tags=tags or [],
                desc=description,
                cover="/Users/chonghaoju/Desktop/ecommerce_vlm_flow.png",
                no_reprint=True  # 禁止转载
            )

            page = video_uploader.VideoUploaderPage(
                path=video_path,
                title=title,
                description=description
            )

            # ========== 创建上传器 ==========
            uploader = video_uploader.VideoUploader(
                pages=[page],
                meta=meta,
                credential=credential,
                line=video_uploader.Lines.QN
            )

            # ========== 进度监控 ==========
            @uploader.on("UPLOAD_PROGRESS")
            async def handle_progress(data):
                logger.info(f"上传进度: {data.get('percent', 0):.1%}")

            # ========== 执行上传 ==========
            result = await uploader.start()
            # =============================

            if not result.get('bvid'):
                raise ValueError("上传未返回有效BV号")

            return f"🎉 上传成功! BV号: {result['bvid']}"

        except Exception as e:
            logger.error(f"💥 系统错误: {str(e)}", exc_info=True)
            return f"上传失败: {str(e)}"

    yield FunctionInfo.from_fn(_inner, description="B站视频上传")