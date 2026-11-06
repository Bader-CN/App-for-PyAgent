import os
import sys
from pathlib import Path

import flet as ft

# 导入说明: flet build 以 [tool.flet.app].path = "src" 把 src/ 目录作为应用根打包,
# bundle 里 main.py 与 views/ components/ cores/ utils/ locales/ 同级、不存在 src 包,
# 因此全项目统一使用裸模块导入 `from xxx import ...` (dev 下 flet run 也会把 src/ 放进 sys.path)
from endpoints import EndPoints
from views.navigation_view import NavigationView
from views.main_view import MainView
from views.chat_view import ChatView
from views.settings_view import SettingsView
from components.chat_input import ChatInput
from components.common import InputCommon
from cores.lc_agents import LCAgents
from utils.config import ConfigUtils, ProfileUtils
from utils.cache import CacheUtils
from utils.data import FileDataUtils
from utils.i18n import LanguageUtils
from utils.logging import logger, setup_file_logging, install_exception_hooks

# 记录软件运行时的根目录
# 注意: 语义已变更 —— 现在是 main.py 所在目录 (dev = <repo>/src, 打包后 = bundle 根),
# 只用于定位 **只读资源** (如 locales/), 不再指向仓库根
EndPoints.runtime["app_path_root"] = str(Path(__file__).resolve().parent)

# 可写数据目录: 打包后的 bundle 应视为只读, 可写文件一律放 Flet 注入的存储目录
# https://flet.dev/docs/cookbook/read-and-write-files
# (flet run 与桌面端生产模式都会设置这两个环境变量, 前者指向 src/.flet/storage/*,
#  后者指向系统应用支持目录)
# 环境变量缺失时 (直接 python src/main.py 运行) 回退到仓库根 storage/*
_path_root = Path(EndPoints.runtime["app_path_root"])
EndPoints.runtime["app_path_data"] = os.environ.get("FLET_APP_STORAGE_DATA") or str(_path_root.parent / "storage" / "data")
EndPoints.runtime["app_path_temp"] = os.environ.get("FLET_APP_STORAGE_TEMP") or str(_path_root.parent / "storage" / "temp")

# 文件日志: 打包后 bundle 只读, 日志统一写可写数据目录 (<app_path_data>/logs/app.log)
# -> 文件 sink 用 DEBUG (事后排查), stderr sink 仍为 TRACE (dev 终端)
# -> 打包版 stderr 被 Flet 接到缓存目录的 console.log (下次启动覆盖 / 系统可能清理), 不适合查历史
EndPoints.runtime["app_path_log"] = setup_file_logging(os.path.join(EndPoints.runtime["app_path_data"], "logs"))
# 未捕获异常 (sys / threading) 同样落文件, 必须在 ft.run 之前挂好
install_exception_hooks()

def main(page: ft.Page):
    """
    Flet 主函数
    """
    logger.info(f"application starting...")
    # 启动摘要: 打包版可从 console.log 反查真实的日志文件位置
    logger.info(
        f"runtime paths | python={sys.version.split()[0]} | root={EndPoints.runtime['app_path_root']} | "
        f"data={EndPoints.runtime['app_path_data']} | log={EndPoints.runtime['app_path_log']}"
    )
    # Page 对象
    EndPoints.root["page"] = page
    # 初始化工具组件
    EndPoints.runtime["app_util_conf"] = ConfigUtils()
    EndPoints.runtime["app_util_cache"] = CacheUtils()
    EndPoints.runtime["app_util_profile"] = ProfileUtils()
    EndPoints.runtime["app_util_filedata"] = FileDataUtils()
    EndPoints.runtime["app_util_lang"] = LanguageUtils()
    # Page 全局设置
    app_theme = ft.Theme(font_family=EndPoints.runtime["app_util_profile"].font_family_global())
    page.on_keyboard_event = listen_keyboard    # 绑定绑定键盘事件
    page.padding = 0
    page.spacing = 0
    page.theme = app_theme
    page.dark_theme = app_theme
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
                        main_view.main_view,
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
    logger.success(f"application has started successfully.")

def listen_keyboard(e: ft.KeyboardEvent):
    """
    监听键盘事件的处理函数

    Note:
    https://flet.dev/docs/types/keyboardevent
    """
    # 情况1: Chat 界面 & 发送消息 (Shift + Enter & session_id_chat_current 不能为 None)
    if e.shift and e.key == "Enter" and EndPoints.runtime["session_id_chat_current"] is not None:
        send_btn = EndPoints.input["input_send_btn"].current
        # 仅在发送按钮存在 & 图标处于可发送时才会触发
        if send_btn is None:
            # 区分「ref 失效 (切页重建中)」与「图标停在 STOP (上一轮异常分叉)」
            # -> 两者对用户都是「快捷键没反应」, 但排查方向完全不同
            logger.warning("input_send_btn not available, ignore this keyboard send.")
        elif send_btn.icon == ft.Icons.SEND:
            ChatInput.callback_send_user_msg()
        else:
            logger.warning(f"send icon is not SEND ({send_btn.icon}), ignore this keyboard send.")

    # 情况2: Chat 界面 & 剪切板 (Ctrl + V & session_id_chat_current 不能为 None)
    elif e.ctrl and e.key == "V" and EndPoints.runtime["session_id_chat_current"] is not None:
        # 异步执行 (获取剪贴板里的图片内容)
        # https://docs.flet.dev/services/clipboard/?h=clipboard
        session_id = EndPoints.runtime["session_id_chat_current"]
        e.page.run_task(listen_clipboard, session_id)

async def listen_clipboard(session_id: str):
    """
    监听剪贴板图片的处理函数
    https://flet.dev/docs/services/clipboard
    
    Note:
    目前只支持图片
    """
    image_data = await ft.Clipboard().get_image()
    # 如果数据非空, 则添加一个图片
    if image_data is not None:
        EndPoints.runtime["app_util_cache"].clipboard_image_add(session_prefix=session_id, image_data=image_data)
        InputCommon.refresh_input_attachments()

if __name__ == "__main__":
    ft.run(main)