import json
import uuid
import asyncio
import flet as ft
from typing import List, Dict, Any
from src.endpoints import EndPoints
from src.components.common import AlertCommon
from src.components.common import MessageCommon
from src.utils.logging import logger
from langchain.messages import SystemMessage, HumanMessage, AIMessage, RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES


class ChatBody:
    """
    对话消息
    """
    @classmethod
    def build_blk_err_msg(cls, reason: str, status="error", errmsg=None):
        """
        构建一个显示错误的消息块

        Args:
        - reason:   错误的原因概述, 中止场景为翻译文案
        - status:   错误的状态, 值可以是 error / aborted
        - errmsg:   错误信息详情, 不传时中止场景用固定文案 / 错误场景复用 reason
        """
        if status == "aborted" and errmsg is None:
            errmsg = EndPoints.runtime["app_util_lang"].translate(key="request_was_aborted_desc")
        elif errmsg is None:
            # 错误场景的 reason 本身就是异常首行, 直接复用为详情 (缺省而不是塞一句英文占位)
            errmsg = reason

        err_blk = ft.Container(
            content=ft.ExpansionTile(
                title=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.WARNING, size=18) if status == "aborted" else ft.Icon(ft.Icons.ERROR, size=18),
                        ft.Text(value=reason, style=ft.TextStyle(color=ft.Colors.ORANGE if status == "aborted" else ft.Colors.RED)),
                    ],
                    spacing=3,
                ),
                subtitle=ft.Row(
                    controls=[
                        # 复制按钮: 用于复制错误详情
                        ft.TextButton(
                            content=ft.Text(
                                value=EndPoints.runtime["app_util_lang"].translate(key="copy"),
                                style=ft.TextStyle(color=ft.Colors.BLACK, size=12),
                            ),
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5)),
                            height=26,
                        ),
                        # 重试按钮: 用于重新发送消息
                        ft.TextButton(
                            content=ft.Text(
                                value=EndPoints.runtime["app_util_lang"].translate(key="retry"),
                                style=ft.TextStyle(color=ft.Colors.BLACK, size=12),
                            ),
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5)),
                            on_click=cls.callback_msg_retry,
                            height=26,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    spacing=5,
                ),
                dense=True,
                tile_padding=ft.Padding.symmetric(vertical=0, horizontal=5),
                # ExpansionTile 控件可以通过这种方式来自己绘制边框
                # 展开时: https://flet.dev/docs/controls/expansiontile#flet.ExpansionTile.shape
                # 收缩时: https://flet.dev/docs/controls/expansiontile#flet.ExpansionTile.collapsed_shape
                shape=ft.RoundedRectangleBorder(side=ft.BorderSide(width=1, color=ft.Colors.ORANGE if status == "aborted" else ft.Colors.RED), radius=5),
                collapsed_shape=ft.RoundedRectangleBorder(side=ft.BorderSide(width=1, color=ft.Colors.ORANGE if status == "aborted" else ft.Colors.RED), radius=5),
                # 错误详情
                controls=[
                    ft.Markdown(
                        value=errmsg,
                        selectable=True, # 允许用户选中复制
                        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                        code_theme=ft.MarkdownCodeTheme.GITHUB,
                    ),
                ],
            ),
            data={"msg_type": "err_msg", "lc_run_id": None},
        )
        return err_blk
    
    @classmethod
    def build_blk_user_msg(cls, user_msg: List[Dict], user_msg_id=None):
        """
        构建一个 User 消息块, 格式参考了如下文档
        https://docs.langchain.com/oss/python/langchain/messages#multimodal

        Args:
        - user_msg:     多模态的用户消息内容, 参考了 HumanMessage 的格式: [{"type": "text", "text": ***}]
        - user_msg_id:  用户消息的唯一标识符, 如果 user_msg 的数据类型为 HumanMessage, 则忽略传入的值, 否则不传则会自动生成

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
                                    on_click=cls.callback_msg_retry,
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
        logger.warning(user_msg)
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
    def build_blk_ai_text_finally(cls, text="", lc_run_id=None):
        """
        构建一个 AI 消息块 (仅针对最后的输出内容)

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
                                content=ft.IconButton(icon=ft.Icons.AUTORENEW, icon_size=14, padding=0, on_click=cls.callback_msg_retry),
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
    async def msg_aborted_save(cls, chat_session_id: str):
        """
        中止后补写已经输出的信息, 把已经流式输出并渲染过的内容保留进 checkpointer

        Note:
        1.checkpointer 是「每个 super-step 一次」的进度记录, 不是事务
        2.langgraph 的图在 abort() 时取消了 in-flight 的 pull, 导致:
          -> AIMessage 从未落库 (正在跑的 model node 被取消, 该 super-step 从不 after_tick)
          -> AIMessage 被丢掉了 (库里于是只剩 source="input")
          -> 即仅剩下 HumanMessage
        3.中止点可能落在 tool 阶段, 此时 model node 的 super-step 已经落库
          -> AIMessage 里包含 reasoning + tool_call, finish_reason="tool_calls"
          -> 这些半成品留着会让下一轮把未完成的工具再跑一次, 故必须重写成本轮的最终形态
        4.重写方式
          -> 用 aimsgs 重建一条 stop 形状的消息, 并让它「顶掉」本轮那条半成品
          -> id 复用半成品的 id, add_messages 才会做原地替换; 改用新 id 会被追加到末尾
          -> 本轮尚无 AI 落库时 (中止发生在首次 model 调用前) 没有可复用的 id, 才新建
        5.tool_calls 必须留空 (实测: 填上会让这次 aupdate_state 直接抛 KeyError)
          -> 异常被下面的 except 吞掉 => 补写静默失效, 中止内容不进库
          -> 机理与验证见 ai_msg 处的注释, 以及 test/sample/abort_save_order_and_tool_calls.py
        """
        # 基于 session_id 来生成 config
        config = {"configurable": {"thread_id": chat_session_id}}

        # 利用空图来读取数据 (与 chat_list.session_msgs_render / callback_msg_retry 逻辑一致)
        lc_agents = EndPoints.runtime["lc_agents"]
        if lc_agents.state_graph_chat is None:
            lc_agents.state_graph_chat_update()
        snapshot = await lc_agents.state_graph_chat.aget_state(config)
        messages = snapshot.values.get("messages", [])

        # 本轮已落库的流内 message (aimsgs 里的 lc_run_id == 对应 AIMessage 的 id)
        # -> round_ids:    本轮所有流式块的 lc_run_id 集合 (reasoning/text/tool_call)
        # -> obsolete_ids: 过时的, 本轮在库里留下的、需要被删除重建的半成品 AIMessage 的 id
        round_ids = {msg.get("lc_run_id") for msg in EndPoints.tmp_msgs[chat_session_id]["aimsgs"]}
        obsolete_ids = [m.id for m in messages if isinstance(m, AIMessage) and m.id in round_ids]

        # 按流式顺序重新整理已累积的内容块 (形状与 langchain 的 v1 protocol block 对齐)
        # 注意: 这里取 aimsgs 全量, 不跳过已落库的内容
        # -> 这里只负责重建, 之后会基于 obsolete_ids 来删除过期数据
        content = []
        for msg in EndPoints.tmp_msgs[chat_session_id]["aimsgs"]:
            if msg["type"] == "reasoning":
                content.append({"type": "reasoning", "reasoning": msg["reasoning"]})
            elif msg["type"] == "text":
                content.append({"type": "text", "text": msg["text"]})
            elif msg["type"] == "tool_call":
                # aimsgs 里 args 是「逐 chunk 拼接的字符串」, 而 protocol block 要求是 dict
                # -> 中止点可能落在参数生成的中途 -> 拼接结果不是合法 JSON
                # -> 此时原样保留字符串
                raw_args = msg.get("args") or ""
                try:
                    args_parsed = json.loads(raw_args) if raw_args else {}
                except json.JSONDecodeError:
                    args_parsed = raw_args
                content.append({
                    "type": "tool_call",
                    "id": msg.get("tool_call_id"),
                    "name": msg.get("name"),
                    "args": args_parsed,
                })
        # 什么都没有: 不写, 避免向历史里塞空消息
        if not content:
            logger.warning(f"nothing to save after abort: session_id={chat_session_id}")
            return
        
        # 组装 AIMessage
        # response_metadata 的两个字段是为对齐正常流程的形态:
        # -> output_version="v1":  声明 content 已是 v1 protocol block, 避免 content_blocks 属性再用 provider 规则二次翻译
        # -> finish_reason="stop": 标记本轮已收尾 (渲染侧据此归入「最终结果」)
        ai_msg = AIMessage(
            content=content,
            tool_calls=[],
            id=obsolete_ids[0] if obsolete_ids else str(uuid.uuid1()),
            response_metadata={"finish_reason": "stop", "output_version": "v1"},
        )

        # 重写本轮已落库的中间结果: 复用 id 的那条被原地替换, 其余多余的一并删除
        try:
            updates = [RemoveMessage(id=i) for i in obsolete_ids]
            updates.append(ai_msg)
            await EndPoints.runtime["lc_agents"].agent_chat.aupdate_state(
                config,
                {"messages": updates},
                # as_node 必须显式指定 "model"
                # 此时 checkpoint 的 versions_seen 里可能已有 model/tools 多个节点, 交给 LangGraph 自行推断会抛 InvalidUpdateError: Ambiguous update
                # https://docs.langchain.com/oss/python/langgraph/checkpointers#update-state
                # https://docs.langchain.com/oss/python/langgraph/use-time-travel#from-a-specific-node
                as_node="model",
            )
            logger.warning(f"aborted content saved: session_id={chat_session_id}, replaced={len(obsolete_ids)}")
        except Exception as e:
            # 补写失败不能连累收尾流程 (否则发送按钮会一直停在 STOP 图标上)
            logger.exception(e)

    @classmethod
    async def msg_error_mark(cls, chat_session_id: str, astream, e: Exception):
        """
        消费流异常时的后处理
        每个 consume_*** 的 except 捕获的异常均在这里统一处理

        Note:
        首个错误优先: 
        - status 已是 error/aborted 时只 abort 直接返回, reason 保留第一个异常
        - 防止多个消费者在同一轮各自标记、各自渲染错误块

        Args:
        - chat_session_id:  对应会话ID, 用于定位 EndPoints.tmp_msgs 以标记 status 并写入 reason
        - astream:          本轮运行的句柄, 调用 abort() 关闭所有 channel, 让 gather 干净返回以进入收尾
        - e:                本次异常的 Exception
        """
        # 检查当前状态是否已经处于 error / aborted
        # 如果是则直接暂停流式输出, 并直接返回 (防止重复处理)
        if EndPoints.tmp_msgs[chat_session_id]["status"] in ["error", "aborted"]:
            logger.warning(f"consume failed after status was already marked: {e}")
            await astream.abort()
            return

        # 首次调用异常, 记录异常并终止流式输出
        logger.exception(e)
        EndPoints.tmp_msgs[chat_session_id]["status"] = "error"
        err_line = str(e).strip().splitlines()
        EndPoints.tmp_msgs[chat_session_id]["reason"] = err_line[0] if err_line else type(e).__name__
        await astream.abort()

    @classmethod
    async def msg_title_summary(cls, chat_session_id: str):
        """
        消息摘要处理函数

        Args:
        - chat_session_id:  对应会话ID
        """
        # 基于 "会话ID" 获取所有的历史消息
        config = {"configurable": {"thread_id": chat_session_id}}
        if EndPoints.runtime["lc_agents"].state_graph_chat is None:
            EndPoints.runtime["lc_agents"].state_graph_chat_update()
        snapshot = await EndPoints.runtime["lc_agents"].state_graph_chat.aget_state(config)
        messages = snapshot.values.get("messages", [])

        # 获取指定类型的 messages
        last_user_msg = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
        last_ai_msg = next((m for m in reversed(messages) if isinstance(m, AIMessage) and m.text), None)
        if last_user_msg and last_ai_msg:
            # 拼接消息 - 最后一条 HumanMessage 的文本部分 + AIMessage 最终输出部分
            summary_text = f"User Question: {last_user_msg}; AI Response: {last_ai_msg}"
            # 组装消息
            summary_msgs = [
                SystemMessage(f"You are a helpful assistant, please summarize the conversation in {EndPoints.runtime["app_language"]}, as few as possible under 10 words."),
                HumanMessage(summary_text),
            ]

        # 调用模型并总结标题
        if EndPoints.runtime["lc_agents"].agent_summary is None:
            EndPoints.runtime["lc_agents"].agent_summary_update()

        # 确保话题总结模型不为 None
        if EndPoints.runtime["lc_agents"].agent_summary is not None:
            response = EndPoints.runtime["lc_agents"].agent_summary.invoke(summary_msgs)
            summary_title = str(response.text)
            # 渲染界面
            sessions = EndPoints.chat["chat_list"].current.controls
            for session in sessions:
                if session.data.get("session_id") == chat_session_id:
                    session.title = ft.Text(summary_title)
                    session.data["title"] = summary_title
                    if chat_session_id == EndPoints.runtime["session_id_chat_current"]:
                        EndPoints.chat["chat_header"].current.content.controls[0].content.value = summary_title
                    break
            EndPoints.root["page"].update()
            # 保持数据 (sessions 数据类型为 list)
            sessions = EndPoints.runtime["app_util_filedata"].data_read(data_type="sort_chat")
            for idx, session_dict in enumerate(sessions):
                if session_dict.get("session_id") == chat_session_id:
                    sessions[idx]["title"] = summary_title
                    EndPoints.runtime["app_util_filedata"].data_save(data_type="sort_chat", data_cont=sessions)
                    break

    @classmethod
    async def msg_update_stream(cls, user_msg):
        """
        以异步的方式更新流式消息

        Args:
        - user_msg:     多模态的用户消息内容, 格式为 [{"type": "text", "text": ***}]
        """
        # 封装 HumanMessage
        human_msg_id = str(uuid.uuid1())
        human_msg = HumanMessage(content=user_msg, id=human_msg_id)

        # 获取当前的 session_id, 用于后续比较会话是否切换
        chat_session_id = EndPoints.runtime["session_id_chat_current"]

        # 清空之前的会话缓存 (仅保留最新一轮)
        # -> 如果 click_count != rendered_click_count, 则证明流式消息中途被打断了, 需要重新补录
        # -> 这两个值会在每次触发新会话时重置为1
        # -> tmp_msgs_init 是「整体替换」, 每一轮持有的是不同的 dict 对象
        EndPoints.runtime["app_util_cache"].tmp_msgs_init(session_id=chat_session_id, status="start")
        # 记录本轮的身份标记 (dict 对象身份, 收尾时比对)
        round_msgs = EndPoints.tmp_msgs[chat_session_id]

        # 获取 Agent 对象
        if EndPoints.runtime["lc_agents"].agent_chat is None:
            EndPoints.runtime["lc_agents"].agent_chat_update()
        if EndPoints.runtime["lc_agents"].agent_chat is None:
            AlertCommon.alert_model_config_none()
            return
        agent = EndPoints.runtime["lc_agents"].agent_chat

        # Agent 异步调用
        try:
            astream = await agent.astream_events(
                {"messages": [human_msg,],}, 
                version="v3", 
                config={"configurable": {"thread_id": chat_session_id}},
            )
        # 模型没有配置时触发
        except Exception as e:
            AlertCommon.alert_model_config_error(message=str(e))
            EndPoints.chat["chat_input_send_btn"].current.icon = ft.Icons.SEND
            EndPoints.root["page"].update()
            return
                    
        async def consume_messages():
            """
            逐条 message 消费三个投影 (每条 message 的 reasoning/text/tool_calls)
            message.*** 投影是每条 message 私有的, 需要放在循环里并发 gather
            """
            # 注意: try 必须包住整个 async for
            # -> 投影/通道出错时, 异常是在 __anext__ (即 async for 本身) 抛出的, 只包循环体会漏掉
            try:
                async for message in astream.messages:
                    # 状态 = error/aborted, 则直接 abort() 来关闭所有 channel 让 gather 干净返回
                    if EndPoints.tmp_msgs[chat_session_id]["status"] in ["error", "aborted"]:
                        logger.warning(f"stream aborted: session_id={chat_session_id}")
                        await astream.abort()
                        return
                    # 获取 langchain 执行的唯一id
                    lc_run_id = message.message_id
                    # 三个 async for 同时驱动共享一个pump(水泵, AsyncGraphRunStream 单飞锁)
                    # 各投影的 delta 到达时立即被对应任务实时消费
                    # https://docs.langchain.com/oss/python/langchain/event-streaming#multiple-projections
                    await asyncio.gather(
                        cls.consume_reasoning(message=message, chat_session_id=chat_session_id, lc_run_id=lc_run_id, astream=astream), 
                        cls.consume_tool_calls_args(message=message, chat_session_id=chat_session_id, lc_run_id=lc_run_id, astream=astream), 
                        cls.consume_text(message=message, chat_session_id=chat_session_id, lc_run_id=lc_run_id, astream=astream),
                    )
                    # 状态 = error/aborted
                    # 走到这里说明本轮 message 的某个消费者在 delta 级检测到中止并 abort() 了
                    # -> 由于 abort() 已在被调用过了, 因此这里只记录日志
                    # -> 和上面那个 return 二者互斥 => 每次中止只打一条
                    if EndPoints.tmp_msgs[chat_session_id]["status"] in ["error", "aborted"]:
                        EndPoints.runtime["app_util_cache"].tmp_msgs_state_update(
                            session_id=chat_session_id, 
                            status=EndPoints.tmp_msgs[chat_session_id]["status"], 
                            reason=EndPoints.tmp_msgs[chat_session_id]["reason"],
                        )
                        logger.warning(f"stream aborted: session_id={chat_session_id}")
                        return
            except Exception as e:
                # 本轮 message 的消费出错: 统一标记 error + 中止本轮流式输出
                await cls.msg_error_mark(chat_session_id=chat_session_id, astream=astream, e=e)

        # 并发驱动两个独立投影, 共享一个pump(水泵)
        # - consume_messages           : astream.messages (每条 message 的 reasoning/text/tool_calls)
        # - consume_tool_calls_output  : astream.tool_calls (Tool Call 的执行生命周期, 用于获取结果, 只允许订阅一次)
        try:
            await asyncio.gather(consume_messages(), cls.consume_tool_calls_output(astream=astream, chat_session_id=chat_session_id))
        except Exception as e:
            logger.exception(e)

        # 身份核对: 本轮是否已被后来的轮次顶掉
        # -> tmp_msgs_init 整体替换 dict, 所以后来那轮持有的是另一个对象
        # -> 不等 => 用户在本轮期间又发了一轮 / 连点了两次重试
        # -> 此时必须整体放弃收尾, 否则会:
        #    (a) 把后来那轮的 status 写成 stop
        #    (b) 按后来那轮的 aimsgs 去切面板 (把它的在飞块搬进 AI Summary)
        #    (c) 重复补写落库 / 重复渲染一个错误块 (实测: 错误块出现 2 次)
        # -> 会话条目被删时 .get() 得 None, 同样在此返回
        if EndPoints.tmp_msgs.get(chat_session_id) is not round_msgs:
            logger.warning(f"this round was superseded, skip finalize. session_id={chat_session_id}")
            return

        # 意外终止时的渲染/后处理 (error/aborted)
        # 1.补写已输出的内容至数据库 (已流式渲染的内容只存在于 tmp_msgs 中)
        # 2.错误块渲染: 只有 error 在这里做
        # -> aborted 已在停止按钮回调里即时渲染 (见 ChatInput.callback_send_user_msg)
        # -> 那里是同步回调, 不用等 gather 返回, 避免工具静默期干等几秒
        if EndPoints.tmp_msgs[chat_session_id]["status"] in ["error", "aborted"]:
            await cls.msg_aborted_save(chat_session_id=chat_session_id)
            # 持久化本轮的中止/错误状态: 供重启后渲染警告块
            EndPoints.runtime["app_util_cache"].tmp_msgs_state_update(
                session_id=chat_session_id,
                status=EndPoints.tmp_msgs[chat_session_id]["status"],
                reason=EndPoints.tmp_msgs[chat_session_id]["reason"],
            )
            # 确保是本次会话
            if EndPoints.tmp_msgs[chat_session_id]["status"] == "error" and chat_session_id == EndPoints.runtime["session_id_chat_current"]:
                EndPoints.chat["chat_body"].current.content.controls.append(cls.build_blk_err_msg(
                    reason=EndPoints.tmp_msgs[chat_session_id]["reason"],
                    status="error",
                ))
                EndPoints.root["page"].update()
        # 正常结束
        else:
            # 消息处理完毕
            EndPoints.tmp_msgs[chat_session_id]["status"] = "stop"
            EndPoints.runtime["app_util_cache"].tmp_msgs_state_del(session_id=chat_session_id)

            # 重新整理本次会话的消息
            if chat_session_id == EndPoints.runtime["session_id_chat_current"]:
                chat_number = len(EndPoints.tmp_msgs[chat_session_id]["aimsgs"])
                need_finally = True  # 最后一条是否需要替换为 blk_ai_finally
                if chat_number > 2:
                    blk_ai_finally = cls.build_blk_ai_text_finally(
                        text=EndPoints.tmp_msgs[chat_session_id]["aimsgs"][-1].get("text"),
                        lc_run_id=EndPoints.tmp_msgs[chat_session_id]["aimsgs"][-1].get("lc_run_id"),
                    )
                    blk_ai_summary = cls.build_blk_ai_summary()
                    controls = EndPoints.chat["chat_body"].current.content.controls[-chat_number:-1]
                    for control in controls:
                        blk_ai_summary.content.controls[0].controls.append(control)
                    EndPoints.chat["chat_body"].current.content.controls = EndPoints.chat["chat_body"].current.content.controls[:-chat_number]
                    EndPoints.chat["chat_body"].current.content.controls.append(blk_ai_summary)
                    EndPoints.chat["chat_body"].current.content.controls.append(blk_ai_finally)
                    need_finally = False
                elif need_finally and EndPoints.tmp_msgs[chat_session_id]["aimsgs"][-1].get("text"):
                    blk_ai_finally = cls.build_blk_ai_text_finally(
                        text=EndPoints.tmp_msgs[chat_session_id]["aimsgs"][-1].get("text"),
                        lc_run_id=EndPoints.tmp_msgs[chat_session_id]["aimsgs"][-1].get("lc_run_id"),
                    )
                    EndPoints.chat["chat_body"].current.content.controls[-1] = blk_ai_finally
                    
                # 混动到底部 & 刷新界面
                await EndPoints.chat["chat_body"].current.content.scroll_to(offset=-1, duration=0)
                EndPoints.root["page"].update()

            # 将发送按钮的图标替换为 ft.Icons.SEND 状态
            if chat_session_id == EndPoints.runtime["session_id_chat_current"]:
                EndPoints.chat["chat_input_send_btn"].current.icon = ft.Icons.SEND
                EndPoints.root["page"].update()

            # 执行标题总结
            sessions = EndPoints.chat["chat_list"].current.controls
            for session in sessions:
                if session.data.get("session_id") == chat_session_id and session.data.get("title") == EndPoints.runtime["app_util_lang"].translate(key="new_session"):
                    EndPoints.root["page"].run_task(cls.msg_title_summary, chat_session_id)
                    break

    @classmethod
    def msg_update_rebuild(cls, msgs: list[Dict]):
        """
        补录缺失的流式消息, 用于会话被切换的场景

        Args:
        - msgs: 消息列表, 用于补全缺失的消息
        """
        # 记录消息总数, 用于判断如何渲染思考模块
        total_msgs = len(msgs)
        # 没有历史消息块 或 存在历史消息块, 但最后一个消息块是 user_msg
        if len(EndPoints.chat["chat_body"].current.content.controls) == 0 \
            or EndPoints.chat["chat_body"].current.content.controls[-1].data.get("msg_type") == "user_msg":
            for idx, msg_dict in enumerate(msgs, start=1):
                if msg_dict["type"] == "reasoning" and idx != total_msgs:   # 该思考块非最后一个 (不需要副标题)
                    EndPoints.chat["chat_body"].current.content.controls.append(cls.build_blk_ai_reasoning(lc_run_id=msg_dict["lc_run_id"]))
                    EndPoints.chat["chat_body"].current.content.controls[-1].content.controls[0].value = msg_dict["reasoning"]
                elif msg_dict["type"] == "reasoning" and idx == total_msgs: # 该思考块是最后一个 (需要副标题)
                    EndPoints.chat["chat_body"].current.content.controls.append(cls.build_blk_ai_reasoning(lc_run_id=msg_dict["lc_run_id"], blk_status="start"))
                    EndPoints.chat["chat_body"].current.content.controls[-1].content.subtitle.controls[0].value = msg_dict["reasoning"]
                    EndPoints.chat["chat_body"].current.content.controls[-1].content.controls[0].value = msg_dict["reasoning"]
                elif msg_dict["type"] == "tool_call":
                    EndPoints.chat["chat_body"].current.content.controls.append(cls.build_blk_ai_tool_call(args_dict=msg_dict, lc_run_id=msg_dict["lc_run_id"]))
                elif msg_dict["type"] == "text":
                    EndPoints.chat["chat_body"].current.content.controls.append(cls.build_blk_ai_text(lc_run_id=msg_dict["lc_run_id"]))
                    EndPoints.chat["chat_body"].current.content.controls[-1].content.value = msg_dict["text"]
        # 存在历史消息块, 但最后一个消息块不是 user_msg
        else:
            last_container = EndPoints.chat["chat_body"].current.content.controls[-1]
            last_msg_type = last_container.data["msg_type"]
            last_lc_run_id = last_container.data["lc_run_id"]
            # 倒叙比对 - 定位 last_container 具体对应的消息
            for idx, msg_dict in enumerate(reversed(msgs), start=1):
                # 不用创建新的消息块: 因为最后一个消息块就是当前消息块
                if idx == 1 and msg_dict["type"] == last_msg_type and msg_dict["lc_run_id"] == last_lc_run_id:
                    if msg_dict["type"] == "reasoning":
                        EndPoints.chat["chat_body"].current.content.controls[-1].content.subtitle.controls[0].value = msg_dict["reasoning"]
                        EndPoints.chat["chat_body"].current.content.controls[-1].content.controls[0].value = msg_dict["reasoning"]
                    elif msg_dict["type"] == "tool_call":
                        EndPoints.chat["chat_body"].current.content.controls.append(cls.build_blk_ai_tool_call(args_dict=msg_dict, lc_run_id=msg_dict["lc_run_id"]))
                    elif msg_dict["type"] == "text":
                        EndPoints.chat["chat_body"].current.content.controls[-1].content.value = msg_dict["text"]
                # 需要新建消息块: 因为 idx !=1, 因此 last_container 和 msgs 之间存在差异
                elif msg_dict["type"] == last_msg_type and msg_dict["lc_run_id"] == last_lc_run_id:
                    for msg_dict in msgs[-idx+1:]:
                        if msg_dict["type"] == "reasoning":
                            EndPoints.chat["chat_body"].current.content.controls.append(cls.build_blk_ai_reasoning(lc_run_id=msg_dict["lc_run_id"], blk_status="start"))
                            EndPoints.chat["chat_body"].current.content.controls[-1].content.subtitle.controls[0].value = msg_dict["reasoning"]
                            EndPoints.chat["chat_body"].current.content.controls[-1].content.controls[0].value = msg_dict["reasoning"]
                        elif msg_dict["type"] == "tool_call":
                            EndPoints.chat["chat_body"].current.content.controls.append(cls.build_blk_ai_tool_call(args_dict=msg_dict, lc_run_id=msg_dict["lc_run_id"]))
                        elif msg_dict["type"] == "text":
                            EndPoints.chat["chat_body"].current.content.controls.append(cls.build_blk_ai_text(lc_run_id=msg_dict["lc_run_id"]))
                            EndPoints.chat["chat_body"].current.content.controls[-1].content.value = msg_dict["text"]
    
    @classmethod
    async def consume_tool_calls_output(cls, astream, chat_session_id):
        """
        获取 Tool Call 的运行结果 astream.tool_calls

        Args:
        - astream:          本轮运行的句柄, 调用 abort() 关闭所有 channel, 让 gather 干净返回以进入收尾
        - chat_session_id:  对应的会话ID, 用于标识这是哪个会话调用的工具
        """
        # 兜底: try 必须包住整个 async for (理由同 consume_messages)
        try:
            async for call in astream.tool_calls:
                # 需要不断拉取来获取结果, 否则消息为空
                async for delta in call.output_deltas:
                    # 状态 = error/aborted 时立即 abort() 关闭所有 channel, 让 gather 干净返回以执行收尾逻辑
                    if EndPoints.tmp_msgs[chat_session_id]["status"] in ["error", "aborted"]:
                        await astream.abort()
                        return
                # drain 结束后的检查点 (工具已跑完 / 工具本就无输出)
                # -> 工具没有 output_deltas 时, 上面那个内层检查点一次都跑不到
                # -> 中止恰好落在 drain 的最后一段时同样漏检
                # -> 漏检 => 一路走到下面的回填, 再回到外层等下一条 call => 又卡住
                if EndPoints.tmp_msgs[chat_session_id]["status"] in ["error", "aborted"]:
                    await astream.abort()
                    return

                # 判断会话状态的标记位
                # is_current: 面板当前展示的就是本次流所属的会话
                # is_synced:  相等 => 面板尾部就是本轮的块, 可原地叠加 / 不相等 => 面板被重建过, 本轮不碰界面 (只累数据, 由 ChatList.session_msgs_render 补录)
                is_current = chat_session_id == EndPoints.runtime["session_id_chat_current"]
                is_synced = EndPoints.tmp_msgs[chat_session_id]["rendered_click_count"] == EndPoints.tmp_msgs[chat_session_id]["click_count"]

                # 获取 Tool Call 的结果, tool_out 可以获取如下信息:
                # -> logger.debug(tool_out.content)
                # -> logger.debug(tool_out.name)
                # -> logger.debug(tool_out.tool_call_id)
                tool_out = call.output
                tool_err = call.error

                # 错误处理
                if tool_err is not None:
                    logger.error(f"[tool_error] {tool_err}")

                # 工具还没结束就被中止: abort() 的 aclose 路径不设 error, 投影以 StopAsyncIteration 正常收尾
                # -> call.output 恒为 None, 没有可回填的结果, 直接跳过
                # -> 否则下面 tool_out.tool_call_id 会抛 AttributeError
                elif tool_out is None:
                    continue

                # 正常情况
                else:
                    for idx, msg in enumerate(reversed(EndPoints.tmp_msgs[chat_session_id]["aimsgs"]), start=1):
                        # 更新数据
                        if msg["type"] == "tool_call" and msg["tool_call_id"] == tool_out.tool_call_id:
                            tool_markdown = MessageCommon.tool_msg_format_markdown(tool_msg=tool_out)
                            msg["tool_result"] = tool_markdown
                            # 渲染界面 (面板尾部就是本轮的块)
                            if is_current and is_synced:
                                EndPoints.chat["chat_body"].current.content.controls[-idx].content.controls = ft.Markdown(value=tool_markdown)
                                EndPoints.root["page"].update()
                            break
        except Exception as e:
            await cls.msg_error_mark(chat_session_id=chat_session_id, astream=astream, e=e)

    @classmethod
    async def consume_tool_calls_args(cls, message, chat_session_id, lc_run_id, astream):
        """
        消费 Tool Call 流数据 (异步) - 仅针对 LLM 输出的参数

        chunk 的消息格式为如下, 该 id 实际对应的是 AIMessage 里的 id, 在 ToolMessage 里应该叫 tool_call_id
        {'type': 'tool_call_chunk', 'id': 'N2cbJBXj9aC6rpUQKuJLhyvb3gozKccF', 'name': 'ls', 'args': '', 'index': 0}
        {'type': 'tool_call_chunk', 'id': 'fCREhQB3v72HT2izIMjsXhoto7KYrSov', 'name': 'write_file', 'args': '', 'index': 0}
        {'type': 'tool_call_chunk', 'id': 'gOTG5jAF8M9ZZPX9lJOc3aFwtv7ANDw8', 'name': 'ls', 'args': '', 'index': 0}

        Args:
        - message:          astream.messages 中的单个 delta
        - char_session_id:  对应的会话ID, 用于标识这是哪个会话调用的工具
        - lc_run_id:        langchain 运行时的唯一id
        - astream:          本轮运行的句柄, 出错时需要用它的 abort() 中止本轮
        """
        # 兜底: try 必须包住整个 async for (理由同 consume_messages)
        try:
            async for chunk in message.tool_calls:
                # 状态 = error/aborted 时立即 abort() 关闭所有 channel, 让 gather 干净返回以执行收尾逻辑
                # 中止日志统一在 consume_messages 处输出, 此处不重复打印
                if EndPoints.tmp_msgs[chat_session_id]["status"] in ["error", "aborted"]:
                    await astream.abort()
                    return
                
                # 判断会话状态的标记位
                # is_current: 面板当前展示的就是本次流所属的会话
                # is_synced:  相等 => 面板尾部就是本轮的块, 可原地叠加 / 不相等 => 面板被重建过, 本轮不碰界面 (只累数据, 由 ChatList.session_msgs_render 补录)
                is_current = chat_session_id == EndPoints.runtime["session_id_chat_current"]
                is_synced = EndPoints.tmp_msgs[chat_session_id]["rendered_click_count"] == EndPoints.tmp_msgs[chat_session_id]["click_count"]

                # 标记位: 状态 = tool_call
                if EndPoints.tmp_msgs[chat_session_id]["status"] != "tool_call":
                    EndPoints.tmp_msgs[chat_session_id]["status"] = "tool_call"
                    # 渲染界面 (非切换重建) & 上一个控件是思考控件
                    # -> 删掉副标题 (要确保 EndPoints.tmp_msgs[chat_session_id]["aimsgs"] 不为空)
                    # -> 思考中 更新为 思考完成
                    if is_current and is_synced and EndPoints.tmp_msgs[chat_session_id]["aimsgs"] and EndPoints.tmp_msgs[chat_session_id]["aimsgs"][-1]["type"] == "reasoning":
                        EndPoints.chat["chat_body"].current.content.controls[-1].content.subtitle = None
                        EndPoints.chat["chat_body"].current.content.controls[-1].content.title.controls[1].value = EndPoints.runtime["app_util_lang"].translate(key="reason_finish")
                # 每个 tool_call 只建立一个 tgt_tool_msg
                # 基于 tool_call_id 来进行唯一标识, tgt_tool_msg 默认为 None
                tgt_tool_msg = None
                for msg in reversed(EndPoints.tmp_msgs[chat_session_id]["aimsgs"]):
                    if msg["type"] == "tool_call" and msg["tool_call_id"] == chunk.get("id"):
                        tgt_tool_msg = msg
                        break
                # 没有 tgt_tool_msg: 首次创建
                if tgt_tool_msg is None:
                    tgt_tool_msg = {"type": "tool_call", "tool_call_id": chunk.get("id"), "lc_run_id": lc_run_id}
                    EndPoints.tmp_msgs[chat_session_id]["aimsgs"].append(tgt_tool_msg)
                    # 渲染界面 (非切换重建)
                    if is_current and is_synced:
                        EndPoints.chat["chat_body"].current.content.controls.append(cls.build_blk_ai_tool_call(args_dict=tgt_tool_msg, lc_run_id=lc_run_id))
                # 基于 chunk.get("id") 来更新 数据 / Flet 控件
                for idx, msg in enumerate(reversed(EndPoints.tmp_msgs[chat_session_id]["aimsgs"]), start=1):
                    if msg["type"] == "tool_call" and msg["tool_call_id"] == chunk.get("id"):
                        for k, v in chunk.items():
                            if k != "type":
                                tgt_tool_msg[k] = v
                        # 渲染界面 (非切换重建)
                        if is_current and is_synced:
                            EndPoints.chat["chat_body"].current.content.controls[-idx] = cls.build_blk_ai_tool_call(args_dict=tgt_tool_msg, lc_run_id=lc_run_id)
                        break
                # 渲染界面 (面板尾部就是本轮的块)
                if is_current and is_synced:
                    await EndPoints.chat["chat_body"].current.content.scroll_to(offset=-1, duration=0)
                    EndPoints.root["page"].update()
        except Exception as e:
            await cls.msg_error_mark(chat_session_id=chat_session_id, astream=astream, e=e)

    @classmethod
    async def consume_reasoning(cls, message, chat_session_id, lc_run_id, astream):
        """
        消费 reasoning 流数据 (异步)

        Args:
        - message:          astream.messages 中的单个 delta
        - char_session_id:  对应的会话ID, 用于标识这是哪个会话调用的工具
        - lc_run_id:        langchain 运行时的唯一id
        - astream:          本轮运行的句柄, 中止时需要用它的 abort() 取消 in-flight pull
        """
        # 兜底: try 必须包住整个 async for (理由同 consume_messages)
        try:
            async for delta in message.reasoning:
                # 状态 = error/aborted 时立即 abort() 关闭所有 channel, 让 gather 干净返回以执行收尾逻辑
                # 中止日志统一在 consume_messages 处输出, 此处不重复打印
                if EndPoints.tmp_msgs[chat_session_id]["status"] in ["error", "aborted"]:
                    await astream.abort()
                    return
                
                # 判断会话状态的标记位
                # is_current: 面板当前展示的就是本次流所属的会话
                # is_synced:  相等 => 面板尾部就是本轮的块, 可原地叠加 / 不相等 => 面板被重建过, 本轮不碰界面 (只累数据, 由 ChatList.session_msgs_render 补录)
                is_current = chat_session_id == EndPoints.runtime["session_id_chat_current"]
                is_synced = EndPoints.tmp_msgs[chat_session_id]["rendered_click_count"] == EndPoints.tmp_msgs[chat_session_id]["click_count"]

                # 标记位: 状态 = reasoning
                if EndPoints.tmp_msgs[chat_session_id]["status"] != "reasoning":
                    EndPoints.tmp_msgs[chat_session_id]["status"] = "reasoning"
                    # 创建一个缓存条目
                    EndPoints.tmp_msgs[chat_session_id]["aimsgs"].append({"type": "reasoning", "reasoning": "", "lc_run_id": lc_run_id})
                    # 渲染界面 (非切换重建)
                    if is_current and is_synced:
                        EndPoints.chat["chat_body"].current.content.controls.append(cls.build_blk_ai_reasoning(lc_run_id=lc_run_id, blk_status="start"))
                # 更新数据
                EndPoints.tmp_msgs[chat_session_id]["aimsgs"][-1]["reasoning"] += delta
                # 渲染界面 (非切换重建): 面板尾部就是本块 -> 原地叠加即可
                if is_current and is_synced:
                    # 针对副标题
                    EndPoints.chat["chat_body"].current.content.controls[-1].content.subtitle.controls[0].value += delta
                    # 针对内容
                    EndPoints.chat["chat_body"].current.content.controls[-1].content.controls[0].value += delta
                    # 更新界面
                    await EndPoints.chat["chat_body"].current.content.scroll_to(offset=-1, duration=0)
                    EndPoints.root["page"].update()
        except Exception as e:
            await cls.msg_error_mark(chat_session_id=chat_session_id, astream=astream, e=e)

    @classmethod
    async def consume_text(cls, message, chat_session_id, lc_run_id, astream):
        """
        消费 text 流数据 (异步)
        
        Args:
        - message:          astream.messages 中的单个 delta
        - char_session_id:  对应的会话ID, 用于标识这是哪个会话调用的工具
        - lc_run_id:        langchain 运行时的唯一id
        - astream:          本轮运行的句柄, 中止时需要用它的 abort() 取消 in-flight pull
        """
        # 兜底: try 必须包住整个 async for (理由同 consume_messages)
        try:
            async for delta in message.text:
                # 状态 = error/aborted 时立即 abort() 关闭所有 channel, 让 gather 干净返回以执行收尾逻辑
                # 中止日志统一在 consume_messages 处输出, 此处不重复打印
                if EndPoints.tmp_msgs[chat_session_id]["status"] in ["error", "aborted"]:
                    await astream.abort()
                    return
                
                # 判断会话状态的标记位
                # is_current: 面板当前展示的就是本次流所属的会话
                # is_synced:  相等 => 面板尾部就是本轮的块, 可原地叠加 / 不相等 => 面板被重建过, 本轮不碰界面 (只累数据, 由 ChatList.session_msgs_render 补录)
                is_current = chat_session_id == EndPoints.runtime["session_id_chat_current"]
                is_synced = EndPoints.tmp_msgs[chat_session_id]["rendered_click_count"] == EndPoints.tmp_msgs[chat_session_id]["click_count"]

                # 标记位: 状态 = text
                if EndPoints.tmp_msgs[chat_session_id]["status"] != "text":
                    EndPoints.tmp_msgs[chat_session_id]["status"] = "text"
                    # 渲染界面 (非切换重建) & 上一个控件是思考控件
                    # -> 删掉副标题 (要确保 EndPoints.tmp_msgs[chat_session_id]["aimsgs"] 不为空)
                    # -> 思考中 更新为 思考完成
                    if EndPoints.tmp_msgs[chat_session_id]["aimsgs"] and EndPoints.tmp_msgs[chat_session_id]["aimsgs"][-1]["type"] == "reasoning" and is_current and is_synced:
                        EndPoints.chat["chat_body"].current.content.controls[-1].content.subtitle = None
                        EndPoints.chat["chat_body"].current.content.controls[-1].content.title.controls[1].value = EndPoints.runtime["app_util_lang"].translate(key="reason_finish")
                    # 创建一个缓存条目
                    EndPoints.tmp_msgs[chat_session_id]["aimsgs"].append({"type": "text", "text": "", "lc_run_id": lc_run_id})
                    # 渲染界面 (非切换重建)
                    if is_current and is_synced:
                        EndPoints.chat["chat_body"].current.content.controls.append(cls.build_blk_ai_text(lc_run_id=lc_run_id))
                # 更新数据
                EndPoints.tmp_msgs[chat_session_id]["aimsgs"][-1]["text"] += delta
                # 渲染界面 (面板尾部就是本轮的块)
                if is_current and is_synced:
                    EndPoints.chat["chat_body"].current.content.controls[-1].content.value += delta
                    await EndPoints.chat["chat_body"].current.content.scroll_to(offset=-1, duration=0)
                    EndPoints.root["page"].update()
        except Exception as e:
            await cls.msg_error_mark(chat_session_id=chat_session_id, astream=astream, e=e)

    @classmethod
    async def callback_msg_retry(cls, e):
        """
        重试按钮触发时来更新消息流 (从最近的 user_msg 处重新发送)

        Note:
        1. 顺序: 删界面 -> 删库 -> 重发
           -> 删界面放最前纯粹为了响应快
           -> user_msg 块本身保留 (不删不重建, 否则删掉再重建会让界面闪一下)
           -> 只退掉它之后的块 (AI Summary / 最后结果块 / 错误块)

        2. 删库必须早于重发
           -> update_msg_stream 第一件事就是用新的 HumanMessage 起 astream_events
           -> 若旧轮还留在 state 里, 新 HumanMessage 会被追加在它之后

        3. 删库失败会中止重发: 记日志 + 补一个错误块告知, 然后 return
           -> user_msg 块仍在, 所以错误块上的重试按钮依然可用 (不会找不到锚点)
           -> 函数开头「抢占」置的 start 要还原回 error (否则后续重试被守卫永久拦住)

        4. 开头「抢占」: 立刻把 status 置为非终态, 防止第二次点击重试并发出两个流

        机制细节: 见可独立运行的验证脚本 test/sample/langgraph_delete_last_turn.py
        - REMOVE_ALL_MESSAGES 的重设语义
        - 为何不用 adelete_thread / 为何 as_node必须显式传
        """
        # 先获取当前的 chat_session_id, 用于删除 checkpointer 中的内容
        chat_session_id = EndPoints.runtime["session_id_chat_current"]
        config = {"configurable": {"thread_id": chat_session_id}}

        # 重试只能发生在「一轮已结束」时: stop / error / aborted
        status = EndPoints.tmp_msgs.get(chat_session_id, {}).get("status")
        if status not in ("stop", "error", "aborted"):
            logger.warning(f"stream is busy (status={status}), ignore this retry click. session_id={chat_session_id}")
            return
        
        # 抢占本轮: 立刻置为非终态, 防止第二次点击重试
        EndPoints.tmp_msgs[chat_session_id]["status"] = "start"

        # 界面上倒序找最近的 user_msg 消息块
        user_msg = None
        controls = EndPoints.chat["chat_body"].current.content.controls
        for idx, control in enumerate(reversed(controls), start=1):
            if control.data.get("msg_type") == "user_msg":
                user_msg = control.data.get("user_msg")
                # 保留 user_msg 块本身: 它的 0-based 下标是 len - idx
                # -> 不能化简成 `-idx + 1`: idx=1 (user_msg 已是最后一块) 时会退化成 [:0], 把整个面板清空 (中止后按库重渲染 / 空内容正常收尾时可达)
                EndPoints.chat["chat_body"].current.content.controls = controls[:len(controls) - idx + 1]
                # 直接将发送图标切换为 Stop
                EndPoints.chat["chat_input_send_btn"].current.icon = ft.Icons.STOP
                EndPoints.root["page"].update()
                break
        if user_msg is None:
            EndPoints.tmp_msgs[chat_session_id]["status"] = status
            logger.warning(f"no user message block found, ignore this retry click. session_id={chat_session_id}")
            return

        # 从 checkpointer 中删除指定内容
        # -> 读历史用只读空壳图 (与 chat_list.session_msgs_render 同款, 见 LCAgents.state_graph_chat_update)
        # -> 写入时必须有 agent, 因为空图只声明了 messages, 用它写会丢掉
        #    branch:to:model / branch:to:tools 等 channel 的 channel_values
        #    (langgraph/pregel/_checkpoint.py: 新 checkpoint 的 values 只从「当前图声明的 channels」里取)
        #################################################################################################################
        lc_agents = EndPoints.runtime["lc_agents"]
        if lc_agents.state_graph_chat is None:
            lc_agents.state_graph_chat_update()
        snapshot = await lc_agents.state_graph_chat.aget_state(config)
        messages = snapshot.values.get("messages", [])
        # 获取最近的 HumanMessage 索引
        last_human_idx = next((i for i in reversed(range(len(messages))) if isinstance(messages[i], HumanMessage)), None)
        # 没有 HumanMessage: 说明上一轮压根没进库, 没有旧轮可退 -> 直接重发即可, 不会产生重复
        if last_human_idx is not None:
            # 删库失败的详情 (None = 成功)
            errmsg = None
            # 注意: 写入入口必须有 agent
            if lc_agents.agent_chat is None:
                await lc_agents.agent_chat_update_async()
            if lc_agents.agent_chat is None:
                # 建不出来: 没配默认模型 / 模型配置有问题
                errmsg = EndPoints.runtime["app_util_lang"].translate(key="retry_failed_desc")
            else:
                keep = messages[:last_human_idx]
                try:
                    # as_node 必须显式传 (理由同 msg_aborted_save):
                    # 推断依赖 checkpoint 的 versions_seen, model/tools 在同一步都更新过就无法判定
                    await lc_agents.agent_chat.aupdate_state(
                        config,
                        {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *keep]},
                        as_node="model",
                    )
                except Exception as e:
                    logger.exception(e)
                    errmsg = str(e)
            # 删库失败 => 必须中止重发, 补一个错误块告知
            if errmsg is not None:
                logger.error(f"Failed to delete last turn, retry aborted: session_id={chat_session_id}, reason={errmsg}")
                # 还原: 上面的「抢占」把它置成了 start, 但本轮并没有真正开始
                # 不还原后续重试会被起点守卫永久拦住
                EndPoints.tmp_msgs[chat_session_id]["status"] = "error"
                EndPoints.chat["chat_body"].current.content.controls.append(cls.build_blk_err_msg(
                    reason=EndPoints.runtime["app_util_lang"].translate(key="retry_failed"),
                    status="error",
                    errmsg=errmsg,
                ))
                EndPoints.root["page"].update()
                return
        #################################################################################################################

        # 重新发送 (update_msg_stream 内部会 tmp_msgs_init, click_count / rendered_click_count 双归 1)
        await cls.msg_update_stream(user_msg=user_msg)

    @classmethod
    def callback_msg_copy(cls, e):
        """
        复制消息块里的内容
        """
        pass