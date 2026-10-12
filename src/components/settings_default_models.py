import flet as ft

from typing import Dict

from src.endpoints import EndPoints
from src.components.common import AlertCommon
from src.utils.logging import logger


class SettingsDefaultModels:
    """
    默认模型
    """
    # 类变量
    popup_width = 300
    popup_height = 32
    min_width = 300
    max_width = 300
    @classmethod
    def build_blk_default_chat_model(cls):
        """
        默认聊天模型
        """
        blk_chat_model = ft.Container(
            ft.Column(
                controls=[
                    ft.Text(
                        value=EndPoints.runtime["app_util_lang"].translate(key="default_chat_model"),
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.PopupMenuButton(
                        # 关闭鼠标悬浮时显示的默认值: "Show menu"
                        # https://flet.dev/docs/controls/control
                        tooltip="",
                        content=ft.Container(
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        value=EndPoints.runtime["app_util_profile"].default_model(default_type="chat_model"),
                                        ref=EndPoints.settings["default_chat_model"],
                                    ),
                                    ft.Container(expand=True),
                                    ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, size=16),
                                ],
                            ),
                            width=cls.popup_width,
                            height=cls.popup_height,
                            border=ft.Border.all(1),
                            border_radius=5,
                            padding=ft.Padding.symmetric(horizontal=5),
                        ),
                        items=[
                            ft.PopupMenuItem(
                                content=i, 
                                height=cls.popup_height,
                                on_click=cls.callback_default_model_set,
                                data={"default_type": "chat_model", "default_model": i},
                            )
                            for i in EndPoints.runtime["app_util_conf"].models_list_enable()
                        ],
                        menu_position=ft.PopupMenuPosition.UNDER,
                        # https://flet.dev/docs/controls/popupmenubutton/#flet.PopupMenuButton.size_constraints
                        size_constraints=ft.BoxConstraints(min_width=cls.min_width, max_width=cls.max_width),
                    ),
                    ft.Text(
                        value=EndPoints.runtime["app_util_lang"].translate(key="default_chat_model_desc"),
                        size=12,
                        color=ft.Colors.GREY_700,
                    ),
                ],
            ),
        )
        return blk_chat_model
    
    @classmethod
    def build_blk_default_agent_model(cls):
        """
        默认主智能体设置块
        """
        blk_default_agent = ft.Container(
            ft.Column(
                controls=[
                    ft.Text(
                        value=EndPoints.runtime["app_util_lang"].translate(key="default_agent_model"),
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.PopupMenuButton(
                        # 关闭鼠标悬浮时显示的默认值: "Show menu"
                        # https://flet.dev/docs/controls/control
                        tooltip="",
                        content=ft.Container(
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        value=EndPoints.runtime["app_util_profile"].default_model(default_type="agent_model"),
                                        ref=EndPoints.settings["default_agent_model"],
                                    ),
                                    ft.Container(expand=True),
                                    ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, size=16),
                                ],
                            ),
                            width=cls.popup_width,
                            height=cls.popup_height,
                            border=ft.Border.all(1),
                            border_radius=5,
                            padding=ft.Padding.symmetric(horizontal=5),
                        ),
                        items=[
                            ft.PopupMenuItem(
                                content=i, 
                                height=cls.popup_height,
                                on_click=cls.callback_default_model_set,
                                data={"default_type": "agent_model", "default_model": i},
                            )
                            for i in EndPoints.runtime["app_util_conf"].models_list_enable()
                        ],
                        menu_position=ft.PopupMenuPosition.UNDER,
                        # https://flet.dev/docs/controls/popupmenubutton/#flet.PopupMenuButton.size_constraints
                        size_constraints=ft.BoxConstraints(min_width=cls.min_width, max_width=cls.max_width),
                    ),
                    ft.Text(
                        value=EndPoints.runtime["app_util_lang"].translate(key="default_agent_model_desc"),
                        size=12,
                        color=ft.Colors.GREY_700,
                    ),
                ],
            ),
        )
        return blk_default_agent

    @classmethod
    def build_blk_default_summary_model(cls):
        """
        默认总结模型设置块
        """
        blk_summary_agent = ft.Container(
            ft.Column(
                controls=[
                    ft.Text(
                        value=EndPoints.runtime["app_util_lang"].translate(key="default_summary_model"),
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.PopupMenuButton(
                        # 关闭鼠标悬浮时显示的默认值: "Show menu"
                        # https://flet.dev/docs/controls/control
                        tooltip="",
                        content=ft.Container(
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        value=EndPoints.runtime["app_util_profile"].default_model(default_type="summary_model"),
                                        ref=EndPoints.settings["default_summary_model"],
                                    ),
                                    ft.Container(expand=True),
                                    ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, size=16),
                                ],
                            ),
                            width=cls.popup_width,
                            height=cls.popup_height,
                            border=ft.Border.all(1),
                            border_radius=5,
                            padding=ft.Padding.symmetric(horizontal=5),
                        ),
                        items=[
                            ft.PopupMenuItem(
                                content=i, 
                                height=cls.popup_height,
                                on_click=cls.callback_default_model_set,
                                data={"default_type": "summary_model", "default_model": i},
                            )
                            for i in EndPoints.runtime["app_util_conf"].models_list_enable()
                        ],
                        menu_position=ft.PopupMenuPosition.UNDER,
                        # https://flet.dev/docs/controls/popupmenubutton/#flet.PopupMenuButton.size_constraints
                        size_constraints=ft.BoxConstraints(min_width=cls.min_width, max_width=cls.max_width),
                    ),
                    ft.Text(
                        value=EndPoints.runtime["app_util_lang"].translate(key="default_summary_model_desc"),
                        size=12,
                        color=ft.Colors.GREY_700,
                    ),
                ],
            ),
        )
        return blk_summary_agent

    @classmethod
    def build_blk_default_translation_model(cls):
        """
        默认翻译模型设置块
        """
        blk_translation_agent = ft.Container(
            ft.Column(
                controls=[
                    ft.Text(
                        value=EndPoints.runtime["app_util_lang"].translate(key="default_translation_model"),
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.PopupMenuButton(
                        # 关闭鼠标悬浮时显示的默认值: "Show menu"
                        # https://flet.dev/docs/controls/control
                        tooltip="",
                        content=ft.Container(
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        value=EndPoints.runtime["app_util_profile"].default_model(default_type="translation_model"),
                                        ref=EndPoints.settings["default_translation_model"],
                                    ),
                                    ft.Container(expand=True),
                                    ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, size=16),
                                ],
                            ),
                            width=cls.popup_width,
                            height=cls.popup_height,
                            border=ft.Border.all(1),
                            border_radius=5,
                            padding=ft.Padding.symmetric(horizontal=5),
                        ),
                        items=[
                            ft.PopupMenuItem(
                                content=i, 
                                height=cls.popup_height,
                                on_click=cls.callback_default_model_set,
                                data={"default_type": "translation_model", "default_model": i},
                            )
                            for i in EndPoints.runtime["app_util_conf"].models_list_enable()
                        ],
                        menu_position=ft.PopupMenuPosition.UNDER,
                        # https://flet.dev/docs/controls/popupmenubutton/#flet.PopupMenuButton.size_constraints
                        size_constraints=ft.BoxConstraints(min_width=cls.min_width, max_width=cls.max_width),
                    ),
                    ft.Text(
                    value=EndPoints.runtime["app_util_lang"].translate(key="default_translation_model_desc"),
                    size=12,
                    color=ft.Colors.GREY_700,
                ),
                ],
            ),
        )
        return blk_translation_agent

    @classmethod
    def callback_default_model_set(cls, e):
        """
        基于控件的 data 来设置默认模型
        """
        # 获取数据
        default_type = e.control.data.get("default_type")
        default_model = e.control.data.get("default_model")
        # 保存数据
        EndPoints.runtime["app_util_profile"].default_model_set(default_type=default_type, default_model=default_model)

        # 聊天模型
        if default_type == "chat_model":
            EndPoints.settings["default_chat_model"].current.value = default_model
            err_msg = EndPoints.runtime["lc_agents"].agent_chat_update()
            # 加载错误时的处理
            if err_msg:
                AlertCommon.alert_model_config_error(message=err_msg)
                # 抹掉配置 & UI
                logger.error(f"Found invalid model configuration, reason is: {err_msg}")
                EndPoints.runtime["app_util_profile"].default_model_set(default_type=default_type, default_model=None)
                EndPoints.settings["default_chat_model"].current.value = None
                EndPoints.root["page"].update()
        # 主智能体
        elif default_type == "agent_model":
            EndPoints.settings["default_agent_model"].current.value = default_model
        # 总结模型
        elif default_type == "summary_model":
            EndPoints.settings["default_summary_model"].current.value = default_model
        # 翻译模型
        elif default_type == "translation_model":
            EndPoints.settings["default_translation_model"].current.value = default_model