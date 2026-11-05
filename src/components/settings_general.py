import ipaddress
import re
from urllib.parse import urlparse

import flet as ft
from endpoints import EndPoints
from utils.logging import logger

# 等宽字体: 代码块 / 需要对齐的场景
# 注意: FONT_ALL 引用本常量, 因此定义顺序必须在 FONT_ALL 之前
FONT_MONO = [
    "Consolas",             # Windows 英文等宽首选
    "Cascadia Mono",        # Win11 / Windows Terminal 自带
    "Courier New",          # 各平台通用兜底
    "Lucida Console",       # Windows 老牌等宽
    "Monaco",               # macOS 等宽
    "MS Gothic",            # 日文等宽 (Windows 自带)
]
# 全部字体: 中 / 英 / 日 常用比例字体 + 等宽字体 (等宽排在后面)
FONT_ALL = [
    "Microsoft YaHei UI",   # 中文: 微软雅黑
    "Segoe UI",             # 英文: Windows 系统 UI 字体
    "Arial",                # 英文: 通用无衬线
    "Meiryo",               # 日文: メイリオ
    *FONT_MONO,             # 等宽字体纳入可选范围, 排在比例字体之后
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
    def build_blk_proxy(cls):
        """
        标题: 代理配置
        """
        blk_proxy = ft.Container(
            ft.Row(
                controls=[
                    ft.Text(
                        EndPoints.runtime["app_util_lang"].translate("proxy_config"), 
                        weight=ft.FontWeight.BOLD,
                        data={"i18n_key": "proxy_config"},
                    )
                ],
            )
        )
        return blk_proxy

    @classmethod
    def build_blk_proxy_address(cls):
        """
        代理地址
        """
        blk_proxy_addr = ft.Container(
            ft.Row(
                controls=[
                    ft.Text(
                        value=EndPoints.runtime["app_util_lang"].translate("proxy_address"),
                        data={"i18n_key": "proxy_address"},
                    ),
                    ft.Container(expand=True, expand_loose=True),
                    ft.TextField(
                        value=EndPoints.runtime["app_util_profile"].proxy_address(),
                        text_size=13,
                        text_style=ft.TextStyle(size=13),
                        hint_text="http://localhost:1080",
                        hint_style=ft.TextStyle(size=13, color=ft.Colors.GREY_500),
                        dense=True,
                        content_padding=ft.Padding(left=0, top=5, right=0, bottom=5),
                        on_blur=cls.callback_proxy_address,
                    ),
                ],
            )
        )
        return blk_proxy_addr

    @classmethod
    def build_blk_proxy_ignore(cls):
        """
        代理的忽略地址
        """
        blk_proxy_ignore = ft.Container(
            ft.Row(
                controls=[
                    ft.Text(
                        value=EndPoints.runtime["app_util_lang"].translate("proxy_ignore"),
                        data={"i18n_key": "proxy_ignore"},
                    ),
                    ft.Container(expand=True, expand_loose=True),
                    ft.TextField(
                        value=EndPoints.runtime["app_util_profile"].proxy_ignore(),
                        text_size=13,
                        text_style=ft.TextStyle(size=13),
                        hint_text="localhost,127.0.0.1",
                        hint_style=ft.TextStyle(size=13, color=ft.Colors.GREY_500),
                        dense=True,
                        content_padding=ft.Padding(left=0, top=5, right=0, bottom=5),
                        on_blur=cls.callback_proxy_ignore,
                    ),
                ],
            )
        )
        return blk_proxy_ignore

    @classmethod
    def build_blk_web_search(cls):
        """
        标题: 网络搜索
        """
        blk_web_search = ft.Container(
            ft.Row(
                controls=[
                    ft.Text(
                        EndPoints.runtime["app_util_lang"].translate("web_search"), 
                        weight=ft.FontWeight.BOLD,
                        data={"i18n_key": "web_search"},
                    )
                ],
            )
        )
        return blk_web_search

    @classmethod
    def build_blk_web_search_engine(cls):
        """
        网络搜索引擎切换
        """
        all_web_search_engine = EndPoints.runtime["web_search_engine"]
        blk_switch_web_engine = ft.Container(
            ft.Row(
                controls=[
                    ft.Text(
                        EndPoints.runtime["app_util_lang"].translate("web_search_engine"),
                        data={"i18n_key": "web_search_engine"},
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
                                        value=EndPoints.runtime["app_util_profile"].web_search_engine(), 
                                        size=14,
                                        ref=EndPoints.settings["web_search_engine"],
                                    ),
                                ), 
                                ft.Container(
                                    content=ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, size=13),
                                    padding=ft.Padding(left=0, top=2, right=0, bottom=0),
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        # 可选子项 - 此处使用了列表表达式 [x for x in all_web_engine_list]
                        items=[
                            ft.PopupMenuItem(
                                content=search_engine, height=32,
                                on_click=cls.callback_web_search_engine,   # 可以利用 e.control 来获取对象本身
                                data={"search_engine": search_engine},     # flet 对象本身可以利用 .data 来挂载自定义数据
                            )
                            for search_engine in all_web_search_engine
                        ],
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
        return blk_switch_web_engine

    @classmethod
    def build_blk_web_search_proxy(cls):
        """
        构建 Web 搜索代理开关组件
        """
        blk_web_search_proxy = ft.Container(
            ft.Row(
                controls=[
                    ft.Text(
                        EndPoints.runtime["app_util_lang"].translate("web_search_proxy"),
                        data={"i18n_key": "web_search_proxy"},
                    ),
                    ft.Container(expand=True, expand_loose=True),
                    ft.Switch(
                        height=20,
                        padding=ft.Padding.symmetric(vertical=0, horizontal=0),
                        value=EndPoints.runtime["app_util_profile"].web_search_proxy(),
                        on_change=cls.callback_web_search_proxy,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
        return blk_web_search_proxy

    @classmethod
    def build_blk_web_search_max_length(cls):
        """
        构建 Web 搜索单次搜索所返回的最大字符长度组件
        """
        blk_web_search_max_length = ft.Container(
            ft.Row(
                controls=[
                    ft.Text(
                        EndPoints.runtime["app_util_lang"].translate("web_search_max_length"),
                        data={"i18n_key": "web_search_max_length"},
                    ),
                    ft.Container(expand=True, expand_loose=True),
                    ft.TextField(
                        value=EndPoints.runtime["app_util_profile"].web_search_max_length(),
                        text_size=13,
                        text_style=ft.TextStyle(size=13),
                        hint_text="128000",
                        hint_style=ft.TextStyle(size=13, color=ft.Colors.GREY_500),
                        dense=True,
                        content_padding=ft.Padding(left=0, top=5, right=0, bottom=5),
                        on_blur=cls.callback_web_search_max_length,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
        return blk_web_search_max_length

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
    def callback_proxy_address(cls, e):
        """
        回调函数 - 更新 proxy address 的值

        校验规则:
        - 空值 / 不合法 -> 仅记录日志, 不写入配置
        - 合法 -> 写入 profile.yaml

        合法形式: <scheme>://<host>[:<port>], 例如 "http://localhost:8080" 或 ”socks5://127.0.0.1:8080"
        """
        # 空值忽略
        proxy_addr = (e.control.value or "").strip()
        if not proxy_addr:
            logger.warning("proxy address is empty, skip saving")
            return
        # 拆分出 scheme / host / port, 非法 IPv6 / 越界端口都会抛 ValueError
        try:
            parsed = urlparse(proxy_addr)
            scheme = parsed.scheme
            host = parsed.hostname
            parsed.port
        except ValueError:
            logger.warning(f"invalid proxy address: {proxy_addr}")
            return
        # 1. scheme 必须在白名单内
        if scheme not in ("http", "https", "socks4", "socks5", "socks5h"):
            logger.warning(f"invalid proxy address (scheme): {proxy_addr}")
            return
        # 2. 必须有 host
        if not host:
            logger.warning(f"invalid proxy address (host): {proxy_addr}")
            return
        # 保存合法的设定值
        EndPoints.runtime["app_util_profile"].proxy_address_set(proxy_addr=proxy_addr)

    @classmethod
    def callback_proxy_ignore(cls, e):
        """
        回调函数 - 更新 proxy ignore 的值

        校验规则:
        - 按逗号拆成单条规则, 逐条校验, 只保留合法的规则
        - 空值 / 全部不合法 -> 仅记录日志, 不写入配置

        合法形式: <host>[:<port>], 支持域名 / IPv4 / IPv6 / CIDR, 例如 "localhost"、"127.0.0.1"、".example.com"、"192.168.0.0/16"
        """
        raw_value = (e.control.value or "").strip()
        # 空值忽略
        if not raw_value:
            logger.warning("proxy ignore is empty, skip saving")
            return

        # 逗号产生的空项直接丢弃, 不算错误
        entries = [item.strip() for item in raw_value.split(",") if item.strip()]
        valid_items = []
        for item in entries:
            # 拆分 host / port:
            # - [IPv6]:port 用方括号区分冒号
            # - 仅当只有一个冒号时才可能是 host:port (裸写 IPv6 含多个冒号)
            host, port = item, ""
            if item.startswith("["):
                end = item.find("]")
                if end == -1:
                    logger.warning(f"invalid proxy ignore entry (bracket): {item}")
                    continue
                host, rest = item[1:end], item[end + 1:]
                if rest.startswith(":"):
                    port = rest[1:]
                elif rest:
                    logger.warning(f"invalid proxy ignore entry (bracket): {item}")
                    continue
            elif item.count(":") == 1:
                host, port = item.split(":", 1)

            # 1. 端口可选, 一旦给出就必须是合法端口号
            if port and not (port.isdigit() and 0 < int(port) <= 65535):
                logger.warning(f"invalid proxy ignore entry (port): {item}")
                continue

            # 2. 域名 / 通配域名去掉前导 "*." 或 "."
            domain = host[2:] if host.startswith("*.") else host.lstrip(".")
            if not domain:
                logger.warning(f"invalid proxy ignore entry (empty host): {item}")
                continue

            # 3. IP / CIDR / 域名 三者任一通过即视为合法
            try:
                ipaddress.ip_address(domain)
            except ValueError:
                try:
                    ipaddress.ip_network(domain, strict=False)
                except ValueError:
                    is_domain = bool(
                        len(domain) <= 253
                        and re.fullmatch(
                            r"[A-Za-z0-9_](?:[A-Za-z0-9_-]{0,61}[A-Za-z0-9_])?"
                            r"(?:\.[A-Za-z0-9_](?:[A-Za-z0-9_-]{0,61}[A-Za-z0-9_])?)*",
                            domain,
                        )
                    )
                    if not is_domain:
                        logger.warning(f"invalid proxy ignore entry (host): {item}")
                        continue

            valid_items.append(item)

        # 没有任何合法规则 -> 不写入配置
        if not valid_items:
            logger.warning(f"proxy ignore has no valid entry, skip saving: {raw_value}")
            return

        proxy_ignore = ",".join(valid_items)
        # 有规则被剔除时提示实际写入的内容
        if len(valid_items) != len(entries):
            logger.warning(f"proxy ignore has invalid entry, saved: {proxy_ignore}")
        # 保存合法的设定值
        EndPoints.runtime["app_util_profile"].proxy_ignore_set(proxy_ignore=proxy_ignore)

    @classmethod
    def callback_web_search_engine(cls, e: ft.ControlEvent):
        """
        回调函数 - 用于切换搜索引擎
        """
        # 利用 flet 的机制
        # e.control 可以获取到 PopupMenuItem 对象本身
        # data 可以挂载自定义数据
        search_engine = e.control.data.get("search_engine")

        if search_engine != EndPoints.runtime["app_util_profile"].web_search_engine():
            # 更改配置文件
            EndPoints.runtime["app_util_profile"].web_search_engine_set(web_search_engine=search_engine)
            # 修改界面上显示的值
            EndPoints.settings["web_search_engine"].current.value = search_engine

    @classmethod
    def callback_web_search_proxy(cls, e: ft.ControlEvent):
        """
        回调函数 - 用于切换搜索引擎代理

        Args:
        - e: ft.ControlEvent, e.control 为 ft.Switch, e.control.value 为开关当前值
        """
        # Switch 的 value 即最新的开关状态
        web_search_proxy = bool(e.control.value)
        if web_search_proxy != EndPoints.runtime["app_util_profile"].web_search_proxy():
            # 更改配置文件
            EndPoints.runtime["app_util_profile"].web_search_proxy_set(web_search_proxy=web_search_proxy)

    @classmethod
    def callback_web_search_max_length(cls, e:ft.ControlEvent):
        """
        回调函数 - 用于修改网络搜索结果的最大长度
        """
        max_length = int(e.control.value)
        if max_length != EndPoints.runtime["app_util_profile"].web_search_max_length():
            # 更改配置文件
            EndPoints.runtime["app_util_profile"].web_search_max_length_set(web_search_max_length=max_length)

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