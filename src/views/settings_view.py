import flet as ft

from src.endpoints import EndPoints
from src.components.settings_general import SettingsGeneral
from src.components.settings_default_models import SettingsDefaultModels
from src.components.settings_model_services import SettingsModelServices
from src.utils.logging import logger


class SettingsView:
    """
    视图 - 设置视图
    """
    def __init__(self):
        # 记录最后一次点击的是什么
        self.last_selected_tag = None
        # 设置视图基础布局
        self.lv1_view = ft.Container(ref=EndPoints.settings["lv1_view"])
        self.lv2_view = ft.Container(ref=EndPoints.settings["lv2_view"])
        self.lv3_view = ft.Container(ref=EndPoints.settings["lv3_view"])
        # 设置视图核心布局
        self.settings_view = ft.Row(
            controls=[
                self.lv1_view,
                ft.VerticalDivider(width=1),
                self.lv2_view,
            ],
            expand=True,
            spacing=0,
            ref=EndPoints.settings["settings_view"],
        )
        # 按钮: 常规设置
        self.btn_general_settings = ft.Button(
            content=EndPoints.runtime["app_util_lang"].translate(key="general_settings"),
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
            data={"i18n_key": "general_settings", "selected_tag": "general_settings"},
            on_click=self.render_lv2,
        )
        # 按钮: 默认模型
        self.btn_default_models = ft.Button(
            content=EndPoints.runtime["app_util_lang"].translate(key="default_models"),
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
            data={"i18n_key": "default_models", "selected_tag": "default_models"},
            on_click=self.render_lv2,
        )
        # 按钮: 模型服务
        self.btn_model_provider = ft.Button(
            content=EndPoints.runtime["app_util_lang"].translate(key="model_provider"),
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
            data={"i18n_key": "model_provider", "selected_tag": "model_provider"},
            on_click=self.render_lv2,
        )
        # 子组件: 通用设置部分
        # 在这里创建主要是为了解决 Python 弱引用问题可能会导致对象被回收, 进而在调用时会出现 None 的问题
        self.blk_i18n = SettingsGeneral.build_blk_i18n()                                        # 国际化
        self.blk_switch_language = SettingsGeneral.build_blk_language_switch()                  # 语言
        self.blk_font = SettingsGeneral.build_blk_font_family()                                 # 字体
        self.blk_font_global = SettingsGeneral.build_blk_font_family_switch(font_type="global") # 全局字体
        self.blk_font_text = SettingsGeneral.build_blk_font_family_switch(font_type="text")     # 全局字体
        self.blk_font_code = SettingsGeneral.build_blk_font_family_switch(font_type="code")     # 全局字体
        # 子组件: 默认服务部分
        # 在这里创建主要是为了解决 Python 弱引用问题可能会导致对象被回收, 进而在调用时会出现 None 的问题
        self.blk_models = None # 模型列表

    def render_full(self):
        """
        完整渲染设置界面, 通常用于首次刷新
        """
        self.render_lv1()
        self.render_lv2()
        logger.debug("rendering settings_view completed.")

    def render_lv1(self):
        """
        渲染设置页面的 lv1 层级视图
        """
        # 调整布局
        self.lv1_view.margin = 10   # 外边距
        self.lv1_view.width = 160
        # 添加组件
        self.lv1_view.content = ft.Column(
            controls = [
                self.btn_general_settings,
                self.btn_default_models,
                self.btn_model_provider,
            ],
            # Stretch: 拉伸至等宽
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        logger.debug("complete rendering of lv1 settings_view.")

    def render_lv2(self, e: ft.ControlEvent | None = None):
        """
        渲染设置页面的 lv2 层级视图

        Args:
        - e (ft.ControlEvent): 事件对象
        """
        # 重复点击: e 非空 & e.control.data.get("selected_tag") == last_selected_tag
        if e is not None and e.control.data.get("selected_tag") == self.last_selected_tag:
            logger.debug(f"duplicate click, ignore rendering of lv2 settings_view {self.last_selected_tag}.")
            return
        # e 非空: e.control.data.get("selected_tag")
        # e 为空: "general_settings"
        selected_tag = e.control.data.get("selected_tag") if e is not None else "general_settings"
        self.render_lv2_content(selected_tag)
        # 更新标记位
        self.last_selected_tag = selected_tag

    def render_lv2_content(self, selected_tag: str):
        """
        根据 selected_tag 渲染 lv2 内容
        """
        # 尝试清空 Lv3 视图
        self.settings_view.controls = self.settings_view.controls[:3]

        # 常规设置
        if selected_tag == "general_settings":
            self.lv2_view.margin = 10
            self.lv2_view.width = None
            self.lv2_view.expand = True
            self.lv2_view.content = ft.Column(
                controls=[
                    # 国际化
                    ft.Container(
                        ft.Column(
                            controls=[
                                self.blk_i18n,
                                ft.Divider(height=1),
                                self.blk_switch_language,
                            ],
                        ),
                        # bgcolor=ft.Colors.GREY_100,
                        border=ft.Border.all(color=ft.Colors.GREY_400),
                        border_radius=5,
                        padding=ft.Padding.symmetric(vertical=5, horizontal=10),
                    ),
                    # 字体
                    ft.Container(
                        ft.Column(
                            controls=[
                                self.blk_font,
                                ft.Divider(height=1),
                                self.blk_font_global,
                                ft.Divider(height=1),
                                self.blk_font_text,
                                ft.Divider(height=1),
                                self.blk_font_code,
                            ],
                        ),
                        border=ft.Border.all(color=ft.Colors.GREY_400),
                        border_radius=5,
                        padding=ft.Padding.symmetric(vertical=5, horizontal=10),
                    ),
                ],
            )

        # 默认模型
        elif selected_tag == "default_models":
            self.lv2_view.margin = 10
            self.lv2_view.width = None
            self.lv2_view.expand = True
            self.lv2_view.content = ft.Column(
                controls=[
                    SettingsDefaultModels.build_blk_default_chat_model(),
                    ft.Divider(height=1),
                    SettingsDefaultModels.build_blk_default_agent_model(),
                    ft.Divider(height=1),
                    SettingsDefaultModels.build_blk_default_summary_model(),
                    ft.Divider(height=1),
                    SettingsDefaultModels.build_blk_default_translation_model(),
                ],
            )

        # 模型服务
        elif selected_tag == "model_provider":
            self.lv2_view.margin = 10
            self.lv2_view.width = 200
            self.lv2_view.expand = False
            self.lv2_view.content = ft.Column(
                controls=[
                    SettingsModelServices.build_blk_provider_btn_add(),
                    SettingsModelServices.build_blk_providers_list(),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            )
            self.render_lv3(selected_tag=selected_tag)

        logger.debug(f"complete rendering of lv2 settings_view with {selected_tag}.")

    def render_lv3(self, selected_tag: str):
        """
        渲染设置页面的 lv3 层级视图
        """
        # Lv3 基础布局
        self.lv3_view.margin = 10
        self.lv3_view.expand = True
        # 将 Lv3 视图添加进 self.settings_view, 类型为 ft.Row
        if selected_tag == "model_provider":
            # 重新渲染 self.lv3_view, 保证语言切换正常
            provider_name = EndPoints.runtime["last_provider_name"]
            if provider_name is not None:
                SettingsModelServices.callback_provider_details_render(provider_name=provider_name)
            self.settings_view.controls.extend([
                ft.VerticalDivider(width=1), 
                self.lv3_view,
            ])
            logger.debug("complete rendering of lv3 settings_view with model_provider.")