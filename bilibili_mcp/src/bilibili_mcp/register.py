import os
import asyncio
import logging
from bilibili_api import video, Credential, sync
from playwright.async_api import async_playwright # [修正] 導入 Playwright
from pydantic import Field, BaseModel, ConfigDict

from nat.builder.builder import Builder
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.function import FunctionBaseConfig

logger = logging.getLogger(__name__)
COOKIE_FILE = ".data/bilibili_cookies.json"

# --- 設定類別 ---
class BilibiliBaseConfig(FunctionBaseConfig):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    cookie_path: str = COOKIE_FILE

class BilibiliLoginConfig(BilibiliBaseConfig, name="bilibili_login"):
    pass

class BilibiliUploadVideoConfig(BilibiliBaseConfig, name="bilibili_upload_video"):
    pass

# --- 工具實現 (使用 Playwright 進行瀏覽器 QR Code 登入) ---
@register_function(config_type=BilibiliLoginConfig)
async def bilibili_login(tool_config: BilibiliLoginConfig, builder: Builder):
    async def _bilibili_login(dummy: str = "start") -> bool:
        playwright = None
        browser = None
        try:
            logger.info("Starting Bilibili login via browser automation...")
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()

            logger.info("Navigating to Bilibili login page. Please scan the QR code in the browser window.")
            await page.goto("https://passport.bilibili.com/login")

            # 等待使用者掃描 QR code 並成功跳轉到 B 站主頁
            logger.info("Waiting for successful login... (Timeout: 3 minutes)")
            await page.wait_for_url("https://www.bilibili.com/", timeout=180000)
            logger.info("Login successful! Capturing session cookies.")

            await asyncio.sleep(3)  # 等待所有 cookies 都被設定好

            cookies = await context.cookies()

            # 從 cookies 中提取 bilibili-api-python 需要的核心憑證資訊
            sessdata = ""
            bili_jct = ""
            dedeuserid = ""

            for cookie in cookies:
                if cookie['name'] == 'SESSDATA':
                    sessdata = cookie['value']
                if cookie['name'] == 'bili_jct':
                    bili_jct = cookie['value']
                if cookie['name'] == 'DedeUserID':
                    dedeuserid = cookie['value']

            if not (sessdata and bili_jct and dedeuserid):
                logger.error("Could not find necessary cookies (SESSDATA, bili_jct, DedeUserID). Login might have failed.")
                return False

            credential = Credential(sessdata=sessdata, bili_jct=bili_jct, dedeuserid=dedeuserid)

            os.makedirs(os.path.dirname(tool_config.cookie_path), exist_ok=True)
            credential.save(tool_config.cookie_path)
            logger.info(f"Bilibili credential saved successfully to {tool_config.cookie_path}")

            logger.info("Browser will close in 3 seconds.")
            await asyncio.sleep(3)
            return True

        except Exception as e:
            logger.error(f"Bilibili login failed with exception: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
        finally:
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()

    yield FunctionInfo.from_fn(_bilibili_login, description="Launches the QR Code login process for a Bilibili account.")

@register_function(config_type=BilibiliUploadVideoConfig)
async def bilibili_upload_video(tool_config: BilibiliUploadVideoConfig, builder: Builder):
    async def _bilibili_upload_video(video_path: str, title: str, description: str, tags: list = None) -> str:
        if not os.path.exists(tool_config.cookie_path):
            return "Error: Bilibili cookie file not found. Please log in first."
        if not os.path.exists(video_path):
            return f"Error: Video file not found at {video_path}"

        try:
            credential = Credential.from_file(tool_config.cookie_path)
            await credential.check_valid()
            logger.info("Bilibili credential loaded and validated.")

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: sync(
                video.upload(
                    credential=credential,
                    path=video_path,
                    title=title,
                    desc=description,
                    tags=tags or [],
                )
            ))

            result_msg = "Video uploaded successfully to Bilibili!"
            logger.info(result_msg)
            return result_msg
        except Exception as e:
            error_msg = f"Failed to upload video to Bilibili: {e}"
            logger.error(error_msg)
            return error_msg

    yield FunctionInfo.from_fn(_bilibili_upload_video, description="Uploads a specified video file to Bilibili.")
