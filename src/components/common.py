"""
该模块的引入条件:
1. 不得 import 任何 src.components / view / cores 模块, 确保无环
2. 可复用, 同一块 UI 在多处出现
3. 数据和锚点请查看 src.endpoints.py 文件里的内容; 
   本文件 common.py 里只定义类似积木的组件模块, 不包含复杂的业务逻辑(尽可能独立成孤立的模块)
   -> 所有操作尽可能局限于在本类自己, 尽量不要跨越别的组件
"""
import copy
import flet as ft
from src.endpoints import EndPoints
from src.utils.logging import logger
from langchain.messages import AIMessage, ToolMessage


class AlertCommon:
    """
    AlertCommon - 弹窗提示
    """
    @classmethod
    def alert_model_config_error(cls, message: str):
        """
        弹窗提示: 模型配置错误

        Args:
        - message:  错误消息字符串
        """
        blk_alert = ft.AlertDialog(
            title=ft.Text(EndPoints.runtime["app_util_lang"].translate(key="default_model_config_error")),
            content=ft.Text(EndPoints.runtime["app_util_lang"].translate(key="default_model_config_error_desc") + message),
            actions=[ft.TextButton(EndPoints.runtime["app_util_lang"].translate(key="confirm"), on_click=lambda e: EndPoints.root["page"].pop_dialog())],
            open=True,
        )
        EndPoints.root["page"].show_dialog(blk_alert)

    @classmethod
    def alert_model_config_none(cls):
        """
        弹窗提示: 模型列表为空时提示需要先配置模型
        """
        blk_alert = ft.AlertDialog(
            title=ft.Text(EndPoints.runtime["app_util_lang"].translate(key="default_model_config_none")),
            content=ft.Text(EndPoints.runtime["app_util_lang"].translate(key="default_model_config_none_desc")),
            actions=[ft.TextButton(EndPoints.runtime["app_util_lang"].translate(key="confirm"), on_click=lambda e: EndPoints.root["page"].pop_dialog())],
            open=True,
        )
        EndPoints.root["page"].show_dialog(blk_alert)

class MessageUtilsCommon:
    """
    针对 LangChain AIMessage / ToolMessage / HumanMessage 的通用处理类

    Note:
    - 只负责「消息对象 -> 渲染数据」的归一化, 不创建任何 ft 控件
    - 消息块 (ft 控件) 见 MessageBlockCommon
    """
    @classmethod
    def format_ai_msg_content(cls, ai_msg: AIMessage) -> list[dict]:
        """
        重新格式化 AIMessage 里面的内容

        Note:
        - 正常情况 content 就是内容块列表, 例如 AIMessage 的 content 为:
            [
            {"type": "reasoning", ...}, 
            {"type": "tool_call", ...}, 
            {"type": "text", ...}
            ]
        - 但 content 也可能是纯字符串, 或字符串列表 (例如模型没有开启思考时直接返回正文)
            直接当列表遍历会按字符切分 => 这里统一归一化成内容块列表
        - 归一化后保证: 元素一定是 dict, 且一定带 "type"

        Args:
        - ai_msg: 单条 AIMessage

        Return:
        - list[dict]: 归一化后的内容块列表, 即 AIMessage.content (空 text 块已被剔除)
        """
        # 先统一成列表, 便于后续逐块处理
        src_aimsg_content = ai_msg.content
        if src_aimsg_content is None:                   # 为空值时直接返回
            logger.warning("AIMessage content is None, fallback to empty list.")
            return []
        elif not isinstance(src_aimsg_content, list):   # 非列表: 纯字符串 / 单个内容块, 包一层列表即可
            src_blocks = [src_aimsg_content]
        else:
            src_blocks = src_aimsg_content              # 为列表时, 原封不动

        finish_aimsg_content = []
        for aimsg in src_blocks:
            # 列表里的元素理论上都是 dict, 但旧数据 / 特殊 provider 可能混入纯字符串或其它对象
            # 这里一律视作 text 块, 并把内容转成 str (下游 ft.Markdown(value=...) 只接受 str)
            if not isinstance(aimsg, dict):
                aimsg = {"type": "text", "text": aimsg if isinstance(aimsg, str) else str(aimsg)}
            # 缺 "type" 的 dict 同样按 text 处理, 保证调用方可以安全地取 ["type"]
            elif "type" not in aimsg:
                aimsg = {**aimsg, "type": "text"}
            # text 块: 空内容直接跳过 (工具调用轮 / 思考晚于正文到达时可能混入空串), 非 str 则转 str
            if aimsg.get("type") == "text":
                if not aimsg.get("text"):
                    continue
                if not isinstance(aimsg.get("text"), str):
                    aimsg = {**aimsg, "text": str(aimsg.get("text"))}
            finish_aimsg_content.append(aimsg)

        return finish_aimsg_content

    @classmethod
    def format_tool_msg_markdown(cls, tool_msg: ToolMessage) -> str:
        """
        重新格式化 ToolMessage 里面的内容, 用于渲染 Markdown

        Note:
        1. 正常情况 content 是内容块列表, 例如 MCP 工具返回:
           [{"type": "text", "text": "## Search Results ..."}]
           -> 直接把列表交给 ft.Markdown, 界面上会渲染出列表的 repr
        2. 普通工具直接返回字符串
        3. 目前只支持 text 块; 图片 / 文件等后续再处理
           -> 不支持的块只在整条消息上汇总告警一次, 避免逐块刷屏

        Args:
        - tool_msg: 单条 ToolMessage

        Returns:
        - str: 格式化后的文本内容, 用于渲染 Markdown
        """
        content = tool_msg.content
        # 不是列表: 原样输出 (普通工具直接返回字符串)
        if isinstance(content, str):
            return content
        # 没有内容: 返回空串, 避免下游 ft.Markdown(value=...) 拿到 None
        if content is None:
            return ""
        # 兜底: content 理论上只会是 str / list
        if not isinstance(content, list):
            return str(content)
        # 如果是列表, 则继续检查里面的内容
        markdown_parts = []
        unsupported_blocks = []
        for block in content:
            # 纯字符串元素: 视作 text 块 (content 的类型允许 list[str | dict])
            if isinstance(block, str):
                if block:
                    markdown_parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text")
                if text:
                    markdown_parts.append(text if isinstance(text, str) else str(text))
            # 其余类型 (图片 / 文件 / 嵌入式资源等) 暂时不支持
            else:
                unsupported_blocks.append(block)
        # 汇总告警: 一条 ToolMessage 只打一次
        if unsupported_blocks:
            logger.warning(f"ToolMessage has {len(unsupported_blocks)} unsupported content block(s)!")
            logger.debug(f"unsupported content blocks: {unsupported_blocks}")
        return "\n\n".join(markdown_parts).strip()
    
    @classmethod
    def session_id_current(cls):
        """
        获取当前的 session_id

        Note:
        - 与 InputCommon.refresh_input_attachments 的识别规则保持一致
        - session_id_chat_current / session_id_agent_current 至多一个非 None
          (停在 docs / settings 时两个都为 None)

        Return:
        - Dict: {"type": "chat/agent", "session_id": str} / None
        """
        chat_id = EndPoints.runtime["session_id_chat_current"]
        agent_id = EndPoints.runtime["session_id_agent_current"]
        # 互斥约定被破坏: 无法判定属于哪个界面, 直接放弃
        if chat_id is not None and agent_id is not None:
            logger.error("mutex violated: both chat and agent session ids are set")
            return None
        elif chat_id is not None:
            return {"type": "chat", "session_id": chat_id}
        elif agent_id is not None:
            return {"type": "agent", "session_id": agent_id}
        else:
            logger.debug("no active session.")
            return None


class MessageBlockCommon:
    """
    通用消息块 (纯渲染, 不持有状态)

    Note:
    - 消息数据归一化见 MessageUtilsCommon
    - 需要回调的块由调用方注入 (本模块不得 import 任何组件, 也不得读写 EndPoints.chat)
    """
    @classmethod
    def build_blk_user_msg(cls, user_msg: list[dict], user_msg_id=None, on_retry=None):
        """
        构建一个 User 消息块, 格式参考了如下文档
        https://docs.langchain.com/oss/python/langchain/messages#multimodal

        Args:
        - user_msg:     多模态的用户消息内容, 参考了 HumanMessage 的格式: [{"type": "text", "text": ***}]
        - user_msg_id:  用户消息的唯一标识符, 如果 user_msg 的数据类型为 HumanMessage, 则忽略传入的值, 否则不传则会自动生成
        - on_retry:     重试按钮的回调; 不传则不绑定 (公共层不反向依赖任何组件, 故由调用方注入)

        Return:
        - Flet Container 控件对象
        """
        # 整理消息
        text = ""
        images = []
        for i in user_msg:
            if i["type"] == "text":
                text = i["text"]
            if i["type"] == "image":
                images.append(i["url"])

        # 用户消息体控件
        user_msg_body = ft.Container(
            ft.Markdown(
                value=text,
            ),
            padding=ft.Padding.symmetric(vertical=3, horizontal=5),
            border=ft.border.Border.all(width=1, color=ft.Colors.GREEN_200),
            bgcolor=ft.Colors.GREEN_100,
            border_radius=5,
        )

        # 截图数据
        user_msg_images = ft.Container(ft.Row(wrap=True))
        for img in images:
            user_msg_images.content.controls.append(
                ft.Image(
                    src=img, 
                    # https://flet.dev/docs/controls/image#flet.Image.fit
                    # https://flet.dev/docs/types/boxfit/
                    fit=ft.BoxFit.SCALE_DOWN,
                )
            )

        # 组装组件
        user_msg_blk = ft.Container(
            ft.Column(
                controls=[
                    user_msg_images if images is not [] else None,
                    user_msg_body,
                    ft.Row(
                        controls=[
                            # 复制按钮
                            ft.Container(
                                content=ft.IconButton(icon=ft.Icons.COPY, icon_size=14, padding=0),
                                width=18,
                                height=18,
                            ),
                            # 重试按钮
                            ft.Container(
                                # ft.Icons.REFRESH / ft.Icons.LOOP
                                content=ft.IconButton(
                                    icon=ft.Icons.AUTORENEW,
                                    icon_size=14,
                                    padding=0,
                                    on_click=on_retry,
                                ),
                                width=18,
                                height=18,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                        spacing=5,
                    )
                ],
                spacing=5,
            ),
            data={"msg_type": "user_msg", "user_msg": user_msg, "user_msg_id": user_msg_id, "lc_run_id": None},
            # border=ft.border.Border.all(width=1, color=ft.Colors.GREY_500),
            # border_radius=5,
        )
        # 调整日志显示内容
        show_user_msg = copy.deepcopy(user_msg)
        idx = 1
        for msg in show_user_msg:
            if msg["type"] == "image":
                msg["url"] = f"image_{idx}"
                idx += 1
        logger.warning(show_user_msg)
        return user_msg_blk

    @classmethod
    def build_blk_ai_reasoning(cls, reasoning="", lc_run_id=None, blk_status="finish", reasoning_high=50):
        """
        构建一个 AI 思考消息块

        Args:
        - reasoning:        思考内容
        - lc_run_id:        LangChain AIMessage 里面的 Internal tracing/callback ID, Reasoning 包含在 AIMessage 中
        - blk_status:       块状态, finish 表示思考内容已经完成, 其余任何值均属于未完成
        - reasoning_high:   思考块在关闭刷新时的最高高度

        Return:
        - Flet Container 控件对象
        """
        # 设定思考中的相关控件
        #############################################################################
        def _on_reasoning_text_size(e):
            """
            动态调整高度的回调函数
            e.height 为该 Text 的完整自然高, 用 min 封顶到指定高度
            """
            new_h = min(int(e.height or 0), reasoning_high)
            if new_h != reasoning_subtitle.height:
                reasoning_subtitle.height = new_h
                reasoning_subtitle.update()

        # 将 ft.Text 包裹在一个可混动的  ft.Column 中
        reasoning_subtitle = ft.Column(
            controls=[
                # ft.Text 不设 max_lines/overflow, 让它在滚动视图里按完整内容布局
                # 这样 on_size_change 时才能读到 "全文自然高"
                ft.Text(
                    value=reasoning,
                    selectable=True,
                    size_change_interval=0,
                    on_size_change=_on_reasoning_text_size,
                ),
            ],
            scroll=ft.ScrollMode.HIDDEN,    # 隐藏滚动条, 仍可滚动, 用 auto_scroll 跟随
            auto_scroll=True,
            auto_scroll_animation=0,        # token 级流式, 瞬时跳底, 避免动画滞后
            height=reasoning_high,
        )
        #############################################################################

        reasoning_blk = ft.Container(
            ft.ExpansionTile(
                dense=True,
                title=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.LIGHTBULB_CIRCLE_ROUNDED, size=18),
                        ft.Text(value=EndPoints.runtime["app_util_lang"].translate(key="reasoning") if blk_status != "finish" else EndPoints.runtime["app_util_lang"].translate(key="reason_finish")),
                    ],
                    spacing=3,
                ),
                tile_padding=ft.Padding.symmetric(vertical=0, horizontal=5),
                subtitle=reasoning_subtitle if blk_status != "finish" else None,
                controls=[
                    ft.Markdown(
                        value=reasoning,
                        selectable=True, # 允许用户选中复制
                        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                        code_theme=ft.MarkdownCodeTheme.GITHUB,
                    ),
                ],
                # 保持控件状态, 防止展开后重新渲染引发的闪烁
                maintain_state=True,
                expanded_alignment=ft.Alignment.BOTTOM_LEFT,
                # ExpansionTile 控件可以通过这种方式来自己绘制边框
                # 展开时: https://flet.dev/docs/controls/expansiontile#flet.ExpansionTile.shape
                # 收缩时: https://flet.dev/docs/controls/expansiontile#flet.ExpansionTile.collapsed_shape
                shape=ft.RoundedRectangleBorder(side=ft.BorderSide(width=1, color=ft.Colors.GREY_500), radius=5),
                collapsed_shape=ft.RoundedRectangleBorder(side=ft.BorderSide(width=1, color=ft.Colors.GREY_500), radius=5),
            ),
            data={"msg_type": "reasoning", "lc_run_id": lc_run_id},
        )
        return reasoning_blk

    @classmethod
    def build_blk_ai_tool_call(cls, args_dict, lc_run_id=None):
        """
        构建一个 AI Tool Call 消息块

        Args:
        - args_dict:    Tool Call 的参数字典
        - lc_run_id:    LangChain AIMessage 里面的 Internal tracing/callback ID, Tool Call 的参数包含在 AIMessage 中

        Return:
        - Flet Container 控件对象
        """
        tool_call_blk = ft.Container(
            ft.ExpansionTile(
                dense=True,
                title=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.BUILD_CIRCLE_ROUNDED, size=18),
                        ft.Text(value=f"{args_dict.get("name")}"),
                    ],
                    spacing=3,
                ),
                tile_padding=ft.Padding.symmetric(vertical=0, horizontal=5),
                subtitle=ft.Text(
                    value=f"{args_dict.get("args")}", 
                    size=11,
                    color=ft.Colors.GREY_600,
                ),
                # ExpansionTile 控件可以通过这种方式来自己绘制边框
                # 展开时: https://flet.dev/docs/controls/expansiontile#flet.ExpansionTile.shape
                # 收缩时: https://flet.dev/docs/controls/expansiontile#flet.ExpansionTile.collapsed_shape
                shape=ft.RoundedRectangleBorder(side=ft.BorderSide(width=1, color=ft.Colors.GREY_500), radius=5),
                collapsed_shape=ft.RoundedRectangleBorder(side=ft.BorderSide(width=1, color=ft.Colors.GREY_500), radius=5),
            ),
            data={"msg_type": "tool_call", "lc_run_id": lc_run_id, "tool_call_id": args_dict.get("id")},
        )
        # 补充结果
        if args_dict.get("tool_result"):
            tool_call_blk.content.controls = ft.Markdown(value=args_dict.get("tool_result"))
            
        return tool_call_blk

    @classmethod
    def build_blk_ai_text(cls, text="", lc_run_id=None):
        """
        构建一个 AI 消息块 (中间的输出)

        Args:
        - text:         AI 消息内容
        - lc_run_id:    LangChain AIMessage 里面的 Internal tracing/callback ID

        Note:
        不设 expand/expand_loose: 它们只作用于「直接父控件的主轴」
        而本块的父控件是 chat_body 那个滚动 Column (主轴=竖直且无界)
        -> 既不撑宽度, 也不撑高度, 是误导性死代码
        -> 横向铺满由该 Column 的 horizontal_alignment=STRETCH 负责
        -> 实际布局见 chat_view.render_lv2

        Return:
        - Flet Container 控件对象
        """
        ai_msg_blk = ft.Container(
            ft.Markdown(
                value=text,
                selectable=True,
            ),
            data={"msg_type": "text", "lc_run_id": lc_run_id},
            padding=ft.Padding.symmetric(vertical=3, horizontal=5),
            border=ft.border.Border.all(width=1, color=ft.Colors.GREY_500),
            border_radius=5,
        )
        return ai_msg_blk

    @classmethod
    def build_blk_ai_text_finally(cls, text="", lc_run_id=None, on_retry=None):
        """
        构建一个 AI 消息块 (仅针对最后的输出内容)

        Args:
        - text:         AI 消息内容
        - lc_run_id:    LangChain AIMessage 里面的 Internal tracing/callback ID
        - on_retry:     重试按钮的回调; 不传则不绑定 (公共层不反向依赖任何组件, 故由调用方注入)

        Note:
        不设 expand/expand_loose: 它们只作用于「直接父控件的主轴」
        而本块的父控件是 chat_body 那个滚动 Column (主轴=竖直且无界)
        -> 既不撑宽度, 也不撑高度, 是误导性死代码
        -> 横向铺满由该 Column 的 horizontal_alignment=STRETCH 负责
        -> 实际布局见 chat_view.render_lv2

        Return:
        - Flet Container 控件对象
        """
        ai_msg_blk = ft.Container(
            ft.Column(
                controls=[
                    ft.Markdown(
                        value=text,
                        selectable=True,
                    ),
                    ft.Row(
                        controls=[
                            # 复制按钮
                            ft.Container(
                                content=ft.IconButton(icon=ft.Icons.COPY, icon_size=14, padding=0),
                                width=18,
                                height=18,
                            ),
                            # 重试按钮
                            ft.Container(
                                # ft.Icons.REFRESH / ft.Icons.LOOP
                                content=ft.IconButton(icon=ft.Icons.AUTORENEW, icon_size=14, padding=0, on_click=on_retry),
                                width=18,
                                height=18,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                        spacing=5,
                    )
                ],
                spacing=5,
            ),
            data={"msg_type": "text", "lc_run_id": lc_run_id},
            padding=ft.Padding.symmetric(vertical=3, horizontal=0),
        )
        return ai_msg_blk

    @classmethod
    def build_blk_ai_summary(cls):
        """
        构建一个 AI 中间 思考/工具调用 的总结块
        """
        ai_summary_blk = ft.Container(
            ft.ExpansionTile(
                dense=True,
                title="AI Summary",
                tile_padding=ft.Padding.symmetric(vertical=0, horizontal=11),
                # 添加一个 ft.Column 控件, 因为 ft.ExpansionTile 不支持调整控件的间距
                controls=[ft.Column(margin=ft.Margin.symmetric(horizontal=5, vertical=5), spacing=5)],
                # ExpansionTile 控件可以通过这种方式来自己绘制边框
                # 展开时: https://flet.dev/docs/controls/expansiontile#flet.ExpansionTile.shape
                # 收缩时: https://flet.dev/docs/controls/expansiontile#flet.ExpansionTile.collapsed_shape
                shape=ft.RoundedRectangleBorder(side=ft.BorderSide(width=1, color=ft.Colors.GREY_500), radius=5,),
                collapsed_shape=ft.RoundedRectangleBorder(side=ft.BorderSide(width=1, color=ft.Colors.GREY_500), radius=5),
            ),
            data={"msg_type": "ai_summary", "lc_run_id": None},
        )
        return ai_summary_blk

    @classmethod
    def build_blk_err_msg(cls, reason: str, status="error", errmsg=None, on_retry=None):
        """
        构建一个显示错误的消息块

        Args:
        - reason:   错误的原因概述 (异常首行), 渲染为标题 (最多 3 行)
        - status:   错误的状态, 值可以是 error / aborted
        - errmsg:   错误信息详情 (完整文本), 不传时中止场景用固定文案 / 错误场景复用 reason
        - on_retry: 重试按钮的回调; 不传则不渲染重试按钮 (公共层不反向依赖任何组件, 故由调用方注入)

        Return:
        - ft.Container 控件对象
        """
        # 图标 / 颜色随状态切换: aborted 用橙色警告, error 用红色错误
        is_aborted = status == "aborted"
        accent_color = ft.Colors.ORANGE if is_aborted else ft.Colors.RED

        if is_aborted and errmsg is None:
            errmsg = EndPoints.runtime["app_util_lang"].translate(key="request_was_aborted_desc")
        elif errmsg is None:
            # 错误场景的 reason 本身就是异常首行, 直接复用为详情 (缺省而不是塞一句英文占位)
            errmsg = reason

        # 按钮行: 复制始终存在, 重试按钮依赖调用方注入的回调
        subtitle_controls = [
            # 复制按钮: 用于复制错误详情
            ft.TextButton(
                content=ft.Text(
                    value=EndPoints.runtime["app_util_lang"].translate(key="copy"),
                    style=ft.TextStyle(color=ft.Colors.BLACK, size=12),
                ),
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5)),
                height=26,
            ),
        ]
        if on_retry is not None:
            # 重试按钮: 用于重新发送消息
            subtitle_controls.append(
                ft.TextButton(
                    content=ft.Text(
                        value=EndPoints.runtime["app_util_lang"].translate(key="retry"),
                        style=ft.TextStyle(color=ft.Colors.BLACK, size=12),
                    ),
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5)),
                    on_click=on_retry,
                    height=26,
                )
            )

        err_blk = ft.Container(
            content=ft.ExpansionTile(
                title=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.WARNING, size=18) if is_aborted else ft.Icon(ft.Icons.ERROR, size=18),
                        # Row 的主轴是「无界」的: 不给 expand 时 Text 拿不到确定宽度, 只会铺一行然后被裁掉
                        # -> expand=True 让它填满 Row 剩余宽度, 从而按需换行
                        # -> max_lines + overflow: 标题最多 3 行, 超出以省略号收尾 (完整文本在详情里)
                        ft.Text(
                            value=reason,
                            style=ft.TextStyle(color=accent_color),
                            expand=True,
                            max_lines=3,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    spacing=3,
                    # 标题换行后图标不再与首行居中, 统一贴顶更整齐
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                subtitle=ft.Row(
                    controls=subtitle_controls,
                    alignment=ft.MainAxisAlignment.END,
                    spacing=5,
                ),
                dense=True,
                tile_padding=ft.Padding.symmetric(vertical=0, horizontal=5),
                # ExpansionTile 控件可以通过这种方式来自己绘制边框
                # 展开时: https://flet.dev/docs/controls/expansiontile#flet.ExpansionTile.shape
                # 收缩时: https://flet.dev/docs/controls/expansiontile#flet.ExpansionTile.collapsed_shape
                shape=ft.RoundedRectangleBorder(side=ft.BorderSide(width=1, color=accent_color), radius=5),
                collapsed_shape=ft.RoundedRectangleBorder(side=ft.BorderSide(width=1, color=accent_color), radius=5),
                # 错误详情: 用 ft.Text 而不是 ft.Markdown
                # -> Markdown 会把单个换行折叠成空格, 并把 <...> 当作 HTML 吞掉 (异常消息里很常见)
                # -> selectable 允许用户选中复制
                controls=[
                    ft.Text(
                        value=errmsg,
                        selectable=True,
                        size=12,
                    ),
                ],
            ),
            data={"msg_type": "err_msg", "lc_run_id": None},
        )
        return err_blk


class InputCommon:
    """
    输入面板的通用积木层 (无状态)
    """
    @classmethod
    def build_blk_input_panel(cls, tools: ft.Control):
        """
        输入面板

        Note:
        - 渲染输入面板公共的部分组件

        Args:
        - tools: 工具列控件, 由调用方组装

        Return:
        - ft.Container 控件对象
        """
        # 最外层容器
        input_panel = ft.Container(
            ref=EndPoints.input["input_panel"],
            border_radius=10,
            border=ft.Border.all(),
            margin=ft.Margin(left=0, top=0, right=0, bottom=10),
            padding=ft.Padding.symmetric(horizontal=5, vertical=5),
        )
        # 新建的容器 content 必为 None; 保留先清后赋仅为与仓库内其他装配处保持一致
        input_panel.content = None
        input_panel.content = ft.Column(
            controls=[
                cls.build_blk_input_attachments(),
                cls.build_blk_input_textfield(),
                tools,
            ],
            spacing=5,
        )
        return input_panel

    @classmethod
    def build_blk_input_textfield(cls):
        """
        文本输入的 TextField

        Return:
        - ft.TextField 控件对象
        """
        input_textfield = ft.TextField(
            multiline=True,
            min_lines=2,
            max_lines=6,
            expand=True,
            expand_loose=True,
            dense=True,
            content_padding=0,
            text_size=13,
            border=ft.NoInputBorder(),
            ref=EndPoints.input["input_textfield"],
        )
        return input_textfield

    @classmethod
    def build_blk_input_attachment(cls, file_type: str, file_name: str):
        """
        构建一个附件的显示块

        Note:
        删除动作属于附件栏自身生命周期, 故在此绑定 callback_attachment_del

        Args:
        - file_type:    附件类型, 值可以是 file/image/video/audio
        - file_name:    附件名称

        Return:
        - ft.Container 控件对象
        """
        if "_screenshot_" in file_name:
            display_name = f"screenshot_{file_name.split("_screenshot_", 1)[-1][:-4]}"
        attachment = ft.Container(
            ft.Row(
                controls=[
                    ft.Text(value=display_name, size=14),
                    ft.IconButton(
                        icon=ft.Icon(ft.Icons.CANCEL, size=14),
                        height=28, width=28,
                        padding=0,
                        data={"type": file_type, "filename": file_name},
                        on_click=cls.callback_attachment_del,
                    ),
                ],
            ),
            # 数据外部也保留一份, 这样比较好获取
            data={"type": file_type, "filename": file_name},
            bgcolor=ft.Colors.GREY_300,
        )
        return attachment

    @classmethod
    def build_blk_input_attachments(cls):
        """
        位于文本输入上方的附件栏

        Return:
        - ft.Row 控件对象
        """
        input_attachments = ft.Row(
            controls=[],
            ref=EndPoints.input["input_attachments"],
        )
        return input_attachments

    @classmethod
    def callback_attachment_del(cls, e):
        """
        删除指定附件文件
        """
        # 获取文件名
        filename = e.control.data["filename"]
        controls = EndPoints.input["input_attachments"].current.controls
        # 针对截图
        if e.control.data["type"] == "image":
            EndPoints.runtime["app_util_cache"].clipboard_image_del(filename=filename)
            for control in controls:
                if control.data.get("filename") == filename:
                    EndPoints.input["input_attachments"].current.controls.remove(control)
                    break

    @classmethod
    def refresh_input_attachments(cls, session_id: str | None = None):
        """
        获取当前会话中的附件信息并显示到输入框里

        Note:
        与 build_blk_input_attachment / callback_attachment_del 同属附件栏的生命周期,
        故一并放在此处

        Args:
        - session_id: 搜索附件的范围是基于哪个会话ID
        """
        # 先清空所有附件控件
        EndPoints.input["input_attachments"].current.controls.clear()

        # session_id_chat_current / session_id_agent_current 是互斥的关系
        # -> 未显式传入时, 统一交由 MessageUtilsCommon.session_id_current 识别
        if session_id is None:
            session_info = MessageUtilsCommon.session_id_current()
            # 两个都为 None (如停在 docs / settings) 或互斥被破坏: 不渲染附件
            if session_info is None:
                logger.debug("no active session, skip refreshing input attachments.")
                return
            session_id = session_info["session_id"]
        # 截图
        images = EndPoints.runtime["app_util_cache"].clipboard_image_get(session_prefix=session_id)
        if images:
            for filename in images:
                image_blk = cls.build_blk_input_attachment(file_type="image", file_name=filename)
                EndPoints.input["input_attachments"].current.controls.append(image_blk)
            EndPoints.root["page"].update()