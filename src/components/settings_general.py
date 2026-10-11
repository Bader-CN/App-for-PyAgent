import flet as ft
from src.endpoints import EndPoints
from src.utils.logging import logger


class SettingsGeneral:
    """
    通用设置组件
    """
    @classmethod
    def build_blk_i18n(cls):
        """
        标题: 国际化
        """
        blk_i18n = ft.Container(
            ft.Row(
                controls=[
                    ft.Text(
                        EndPoints.runtime["app_util_lang"].translate("Internationalization"), 
                        weight=ft.FontWeight.BOLD,
                        data={"i18n_key": "Internationalization"},
                    )
                ],
            )
        )
        return blk_i18n

    @classmethod
    def build_blk_language_switch(cls):
        """
        语言切换
        """
        all_language_list = EndPoints.runtime["app_util_profile"].languages_list()
        blk_switch_language = ft.Container(
            ft.Row(
                controls=[
                    ft.Text(
                        EndPoints.runtime["app_util_lang"].translate("language"),
                        data={"i18n_key": "language"},
                    ),
                    ft.Container(expand=True, expand_loose=True),
                    ft.PopupMenuButton(
                        # 关闭鼠标悬浮时显示的默认值: "Show menu"
                        # https://flet.dev/docs/controls/control
                        tooltip="",
                        # 显示的内容
                        content = ft.Row(
                            controls=[
                                ft.Container(
                                    content = ft.Text(
                                        value=EndPoints.runtime["app_language"], 
                                        size=14,
                                        ref=EndPoints.settings["switch_language"],
                                    ),
                                ), 
                                ft.Container(
                                    content=ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, size=13),
                                    padding=ft.Padding(left=0, top=2, right=0, bottom=0),
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        # 可选子项 - 此处使用了列表表达式 [x for x in all_language_list]
                        items=[
                            ft.PopupMenuItem(
                                content=lang, height=32,
                                on_click=cls.callback_language_switch,  # 可以利用 e.control 来获取对象本身
                                data={"language": lang},                # flet 对象本身可以利用 .data 来挂载自定义数据
                            )
                            for lang in all_language_list
                        ],
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
        return blk_switch_language

    @classmethod
    def callback_language_switch(cls, e: ft.ControlEvent):
        """
        回调函数 - 用于切换语言
        """
        # 利用 flet 的机制
        # e.control 可以获取到 PopupMenuItem 对象本身
        # data 可以挂载自定义数据
        lang = e.control.data.get("language")

        if lang != EndPoints.runtime["app_language"]:
            # 更改配置文件
            EndPoints.runtime["app_util_profile"].language_set(lang=lang)
            # 修改界面上显示的值
            EndPoints.settings["switch_language"].current.value = EndPoints.runtime["app_language"]

            # 自动更新 - 导航栏
            try:
                nav_controls = EndPoints.root["navigation"].current.content.controls
                for nav_control in nav_controls:
                    # 只针对导航栏的 IconButton 类型, 抓取控件 data={"i18n_key": <key>}
                    if type(nav_control.content) == ft.IconButton:
                        i18n_key = nav_control.content.data.get("i18n_key")
                        nav_control.content.tooltip = EndPoints.runtime["app_util_lang"].translate(key=i18n_key)

                # 自动更新 - 设置 Lv1
                settings_lv1_controls = EndPoints.settings["lv1_view"].current.content.controls
                for lv1_control in settings_lv1_controls:
                    # 只针对按钮 ft.Button 类型
                    if type(lv1_control) == ft.Button:
                        i18n_key = lv1_control.data.get("i18n_key")
                        lv1_control.content = EndPoints.runtime["app_util_lang"].translate(key=i18n_key)

                # 自动更新 - 设置 Lv2
                settings_lv2_controls = EndPoints.settings["lv2_view"].current.content.controls
                for lv2_control in settings_lv2_controls:
                    # ft.Container -> ft.Row
                    if type(lv2_control) == ft.Container:
                        if type(lv2_control.content) == ft.Row:
                            for lv2_sub_control in lv2_control.content.controls:
                                # ft.Row 里面的控件里 data 不为 None
                                if lv2_sub_control.data:
                                    i18n_key = lv2_sub_control.data.get("i18n_key")
                                    # data 中存在 i18n_key & type 为 ft.Text
                                    if i18n_key and type(lv2_sub_control) == ft.Text:
                                        lv2_sub_control.value = EndPoints.runtime["app_util_lang"].translate(key=i18n_key)
            # 自动更新出错仅提示即可
            except Exception as e:
                logger.warning(e)