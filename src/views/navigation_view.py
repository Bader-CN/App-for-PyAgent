import flet as ft

from src.endpoints import EndPoints
from src.components.chat_list import ChatList
from src.utils.logging import logger


class NavigationView:
    """
    视图 - 导航栏
    用于实现导航栏的相关功能, 包括按钮点击事件等
    """
    def __init__(self):
        # 记录上一次点击的导航栏按钮
        self.last_selected_button = None

        # 导航栏按钮
        self.chat = ft.Container(content = ft.IconButton(
            ft.Icons.CHAT, tooltip=EndPoints.runtime["app_util_lang"].translate(key="chat"), 
            on_click=self.render_main_view,
            data={"i18n_key": "chat", "selected_tag": "chat"},
        ))
        self.docs = ft.Container(content = ft.IconButton(
            ft.Icons.SNIPPET_FOLDER, tooltip=EndPoints.runtime["app_util_lang"].translate(key="docs"),
            on_click=self.render_main_view,
            data={"i18n_key": "docs", "selected_tag": "docs"},
        ))
        self.settings = ft.Container(content = ft.IconButton(
            ft.Icons.SETTINGS, tooltip=EndPoints.runtime["app_util_lang"].translate(key="settings"), 
            on_click=self.render_main_view,
            data={"i18n_key": "settings", "selected_tag": "settings"},
        ))

        # 导航栏对象
        self.navigation = ft.Container(
            content = ft.Column(
                controls=[
                    self.chat, 
                    self.docs, 
                    ft.Container(expand=True), 
                    self.settings
                ],
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=40,
            bgcolor="#E8E8E8",
            ref=EndPoints.root["navigation"],
        )

    def render_main_view(self, e: ft.ControlEvent):
        """
        基于 ft.ControlEvent 所携带的 data 来渲染主视图
        """
        selected_tag = e.control.data.get("selected_tag")
        if self.last_selected_button != selected_tag:
            self.last_selected_button = selected_tag
            # 抹除主视图中的内容
            if EndPoints.root["main_view"].current.content is not None:
                EndPoints.root["main_view"].current.content = None
                logger.debug("main_view container content have been cleared.")
                
            # 基于 selected_tag 来调用对应的渲染组件
            if selected_tag == "chat":
                # 将 "对话界面" 渲染在 "主界面" 上 & 渲染对话界面
                EndPoints.root["main_view"].current.content = EndPoints.chat["chat_view"].current
                EndPoints.views["chat_view"].render_full()
                # 基于实际情况来决定如何渲染会话内容
                if len(EndPoints.chat["chat_list"].current.controls) == 0:
                    ChatList.callback_session_add()
                    ChatList.callback_session_msgs_render()
                if EndPoints.runtime["session_id_chat_last"] is None:
                    ChatList.callback_session_msgs_render()
                else:
                    session_id_chat_last = EndPoints.runtime["session_id_chat_last"]
                    controls = EndPoints.chat["chat_list"].current.controls
                    for control in controls:
                        if control.data.get("session_id") == session_id_chat_last:
                            ChatList.callback_session_msgs_render(session_id=session_id_chat_last, title=control.data.get("title"))
                            break
            elif selected_tag == "docs":
                # 清除 "对话ID" 的标记位
                EndPoints.runtime["session_id_chat_current"] = None
                EndPoints.runtime["session_id_agent_current"] = None
            elif selected_tag == "settings":
                # 清除 "对话ID" 的标记位
                EndPoints.runtime["session_id_chat_current"] = None
                EndPoints.runtime["session_id_agent_current"] = None
                # 将 "设置界面" 渲染在 "主界面" 上 & 渲染设置界面
                EndPoints.root["main_view"].current.content = EndPoints.settings["settings_view"].current
                EndPoints.views["settings_view"].render_full()