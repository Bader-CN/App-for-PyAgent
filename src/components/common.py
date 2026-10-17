"""
该模块的引入条件:
1. 不得 import 任何 src.components / view / cores 模块, 确保无环
2. 可复用, 同一块 UI 在多处出现
3. 数据和锚点请查看 src.endpoints.py 文件里的内容; 
   本文件 common.py 里只定义类似积木的组件模块, 不包含复杂的业务逻辑(尽可能独立成孤立的模块)
   -> 所有操作必须局限于在本类自己, 不能跨越别的组件
"""
import flet as ft
from src.endpoints import EndPoints
from src.utils.logging import logger
from langchain.messages import HumanMessage, AIMessage, ToolMessage


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

class MessageCommon:
    """
    针对 LangChain AIMessage / ToolMessage / HumanMessage 的通用处理类
    """
    @classmethod
    def ai_msg_format_content(cls, ai_msg: AIMessage):
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
    
        Args:
        - ai_msg: 单条 AIMessage
    
        Return:
        - AIMessage.content: 类型为 List
        """
        src_aimsg_content = ai_msg.content
        if isinstance(src_aimsg_content, list):
            # 列表里的元素理论上都是 dict, 但旧数据 / 特殊 provider 可能混入纯字符串
            format_aimsg_content = [
                # 每一个 aimsg 都需要转换为一个 dict
                aimsg if isinstance(aimsg, dict) else {"type": "text", "text": aimsg}
                for aimsg in src_aimsg_content
            ]
        else:
            format_aimsg_content = [{"type": "text", "text": src_aimsg_content}]
        # 丢掉空 text 块
        # -> 工具调用轮 / 思考晚于正文到达时, content 里可能混入空串
        # -> 等价于 return [aimsg for aimsg in format_aimsg_content if aimsg.get("type") != "text" or aimsg.get("text")]
        finish_aimsg_content = []
        for aimsg in format_aimsg_content:
            # 空 text 块直接跳过
            if aimsg.get("type") == "text" and not aimsg.get("text"):
                continue
            finish_aimsg_content.append(aimsg)

        return finish_aimsg_content

    @classmethod
    def tool_msg_format_markdown(cls, tool_msg: ToolMessage) -> str:
        """
        重新格式化 ToolMessage 里面的内容, 用于渲染 Markdown

        Note:
        1. 正常情况 content 是内容块列表, 例如 MCP 工具返回:
           [{"type": "text", "text": "## Search Results ..."}]
           -> 直接把列表交给 ft.Markdown, 界面上会渲染出列表的 repr
        2. 普通工具直接返回字符串
        3. 目前只支持 text 块; 图片 / 文件等后续再处理

        Args:
        - tool_msg: 单条 ToolMessage

        Returns:
        - str: 格式化后的文本内容, 用于渲染 Markdown
        """
        # 不是列表: 原样输出 (普通工具直接返回字符串)
        if isinstance(tool_msg.content, str):
            return tool_msg.content
        # 如果是列表, 则继续检查里面的内容
        elif isinstance(tool_msg.content, list):
            markdown_content = ""
            for i in tool_msg.content:
                # 纯字符串元素: 视作 text 块 (content 的类型允许 list[str | dict])
                if isinstance(i, str):
                    markdown_content += i + "\n\n"
                elif isinstance(i, dict) and i.get("type") == "text":
                    markdown_content += (i.get("text") or "") + "\n\n"
                # 其余类型 (图片 / 文件 / 嵌入式资源等) 暂时不支持
                else:
                    logger.warning("ToolMessage has unsupported content blocks!")
                    logger.debug(f"unsupported content block: {i}")
            return markdown_content.strip()
        # 兜底: content 理论上只会是 str / list
        return ""

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
        if session_id is None:
            if EndPoints.runtime["session_id_chat_current"] is not None and EndPoints.runtime["session_id_agent_current"] is not None:
                logger.error("mutex violated: both chat and agent session ids are set")
                return
            elif EndPoints.runtime["session_id_chat_current"] is not None:
                session_id = EndPoints.runtime["session_id_chat_current"]
            elif EndPoints.runtime["session_id_agent_current"] is not None:
                session_id = EndPoints.runtime["session_id_agent_current"]
            else:
                # 两个都为 None: 尚未定位到任何会话 (如停在 docs / settings)
                logger.debug("no active session, skip refreshing input attachments.")
                return
        # 截图
        images = EndPoints.runtime["app_util_cache"].clipboard_image_get(session_prefix=session_id)
        if images:
            for filename in images:
                image_blk = cls.build_blk_input_attachment(file_type="image", file_name=filename)
                EndPoints.input["input_attachments"].current.controls.append(image_blk)
            EndPoints.root["page"].update()