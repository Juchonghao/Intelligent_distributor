import os
import json
import time
import logging
import asyncio

from nat.builder.builder import Builder
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.function import FunctionBaseConfig

from playwright.async_api import async_playwright, Page, expect, Playwright, Browser
from pydantic import BaseModel, ConfigDict
logger = logging.getLogger(__name__)


class XiaoHongShuBaseConfig(FunctionBaseConfig):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    creator_platform_url: str = "https://creator.xiaohongshu.com"
    cookie_path:str = ".data/cookies.json"

    playwright: Playwright = None
    browser:Browser = None

    async def launch_browser(self, headless=False):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=headless, args=['--start-maximized'])

    async def close_browser(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("浏览器已关闭。")

class XiaoHongShuLoginConfig(XiaoHongShuBaseConfig, name="xiaohongshu_login"):
    pass

class XiaoHongShuCheckLoginStatusConfig(XiaoHongShuBaseConfig, name="xiaohongshu_check_login_status"):
    pass

class XiaoHongShuUploadVideoConfig(XiaoHongShuBaseConfig, name="xiaohongshu_upload_video"):
    pass

@register_function(config_type=XiaoHongShuLoginConfig)
async def xiaohongshu_login(tool_config: XiaoHongShuLoginConfig, builder: Builder):

    async def _xiaohongshu_login(dummy: str = None) -> bool:
        # 确保dummy参数有一个默认值，即使传入None也能工作
        dummy = dummy or ""
        if os.path.exists(tool_config.cookie_path):
            logger.info(f"提示：旧的 Cookie 文件 '{tool_config.cookie_path}' 已存在，将会被覆盖。")

        await tool_config.launch_browser(headless=False)
        context = await tool_config.browser.new_context(no_viewport=True)
        page = await context.new_page()

        try:
            logger.info("正在打开小红书登录页面，请手动扫码登录...")
            await page.goto(f"{tool_config.creator_platform_url}/login")
            logger.info("请在 3 分钟内完成扫码...")
            logger.info("扫码后请等待页面自动跳转，不要手动关闭浏览器...")
            
            # 增加超时时间，给用户更多时间扫码
            try:
                await page.wait_for_url(f"{tool_config.creator_platform_url}/new/home", timeout=180000)  # 3分钟
                logger.info("检测到页面跳转，登录成功！")
                
                # 登录成功后，等待一段时间确保所有cookie都已设置
                await asyncio.sleep(3)
                
                cookies = await context.cookies()
                os.makedirs(os.path.dirname(tool_config.cookie_path), exist_ok=True)  # 确保目录存在
                with open(tool_config.cookie_path, 'w', encoding='utf-8') as f:
                    json.dump(cookies, f, ensure_ascii=False, indent=4)
                logger.info(f"Cookie 已成功保存到: {tool_config.cookie_path}")
                
                # 再等待一段时间，让用户看到成功消息
                logger.info("浏览器将在 3 秒后自动关闭...")
                await asyncio.sleep(3)
                return True
            except Exception as e:
                logger.error(f"等待登录超时或发生错误: {e}")
                logger.error("您可能没有在规定时间内完成扫码，或者扫码后页面没有正确跳转。")
                logger.error("请再次尝试登录，或检查网络连接。")
                return False
        except Exception as e:
            logger.error(f"登录过程中发生错误: {e}")
            # 出错时等待一段时间，让用户看到错误消息
            logger.error("浏览器将在 5 秒后自动关闭...")
            await asyncio.sleep(5)
            return False
        finally:
            await tool_config.close_browser()

    yield FunctionInfo.from_fn(
        _xiaohongshu_login,
        description=("这是结合playwright的小红书登录工具，需要显式手动扫码"
                     "这个工具不需要输入参数，返回1个bool值，表示是否登录成功"))

@register_function(config_type=XiaoHongShuCheckLoginStatusConfig)
async def xiaohongshu_check_login_status(tool_config: XiaoHongShuCheckLoginStatusConfig, builder: Builder):

    async def _xiaohongshu_check_login_status(dummy: str = None) ->bool:
        # 确保dummy参数有一个默认值，即使传入None也能工作
        dummy = dummy or ""
        # 确保cookie路径存在
        cookie_dir = os.path.dirname(tool_config.cookie_path)
        if not os.path.exists(cookie_dir):
            os.makedirs(cookie_dir, exist_ok=True)
            logger.info(f"创建目录: {cookie_dir}")
            
        if not os.path.exists(tool_config.cookie_path) or os.path.getsize(tool_config.cookie_path) == 0:
            logger.info(f"检查完毕：Cookie 文件不存在或为空，需要登录。路径: {tool_config.cookie_path}")
            return False

        # 验证过程使用无头模式，不打扰用户
        try:
            logger.info(f"正在读取Cookie文件: {tool_config.cookie_path}")
            with open(tool_config.cookie_path, 'r', encoding='utf-8') as f:
                cookies_content = f.read()
                logger.info(f"Cookie文件内容长度: {len(cookies_content)} 字节")
                cookies = json.loads(cookies_content)
                logger.info(f"成功解析Cookie，共 {len(cookies)} 项")
                
            await tool_config.launch_browser(headless=True)
            logger.info("浏览器已启动，准备验证Cookie")
            
            context = await tool_config.browser.new_context(storage_state={"cookies": cookies})
            page = await context.new_page()

            logger.info("正在验证 Cookie 有效性...")
            await page.goto(f"{tool_config.creator_platform_url}/creator/home")
            # 等待页面加载，给予一个较短的超时
            await page.wait_for_load_state('domcontentloaded', timeout=15000)

            # 最可靠的判断方式：如果 Cookie 失效，页面会强制跳转到 /login
            logger.info("页面已加载，等待3秒检查URL...")
            await asyncio.sleep(3)  # 等待JS跳转
            final_url = page.url
            logger.info(f"当前页面URL: {final_url}")
            
            if "/login" in final_url:
                logger.info("检查完毕：Cookie 已过期，需要重新登录。")
                return False
            else:
                logger.info("检查完毕：Cookie 有效，处于登录状态。")
                return True
        except Exception as e:
            logger.error(f"验证过程中发生错误: {str(e)}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            logger.error("检查完毕：验证失败，需要重新登录。")
            return False
        finally:
            try:
                if hasattr(tool_config, 'browser') and tool_config.browser:
                    await tool_config.close_browser()
                    logger.info("浏览器已关闭。")
            except Exception as e:
                logger.error(f"关闭浏览器时发生错误: {str(e)}")

    yield FunctionInfo.from_fn(
        _xiaohongshu_check_login_status,
        description=("这是结合playwright的小红书登录状态检查工具"
                     "这个工具不需要输入参数，返回1个bool值，表示是否登录处于登录状态"))

@register_function(config_type=XiaoHongShuUploadVideoConfig)
async def xiaohongshu_upload_video(tool_config: XiaoHongShuUploadVideoConfig, builder: Builder):

    async def _xiaohongshu_upload_video(video_path: str = None, title: str = None, description: str = None, tags: list = None) -> bool:
        # 确保参数有默认值，即使传入None也能工作
        if video_path is None or title is None or description is None:
            print("错误：必须提供视频路径、标题和描述")
            return False
        """
        小红书上传视频
        """
        if not os.path.exists(video_path):
            logger.error(f"错误：视频文件不存在 -> {video_path}")
            return False

        await tool_config.launch_browser(headless=False)

        try:
            with open(tool_config.cookie_path, 'r', encoding='utf-8') as f:
                cookies = json.load(f)

            context = await tool_config.browser.new_context(storage_state={"cookies": cookies}, no_viewport=True)
            page = await context.new_page()

            logger.info("正在使用 Cookie 访问创作者中心发布页面...")
            # 【优化点1】使用更精确的发布页面URL
            await page.goto(f"{tool_config.creator_platform_url}/publish/publish?type=video")

            # --- 开始自动化操作 ---

            # 2. 上传视频文件
            logger.info(f"定位上传入口并上传视频: {os.path.basename(video_path)}...")
            # 【优化点2】直接定位隐藏的 input 元素并设置文件，比模拟点击更稳定
            # 这个选择器 `div[class^='upload-content'] input[type='file']` 能够精准找到上传文件的input控件
            await page.locator("div[class^='upload-content'] input[type='file']").set_input_files(video_path)

            # 3. 等待视频上传和处理完成
            logger.info("视频上传中，请耐心等待... (最长等待5分钟)")
            # 【优化点3】采用更可靠的轮询方式检查上传状态，而不是简单等待某个元素出现
            upload_success_locator = page.locator('div.stage:has-text("上传成功")')
            await expect(upload_success_locator).to_be_visible(timeout=300000)  # 等待"上传成功"的提示出现
            logger.info("视频处理完成！")

            # 4. 填写标题
            logger.debug(f"填写标题: {title}")
            # 【优化点4】使用新的标题输入框选择器
            await page.locator('.title-container input').fill(title)

            # 5. 填写描述和话题
            logger.debug("填写描述和话题标签...")
            # 【优化点5】使用 Quill富文本编辑器的选择器 `.ql-editor`
            editor_locator = page.locator("div.tiptap.ProseMirror")

            # 首先清空可能存在的默认内容
            await editor_locator.click()
            await page.keyboard.press("Control+KeyA")
            await page.keyboard.press("Delete")

            # 填入描述
            await editor_locator.type(description)

            # 填入话题标签
            if tags:
                await page.keyboard.press("Enter")
                await asyncio.sleep(0.5)
                for tag in tags:
                    await editor_locator.press_sequentially(f"#{tag}\n ", delay=200)
                    await asyncio.sleep(1)
                logger.debug(f"已添加 {len(tags)} 个话题。")

            await asyncio.sleep(1)  # 等待一下，确保内容输入稳定

            # 6. 点击发布按钮
            publish_button = page.get_by_role("button", name="发布")
            await expect(publish_button).to_be_enabled(timeout=20000)  # 确保按钮是可点击状态

            logger.debug("点击发布按钮...")
            await asyncio.sleep(2)
            await publish_button.dispatch_event('click')

            # 7. 等待发布成功
            logger.info("正在发布，等待最终确认...")
            # 【优化点6】通过监听URL跳转到成功页面来确认发布成功，这是最可靠的方式
            await expect(page).to_have_url(f"{tool_config.creator_platform_url}/publish/publish?source=&published=true", timeout=60000)
            logger.info("🎉 视频笔记发布成功！URL已跳转至成功页。")
            return True

        except Exception as e:
            logger.error(f"发布过程中发生错误: {e}")
            return False
        finally:
            await tool_config.close_browser()

    yield FunctionInfo.from_fn(
        _xiaohongshu_upload_video,
        description=("这是结合playwright的小红书视频上传工具"
                     "这个工具至少需要输入三个参数："
                     "video_path:str（视频路径），title:str（视频标题），description:str（视频描述）；"
                     "可选参数：tags:list（话题）"
                     "返回1个bool值，表示是否登录处于登录状态"))