import flet as ft
from src.endpoints import EndPoints
from src.utils.logging import logger

# 等宽字体: 代码块 / 需要对齐的场景
# 注意: FONT_ALL 引用本常量, 因此定义顺序必须在 FONT_ALL 之前
FONT_MONO = [
    "Consolas",         # Windows 英文等宽首选
    "Cascadia Mono",    # Win11 / Windows Terminal 自带
    "Courier New",      # 各平台通用兜底
    "Lucida Console",   # Windows 老牌等宽
    "Monaco",           # macOS 等宽
    "MS Gothic",        # 日文等宽 (Windows 自带)
]
# 全部字体: 中 / 英 / 日 常用比例字体 + 等宽字体 (等宽排在后面)
FONT_ALL = [
    "Microsoft YaHei",  # 中文: 微软雅黑
    "Segoe UI",         # 英文: Windows 系统 UI 字体
    "Arial",            # 英文: 通用无衬线
    "Meiryo",           # 日文: メイリオ
    *FONT_MONO,         # 等宽字体纳入可选范围, 排在比例字体之后
]


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
                        EndPoints.runtime["app_util_lang"].translate("internationalization"), 
                        weight=ft.FontWeight.BOLD,
                        data={"i18n_key": "internationalization"},
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
    def build_blk_font_family(cls):
        """
        标题: 字体
        """
        blk_font_family = ft.Container(
            ft.Row(
                controls=[
                    ft.Text(
                        EndPoints.runtime["app_util_lang"].translate("font_family"), 
                        weight=ft.FontWeight.BOLD,
                        data={"i18n_key": "font_family"},
                    )
                ],
            )
        )
        return blk_font_family

    @classmethod
    def build_blk_font_family_switch(cls, font_type: str):
        """
        字体切换

        Args:
        - font_type: 字体负责的范围 global / text / code
        """
        # 基于 font_type 来确认字体属于哪个分类
        if font_type == "global":
            font_value = EndPoints.runtime["app_util_lang"].translate("font_family_global")
            font_current_value = EndPoints.runtime["app_util_profile"].font_family_global()
            font_i18n_key = "font_family_global"
            font_ref = EndPoints.settings[font_i18n_key]
        elif font_type == "text":
            font_value = EndPoints.runtime["app_util_lang"].translate("font_family_text")
            font_current_value = EndPoints.runtime["app_util_profile"].font_family_text()
            font_i18n_key = "font_family_text"
            font_ref = EndPoints.settings[font_i18n_key]
        elif font_type == "code":
            font_value = EndPoints.runtime["app_util_lang"].translate("font_family_code")
            font_current_value = EndPoints.runtime["app_util_profile"].font_family_code()
            font_i18n_key = "font_family_code"
            font_ref = EndPoints.settings[font_i18n_key]
        else:
            font_value = EndPoints.runtime["app_util_lang"].translate("font_family_global")
            font_current_value = EndPoints.runtime["app_util_profile"].font_family_global()
            font_i18n_key = "font_family_global"
            font_ref = EndPoints.settings[font_i18n_key]
            logger.warning("font_type error, falling back to font_family_global")

        # 字体切换控件
        blk_switch_font_family = ft.Container(
            ft.Row(
                controls=[
                    ft.Text(
                        font_value,
                        data={"i18n_key": font_i18n_key},
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
                                        value=font_current_value, 
                                        size=14,
                                        ref=font_ref,
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
                                content=font_family, height=32,
                                on_click=cls.callback_font_family_switch,
                                data={"font_family": font_family, "font_type": font_type},
                            )
                            for font_family in (FONT_MONO if font_type == "code" else FONT_ALL)
                        ],
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
        return blk_switch_font_family

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

            try:
                # 自动更新 - 导航栏
                cls.refresh_i18n(EndPoints.root["navigation"].current)
                # 自动更新 - 设置 Lv1
                cls.refresh_i18n(EndPoints.settings["lv1_view"].current)
                # 自动更新 - 设置 Lv2
                cls.refresh_i18n(EndPoints.settings["lv2_view"].current)
            # 自动更新出错仅提示即可
            except Exception as e:
                logger.warning(e)

    @classmethod
    def callback_font_family_switch(cls, e: ft.ControlEvent):
        """
        回调函数 - 用于切换字体
        """
        font = e.control.data
        font_type = font.get("font_type")
        font_family = font.get("font_family")
        if font_type == "global":
            # 保存 & 更新当前显示的字体值
            EndPoints.runtime["app_util_profile"].font_family_global_set(font_family=font_family)
            EndPoints.settings["font_family_global"].current.value = font_family
            # 刷新全局字体设置
            page = EndPoints.root["page"]
            if page is not None:
                theme = ft.Theme(font_family=font_family)
                # theme_mode 默认 system, 深色模式走 dark_theme, 两处都要设
                page.theme = theme
                page.dark_theme = theme
                page.update()
        elif font_type == "text":
            EndPoints.runtime["app_util_profile"].font_family_text_set(font_family=font_family)
            EndPoints.settings["font_family_text"].current.value = font_family
        elif font_type == "code":
            EndPoints.runtime["app_util_profile"].font_family_code_set(font_family=font_family)
            EndPoints.settings["font_family_code"].current.value = font_family

    @classmethod
    def refresh_i18n(cls, control: ft.BaseControl | None):
        """
        自动刷新 - 递归遍历控件树, 刷新所有以 data={"i18n_key": <key>} 自标识的控件

        回写字段按控件类型决定:
        - ft.Text       -> value
        - ft.Button     -> content (仅当 content 为文本时)
        - ft.IconButton -> tooltip
        """
        if not isinstance(control, ft.BaseControl):
            return

        # 1. 自身携带 i18n_key: 按控件类型回写对应字段
        data = getattr(control, "data", None)
        data = data if isinstance(data, dict) else None
        i18n_key = data.get("i18n_key") if data else None
        if i18n_key:
            text = EndPoints.runtime["app_util_lang"].translate(key=i18n_key)
            if isinstance(control, ft.Text):
                control.value = text
            elif isinstance(control, ft.Button):
                # Button 的 content 可能被替换成子控件, 此时不覆盖
                if isinstance(control.content, str):
                    control.content = text
            elif isinstance(control, ft.IconButton):
                control.tooltip = text

        # 2. 递归子控件: 容器的 content / 列表类的 controls & items / ListTile 等的 title 等
        for attr in ("content", "controls", "items", "title", "subtitle", "leading", "trailing"):
            child = getattr(control, attr, None)
            if isinstance(child, (list, tuple)):
                for item in child:
                    cls.refresh_i18n(item)
            else:
                cls.refresh_i18n(child)