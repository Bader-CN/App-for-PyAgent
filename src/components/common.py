import flet as ft
from src.endpoints import EndPoints
from src.utils.logging import logger
from langchain.messages import HumanMessage, AIMessage, ToolMessage


class AlertCommon:
    """
    AlertCommon - 弹窗提示积木 (无状态, 可被任何组件直接 import, 不走 EndPoints)

    准入标准 (二者缺一不可):
    1. 无状态: 不持有实例状态 / ft.Ref, 不读写 EndPoints.chat / EndPoints.settings
    2. 可复用: 同一块 UI 在多处出现, 或已预见会被多处调用

    硬约束:
    - 本文件不得 import 任何 src/components/* 或 src/views/* (保证依赖无环)
    - 触发层级在 page 上 (show_dialog / pop_dialog), 与调用方零状态牵连
    """
    @classmethod
    def alert_model_config_error(cls, message: str):
        """
        弹出模型配置错误提示框

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
        模型列表为空时提示需要先配置模型
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
                    logger.debug(f"Unsupported content block: {i}")
            return markdown_content.strip()
        # 兜底: content 理论上只会是 str / list
        return ""