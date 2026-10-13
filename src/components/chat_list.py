import copy
import uuid
import flet as ft
from src.endpoints import EndPoints
from src.components.chat_header import ChatHeader
from src.components.chat_body import ChatBody
from src.components.chat_input import ChatInput
from src.components.common import MessageCommon
from src.utils.logging import logger
from langchain.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.graph import START, StateGraph
from langgraph.graph.message import MessagesState


class ChatList:
    """
    对话列表
    """
    @classmethod
    def build_blk_session_add_btn(cls):
        """
        新建会话按钮
        """
        session_add_btn = ft.Button(
            content=EndPoints.runtime["app_util_lang"].translate(key="add_session"),
            expand=True,
            expand_loose=True,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
            on_click=cls.callback_session_add,
        )
        return session_add_btn

    @classmethod
    def build_blk_session_item(cls, session_id, title):
        """
        构建一个会话项
        """
        session_item = ft.ListTile(
            title=ft.Text(title),
            dense=True,
            leading=ft.ReorderableDragHandle(
                content=ft.Icon(ft.Icons.DRAG_INDICATOR, color=ft.Colors.GREY_500, size=20),
                mouse_cursor=ft.MouseCursor.GRAB,
            ),
            trailing=ft.IconButton(
                icon=ft.Icons.CANCEL,
                padding=0, 
                icon_size=18,
                width=20,
                height=20,
                data={"session_id": session_id},
                on_click=cls.callback_session_del,
            ),
            content_padding=0,
            data={"session_id": session_id, "title": title},
            on_click=cls.callback_session_msgs_render,
        )
        return session_item

    @classmethod
    def build_blk_sessions_list(cls):
        """
        构建一个会话列表
        """
        all_sessions = ft.ReorderableListView(
            show_default_drag_handles=False,
            controls=[
                cls.build_blk_session_item(session_id=session["session_id"], title=session["title"])
                for session in EndPoints.runtime["app_util_filedata"].data_read(data_type="sort_chat")
            ],
            ref=EndPoints.chat["chat_list"],
            on_reorder=cls.callback_sessions_reorder,
        )
        return all_sessions

    @classmethod
    def callback_session_add(cls, e=None):
        """
        添加会话回调函数

        Args:
        - e:    e 是 Flet 传递的 event 对象, 如果为 None 则说明是由手动触发的 (删掉了所有的会话列表, 需要新建一个)
        """
        # 基于时间来生成唯一的 uuid, 该值在 langchain 里会被用作 thread_id
        # 格式为: <user>_<chat/agent>_<uuid>
        username = "default"
        session_id = f"{username}_chat_{uuid.uuid1()}"
        title = EndPoints.runtime["app_util_lang"].translate(key="new_session")
        # 添加新的会话项
        EndPoints.chat["chat_list"].current.controls.append(
            cls.build_blk_session_item(
                session_id=session_id, 
                title=title,
            )
        )
        # 同步至持久化数据
        sessions = EndPoints.runtime["app_util_filedata"].data_read(data_type="sort_chat")
        sessions.append({"session_id": session_id, "title": title})
        EndPoints.runtime["app_util_filedata"].data_save(data_type="sort_chat", data_cont=sessions)

    @classmethod
    def callback_session_del(cls, e):
        """
        删除指定会话的回调函数
        """
        # 会话列表部分: controls 是 UI / sessions 是 Data
        controls = EndPoints.chat["chat_list"].current.controls
        sessions = EndPoints.runtime["app_util_filedata"].data_read(data_type="sort_chat")
        for i in range(len(controls)):
            if e.control.data.get("session_id") == controls[i].data.get("session_id"):
                # 界面删除
                controls.pop(i)
                # 同步数据
                sessions.pop(i)
                EndPoints.runtime["app_util_filedata"].data_save(data_type="sort_chat", data_cont=sessions)
                EndPoints.runtime["app_util_cache"].tmp_msgs_del(session_id=e.control.data.get("session_id"))
                EndPoints.runtime["app_util_cache"].tmp_msgs_state_del(session_id=e.control.data.get("session_id"))
                break

        # 会话详情部分: 删掉 checkpointer 里该 thread 的全部数据 (checkpoints + writes)
        # https://docs.langchain.com/oss/python/langgraph/add-memory#delete-all-checkpoints-for-a-thread
        # https://docs.langchain.com/oss/python/langgraph/add-memory#database-management
        # https://reference.langchain.com/python/langgraph.checkpoint.sqlite/aio/AsyncSqliteSaver/setup
        # 走 LCAgents.session_delete(): 它内部先 await setup() 再 adelete_thread,
        # 避免冷启动 (aiosqlite 连接尚未建立) 时直接删除抛 ValueError: no active connection
        e.page.run_task(EndPoints.runtime["lc_agents"].session_delete, e.control.data.get("session_id"))
        # 界面删除 & 刷新
        EndPoints.chat["chat_header"].current.content.controls[0].content.value = None
        EndPoints.chat["chat_body"].current.content.controls.clear()
        e.page.update()
        # 更新 session_id 的相关标记位 (全删除掉)
        EndPoints.runtime["session_id_chat_current"] = None
        EndPoints.runtime["session_id_chat_last"] = None        # 主要用于判断是否在重复点击
        EndPoints.runtime["session_id_agent_current"] = None
        EndPoints.runtime["session_id_agent_last"] = None       # 主要用于判断是否在重复点击

        # 判断删除后会话列表是否为空, 如果是则补充一个
        if len(EndPoints.chat["chat_list"].current.controls) == 0:
            cls.callback_session_add()
            cls.callback_session_msgs_render()
            EndPoints.root["page"].update()

    @classmethod
    def callback_session_msgs_render(cls, e=None, session_id=None, title=None):
        """
        对指定 session_id 来渲染所有历史消息

        Args:
        - e:            ft.Event 对象, 如果为 None 说明是手动触发
        - session_id:   如果非 None, 则基于指定的 session_id 来渲染
        - title:        如果非 None, 则基于指定的 title 来渲染
        """
        # 基于不同情况来判断如何获取 session_id & title
        ####################################################################################
        # 如果 e 不是 None, 则说明是点击事件触发
        if e:
            session_id = e.control.data.get("session_id")
            title = e.control.data.get("title")
        # 如果 session_id 和 title 都不为 None, 则说明是通过传值传递进来的
        elif session_id and title:
            session_id = session_id
            title = title
        # 其余情况, 从当前的 chat_list 中获取第一个控件的 session_id & title
        else:
            control = EndPoints.chat["chat_list"].current.controls[0]
            session_id = control.data.get("session_id")
            title = control.data.get("title")
        ####################################################################################

        # 重复点击: 必须是 session_id_chat_current / session_id_chat_last 同时满足才可以
        # -> 如果 session_id_chat_current = None, 则意味着重新点击了会话按钮, 此刻不属于重复点击
        if session_id == EndPoints.runtime["session_id_chat_last"] and session_id == EndPoints.runtime["session_id_chat_current"]:
            logger.info("Ignore duplicate clicks on the same conversation details.")
        else:
            # 清空历史会话内容
            EndPoints.chat["chat_body"].current.content.controls.clear()
            # 更新 session_id 的相关标记位
            # -> 更新 chat_current / chat_last
            # -> 清除 agent_current
            # -> 不动 agent_last
            EndPoints.runtime["session_id_chat_current"] = session_id
            EndPoints.runtime["session_id_chat_last"] = session_id
            EndPoints.runtime["session_id_agent_current"] = None
            # 更新该会话的点击状态
            # -> 如果不存在该缓存条目, 则直接初始化
            # -> 否则点击数 +1
            if EndPoints.tmp_msgs.get(session_id) is None:
                EndPoints.runtime["app_util_cache"].tmp_msgs_init(session_id=session_id)
            else:
                EndPoints.tmp_msgs[session_id]["click_count"] += 1

            # 渲染 header 部分
            ChatHeader.build_blk_header(session_id, title)
            # 调整发送按钮图标
            if EndPoints.tmp_msgs[session_id]["status"] in ["stop", "error", "aborted"]:
                EndPoints.chat["chat_input_send_btn"].current.icon = ft.Icons.SEND
            else:
                EndPoints.chat["chat_input_send_btn"].current.icon = ft.Icons.STOP
            # 附件信息
            ChatInput.refresh_input_attachments()

            # 更新 & 异步渲染
            if e:
                e.page.update()
                e.page.run_task(cls.session_msgs_render, session_id=session_id)
            else:
                EndPoints.root["page"].update()
                EndPoints.root["page"].run_task(cls.session_msgs_render, session_id=session_id)

    @classmethod
    def callback_sessions_reorder(cls, e: ft.OnReorderEvent):
        """
        重新排序会话列表

        Note:
        使用到了 sequence.insert 方法
        将 value 在给定的 index 位置插入到 sequence 中: sequence.insert(index, value, /)
        """
        # controls 是 UI / sessions 是 Data
        controls = EndPoints.chat["chat_list"].current.controls
        sessions = EndPoints.runtime["app_util_filedata"].data_read(data_type="sort_chat")
        controls.insert(e.new_index, controls.pop(e.old_index))
        sessions.insert(e.new_index, sessions.pop(e.old_index))
        # 同步数据
        EndPoints.runtime["app_util_filedata"].data_save(data_type="sort_chat", data_cont=sessions)

    @classmethod
    def _session_msgs_merge(cls, msg_group: list) -> bool:
        """
        用于判定一个消息段是否需要聚合 (session_msgs_render 的子函数)

        规则:
        1. msg_group 内 AIMessage 数量 =1 => 不聚合
           -> 只有一条 AI 回复, 没有中间过程可折叠
        2. msg_group 内的最后一条消息不是 AIMessage => 不聚合
           -> 例如停在 ToolMessage, 说明工具刚跑完就被中止
        3. 段内最后一条 AIMessage 的最后一个内容块不是 text => 不聚合
           -> 说明还在流式输出, 或被迫中止

        Args:
        - msg_group: 每一个消息组, 即同一个 HumanMessage 之后的全部消息列表

        Return:
        - True  => 聚合 (中间过程折叠进 AI Summary, 末尾 text 单独成块)
        - False => 不聚合 (全部平铺)
        """
        # msg_group 内 AIMessage 数量 =1
        if sum(1 for message in msg_group if isinstance(message, AIMessage)) == 1:
            return False
        # msg_group 内的最后一条消息不是 AIMessage
        if not isinstance(msg_group[-1], AIMessage):
            return False
        # 归一化最后一条 AIMessage 里的 content
        ai_msg_blk = MessageCommon.ai_msg_format_content(ai_msg=msg_group[-1])
        # 聚合: ai_msg_blk 不为空 & ai_msg_blk[-1] 的类型必须是 text
        return bool(ai_msg_blk) and ai_msg_blk[-1].get("type") == "text"

    @classmethod
    def _session_msgs_group_render(cls, group: list, merge: bool):
        """
        渲染一个消息段

        Args:
        - group: 消息段, 即同一个 HumanMessage 之后的全部消息
        - merge: 是否聚合 (由 session_msgs_merge 判定)
        """
        # 当前界面的所有控件
        controls = EndPoints.chat["chat_body"].current.content.controls
        # AI Summary 块 (仅在聚合时创建)
        blk_ai_summary = ChatBody.build_blk_ai_summary() if merge else None
        # 标记位: AI Summary 是否已经挂到界面上 (保证只挂一次)
        summary_appended = False

        def _summary_get() -> list:
            """
            取 AI Summary 内部的控件列表

            blk_ai_summary.content.controls[0] 对应 ExpansionTile 里那个 ft.Column
            """
            return blk_ai_summary.content.controls[0].controls

        def _summary_append():
            """
            把 AI Summary 挂到界面上 (仅第一次生效, 重复调用无副作用)
            """
            # https://docs.python.org/zh-cn/3.14/reference/simple_stmts.html#nonlocal
            # 当一个函数或类的定义嵌套 (被包围) 在其他函数的定义中时, 其非局部作用域就是包围它的函数的局部作用域
            # nonlocal 语句会使其所列出的标识符指向之前在非局部作用域中绑定的名称
            nonlocal summary_appended
            if blk_ai_summary is not None and not summary_appended:
                controls.append(blk_ai_summary)
                summary_appended = True

        # 第一遍: 渲染全部 AIMessage
        for idx, message in enumerate(group):
            if not isinstance(message, AIMessage):
                continue
            aimsg_content = MessageCommon.ai_msg_format_content(ai_msg=message)
            is_last_message = idx == len(group) - 1
            for bidx, msg in enumerate(aimsg_content):
                # 该块的挂载位置: 聚合时进 AI Summary, 平铺时直接进界面
                into_summary = merge
                if msg["type"] == "reasoning":
                    blk = ChatBody.build_blk_ai_reasoning(reasoning=msg["reasoning"], lc_run_id=message.id)
                elif msg["type"] == "tool_call":
                    blk = ChatBody.build_blk_ai_tool_call(args_dict=msg, lc_run_id=message.id)
                elif msg["type"] == "text":
                    # 只有「末条消息的最后一个 text 块」才是这一轮真正的结尾
                    if is_last_message and bidx == len(aimsg_content) - 1:
                        _summary_append()   # 先挂 AI Summary, 再挂最终结果 (保证先后顺序)
                        into_summary = False
                        blk = ChatBody.build_blk_ai_text_finally(text=msg["text"], lc_run_id=message.id)
                    # 其余 text 都属于中间过程
                    else:
                        blk = ChatBody.build_blk_ai_text(text=msg["text"], lc_run_id=message.id)
                else:
                    logger.error(f"Unknown message type: {msg}")
                    continue
                if into_summary:
                    _summary_get().append(blk)
                else:
                    controls.append(blk)

        # 第二遍: 把 ToolMessage 的结果回填到对应的 tool_call 块里
        # -> 必须放在 AIMessage 之后: 中止补写会让 ToolMessage 排在 AIMessage 之前 (二者同段),
        #    只有先渲染完 tool_call 块, 才能按 tool_call_id 找到它
        # -> 匹配只用 tool_call_id, 不用位置: 多轮工具时只有 id 与 AIMessage 的成对关系可靠
        for message in group:
            if not isinstance(message, ToolMessage):
                continue
            # tool_call 块可能在 AI Summary 内部 (聚合), 也可能直接在界面上 (平铺)
            pools = [controls] if blk_ai_summary is None else [_summary_get(), controls]
            for pool in pools:
                blk = next((
                    control for control in pool
                    if control.data is not None
                    and control.data.get("msg_type") == "tool_call"
                    and control.data.get("tool_call_id") == message.tool_call_id
                ), None)
                if blk is not None:
                    blk.content.controls = [ft.Markdown(value=MessageCommon.tool_msg_format_markdown(tool_msg=message))]
                    break
            else:
                logger.warning(f"ToolMessage has no matched tool_call block: {message.tool_call_id}")

        # 兜底: 这一段有中间过程, 但末尾不是 text (还在流式输出 / 被迫中止) => 也要把 AI Summary 挂上
        # -> 否则 AI Summary 永远不会出现在界面上, 这一段的内容全部丢失
        if blk_ai_summary is not None and _summary_get():
            _summary_append()

    @classmethod
    async def session_msgs_render(cls, session_id: str):
        """
        渲染对应会话的历史消息, 包括:
        1. 对应数据库中的历史内容
        2. 如果该会话处于流式输出截断, 则也会把还未保留到数据库中的消息也一并渲染出来

        Args:
        - session_id: 对应的会话ID
        """
        # 基于 "会话ID" 获取所有的历史消息
        config = {"configurable": {"thread_id": session_id}}
        if EndPoints.runtime["lc_agents"].state_graph_chat is None:
            EndPoints.runtime["lc_agents"].state_graph_chat_update()
        snapshot = await EndPoints.runtime["lc_agents"].state_graph_chat.aget_state(config)
        messages = snapshot.values.get("messages", [])

        # 对历史消息按 HumanMessage 切片分组
        # -> 形状: [HumanMessage, [消息段], HumanMessage, [消息段], ...]
        all_group = []
        msg_group = []
        for message in messages:
            if isinstance(message, HumanMessage):
                if msg_group:
                    all_group.append(msg_group)
                    msg_group = []
                all_group.append(message)
            else:
                msg_group.append(message)
        if msg_group:   # 补齐最后一段结尾
            all_group.append(msg_group)

        # 渲染历史消息
        # -> HumanMessage => 用户消息块
        # -> list         => 一轮对话的消息段 (即该 HumanMessage 之后的全部消息)
        for group in all_group:
            if isinstance(group, HumanMessage):
                # HumanMessage 仅构建一个消息块即可
                blk_user_msg = ChatBody.build_blk_user_msg(user_msg=group.content, user_msg_id=None)
                EndPoints.chat["chat_body"].current.content.controls.append(blk_user_msg)
            else:
                # 渲染一个消息块
                # -> group: 一个完整的消息块分组
                # -> merge: 基于这个消息块来判断是否需要合并
                cls._session_msgs_group_render(group=group, merge=cls._session_msgs_merge(msg_group=group))

        # 更新 UI - 数据库中的历史数据渲染完毕
        EndPoints.root["page"].update()

        # 如果当前会话正处于流式输出阶段, 则继续补录
        if session_id == EndPoints.runtime["session_id_chat_current"] and EndPoints.tmp_msgs.get(session_id, {}).get("status") not in (None, "stop", "error", "aborted"):
            # 调用重建的补录函数
            ChatBody.msg_update_rebuild(msgs=EndPoints.tmp_msgs[session_id]["aimsgs"])
            # 补录完成后, 将该会话的 click_count 同步至 rendered_click_count
            # -> click_count: 每次点击该会话就+1
            # -> rendered_click_count: 必须渲染完历史会话才和 click_count 同步
            # -> 如果这两个值不相等, 则证明流式消息中途被打断了, 需要重新补录
            EndPoints.tmp_msgs[session_id]["rendered_click_count"] = EndPoints.tmp_msgs[session_id]["click_count"]
            EndPoints.root["page"].update()

        # 如果当前会话已意外终止 (error / aborted), 则补一个错误块
        if session_id == EndPoints.runtime["session_id_chat_current"] and EndPoints.tmp_msgs.get(session_id, {}).get("status") in ("error", "aborted"):
            EndPoints.chat["chat_body"].current.content.controls.append(ChatBody.build_blk_err_msg(
                reason=EndPoints.tmp_msgs[session_id]["reason"],
                status=EndPoints.tmp_msgs[session_id]["status"],
            ))
            EndPoints.root["page"].update()