import sys
from pathlib import Path
# 添加项目根目录到 Python 路径
sys.path.append(str(Path(__file__).resolve().parent.parent))

import flet as ft

from src.endpoints import EndPoints
from src.views.navigation_view import NavigationView
from src.views.main_view import MainView
from src.views.chat_view import ChatView
from src.views.settings_view import SettingsView
from src.components.chat_input import ChatInput
from src.cores.lc_agents import LCAgents
from src.utils.config import ConfigUtils, ProfileUtils
from src.utils.cache import CacheUtils
from src.utils.data import FileDataUtils
from src.utils.i18n import LanguageUtils
from src.utils.logging import logger

# 记录软件运行时的根目录
EndPoints.runtime["app_path_root"] = str(Path(__file__).resolve().parent.parent)

def main(page: ft.Page):
    """
    Flet 主函数
    """
    # 绑定 page 对象
    EndPoints.root["page"] = page
    # 绑定绑定键盘事件
    page.on_keyboard_event = listen_keyboard
    # Page 全局
    page.padding = 0
    page.spacing = 0
    # 初始化工具组件
    EndPoints.runtime["app_util_conf"] = ConfigUtils()
    EndPoints.runtime["app_util_cache"] = CacheUtils()
    EndPoints.runtime["app_util_profile"] = ProfileUtils()
    EndPoints.runtime["app_util_filedata"] = FileDataUtils()
    EndPoints.runtime["app_util_lang"] = LanguageUtils()
    # 初始化相关视图组件
    main_view = MainView()
    navigation_view = NavigationView()
    chat_view = ChatView()
    settings_view = SettingsView()
    # 记录各个 view 实例对象, 未来用此来在各组件之间相互调用
    EndPoints.views["main_view"] = main_view
    EndPoints.views["chat_view"] = chat_view
    EndPoints.views["navigation_view"] = navigation_view
    EndPoints.views["settings_view"] = settings_view
    # 加载智能体
    EndPoints.runtime["lc_agents"] = LCAgents()
    # # 预热 MCP 工具 (临时测试): 提前把联网工具取回来
    # # -> 否则冷启动后的第一次发送要先等一次网络往返
    # # -> 注意: 必须走 page.run_task 投到 event loop 上, 不能在这里直接 await/run
    # page.run_task(EndPoints.runtime["lc_agents"].mcp_tools_load)

    page.add(
        ft.Column(
            controls = [
                # 顶部分割线
                ft.Divider(height=1),
                # 主视图区域
                ft.Row(
                    controls=[
                        # 导航栏
                        navigation_view.navigation,
                        # 分割线
                        ft.VerticalDivider(width=1),
                        # 主视图
                        main_view.main_view
                    ],
                    spacing=0,
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        )
    )

    page.update()
    logger.trace(f"App started successfully.")

def listen_keyboard(e: ft.KeyboardEvent):
    """
    监听键盘事件的处理函数

    Note:
    https://flet.dev/docs/types/keyboardevent
    """
    # Chat 界面发送消息
    # Shift + Enter 且当前 session_id_chat_current 不能为 None
    if e.shift and e.key == "Enter" and EndPoints.runtime["session_id_chat_current"] is not None:
        logger.debug(f"[Send Keyboard] Current session_id_chat is: {EndPoints.runtime["session_id_chat_current"]}")
        send_btn = EndPoints.chat["chat_input_send_icon"].current
        if send_btn is not None and send_btn.icon == ft.Icons.SEND:
            ChatInput.callback_send_user_msg()
        else:
            logger.debug("[Send Keyboard] Send icon is Stop. Ignore this click...")
    # Chat 界面剪切板
    # Ctrl + V 且当前 session_id_chat_current 不能为 None
    elif e.ctrl and e.key == "V" and EndPoints.runtime["session_id_chat_current"] is not None:
        # 异步执行 (获取剪贴板里的图片内容)
        # https://docs.flet.dev/services/clipboard/?h=clipboard
        session_id = EndPoints.runtime["session_id_chat_current"]
        e.page.run_task(listen_clipboard, session_id)

async def listen_clipboard(session_id: str):
    """
    监听剪贴板图片的处理函数
    
    Note:
    目前只支持图片
    """
    image_data = await ft.Clipboard().get_image()
    # 如果数据非空, 则添加一个图片
    if image_data is not None:
        EndPoints.runtime["app_util_cache"].clipboard_image_add(session_prefix=session_id, image_data=image_data)
        ChatInput.refresh_input_attachments()

if __name__ == "__main__":
    ft.run(main)