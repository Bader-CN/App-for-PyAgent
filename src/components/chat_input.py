import asyncio
import flet as ft
from src.endpoints import EndPoints
from src.components.chat_body import ChatBody
from src.components.common import AlertCommon
from src.utils.logging import logger


class ChatInput:
    """
    输入组件
    """
    # 类变量
    btn_height = 32
    btn_width = 32
    popup_height = 28
    popup_font_size = 12
    model_min_width = 100
    model_max_width = 250

    @classmethod
    def build_blk_attachment(cls, file_type: str, file_name: str):
        """
        构建一个附件的显示块

        Args:
        - file_type: 附件类型, 值可以是 file/image/video/audio
        - file_name: 附件名称
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
        """
        input_attachments = ft.Row(
            controls=[],
            ref=EndPoints.chat["chat_input_attachments"],
        )
        return input_attachments

    @classmethod
    def build_blk_input_textfield(cls):
        """
        文本输入的 TextField
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
            ref=EndPoints.chat["chat_input_textfield"],
        )
        return input_textfield

    @classmethod
    def build_blk_input_tool_add_attachments(cls):
        """
        工具 - 添加附件
        """
        add_btn = ft.Container(
            ft.IconButton(
                icon=ft.Icons.ADD,
                padding=0,
                height=cls.btn_height,
                width=cls.btn_width,
            ),
        )
        return add_btn

    @classmethod
    def build_blk_input_tool_model_switch(cls):
        """
        工具 - 模型切换控件
        """
        model_select = ft.PopupMenuButton(
            tooltip=EndPoints.runtime["app_util_lang"].translate(key="default_chat_model"),
            content=ft.Container(
                ft.Row(
                    controls=[
                        ft.Text(
                            value=EndPoints.runtime["app_util_profile"].default_model(default_type="chat_model"),
                            size=cls.popup_font_size,
                            ref=EndPoints.chat["chat_input_model_select"],
                        ),
                        ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, size=cls.popup_font_size),
                    ],
                ),
                border=ft.Border.all(),
                border_radius=5,
                padding=ft.Padding.symmetric(horizontal=5),
                height=cls.popup_height,
            ),
            items=[
                ft.PopupMenuItem(
                    content=i, 
                    height=cls.popup_height,
                    label_text_style=ft.TextStyle(size=cls.popup_font_size, color=ft.Colors.BLACK),
                    on_click=cls.callback_switch_chat_model,
                    data={"default_type": "chat_model", "default_model": i},
                )
                for i in EndPoints.runtime["app_util_conf"].models_list_enable()
            ],
            size_constraints=ft.BoxConstraints(min_width=cls.model_min_width, max_width=cls.model_max_width),
            menu_position=ft.PopupMenuPosition.OVER,
        )
        return model_select

    @classmethod
    def build_blk_input_tool_model_reasoning(cls):
        """
        工具 - 模型思考控制
        """
        model_thinking = ft.PopupMenuButton(
            tooltip="",
            content=ft.Container(
                ft.Row(
                    controls=[
                        ft.Text(
                            EndPoints.runtime["app_util_profile"].reasoning_level()["chat"], 
                            size=cls.popup_font_size, 
                            ref=EndPoints.chat["chat_input_model_reason"]
                        ),
                        ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, size=cls.popup_font_size),
                    ],
                ),
                border=ft.Border.all(),
                border_radius=5,
                padding=ft.Padding.symmetric(horizontal=5),
                height=cls.popup_height,
            ),
            items=[
                ft.PopupMenuItem(
                    content=i, 
                    height=cls.popup_height, 
                    label_text_style=ft.TextStyle(size=cls.popup_font_size, color=ft.Colors.BLACK),
                    on_click=cls.callback_switch_reasoning,
                    data={"reasoning_level": i},
                )
                for i in ["Off", "Low", "Medium", "High", "Auto"]
            ],
            menu_position=ft.PopupMenuPosition.OVER,
        )
        return model_thinking

    @classmethod
    def build_blk_input_tool_web_search(cls):
        """
        工具 - 搜索按钮
        """
        search_btn = ft.Container(
            ft.IconButton(
                icon=ft.Icons.LANGUAGE,
                icon_color=ft.Colors.BLUE, 
                padding=0,
                height=cls.btn_height,
                width=cls.btn_width,
                on_click=cls.callback_switch_web_search,
            ),
        )
        return search_btn

    @classmethod
    def build_blk_input_tools(cls):
        """
        输入栏相关工具
        """
        input_tools = ft.Row(
            controls=[
                # 添加附件
                cls.build_blk_input_tool_add_attachments(),
                # 模型选择
                cls.build_blk_input_tool_model_switch(),
                # 思考开关
                cls.build_blk_input_tool_model_reasoning(),
                # 网络搜索
                cls.build_blk_input_tool_web_search(),
                # 占位
                ft.Container(expand=True),
                # 发送按钮
                ft.IconButton(
                    icon=ft.Icons.SEND,
                    padding=0,
                    height=cls.btn_height,
                    width=cls.btn_width,
                    on_click=cls.callback_send_user_msg,
                    ref=EndPoints.chat["chat_input_send_btn"],
                ),
            ],
            spacing=5,
        )
        return input_tools

    @classmethod
    def refresh_input_attachments(cls, session_id_chat: str|None = None):
        """
        获取当前会话中的附件信息并显示到输入框里

        Args:
        - session_id_chat: 搜索附件的范围是基于哪个会话ID
        """
        # 先情况所有附件控件
        EndPoints.chat["chat_input_attachments"].current.controls.clear()
        
        if session_id_chat is None:
            session_id_chat = EndPoints.runtime["session_id_chat_current"]
        # 截图
        images = EndPoints.runtime["app_util_cache"].clipboard_image_get(session_prefix=session_id_chat)
        if images:
            logger.debug(images)
            for filename in images:
                image_blk = cls.build_blk_attachment(file_type="image", file_name=filename)
                EndPoints.chat["chat_input_attachments"].current.controls.append(image_blk)
            EndPoints.root["page"].update()

    @classmethod
    def callback_send_user_msg(cls, e: ft.ControlEvent | None = None):
        """
        获取并整理用户输入的信息

        Notes:
        - 如果 e 为 None, 则属于自动发送消息的情况, 例如被快捷键触发
        - LangChain 多模态数据格式
          https://docs.langchain.com/oss/python/langchain/messages#multimodal

        Args:
        - e:    可以是 ft.ControlEvent, 也可以为 None
        """
        # 获取 ft.IconButton & Page 对象
        if e is None:
            ft_btn = EndPoints.chat["chat_input_send_btn"].current
            page = EndPoints.root["page"]
            if ft_btn is None:
                logger.warning("Send button not available, ignore this call.")
                return
        else:
            ft_btn = e.control
            page = e.page

        # 基于图标判断: 发送消息
        if ft_btn.icon == ft.Icons.SEND:
            # 消息数据
            # https://docs.langchain.com/oss/python/langchain/messages#message-content
            user_msg = []
            ft_btn.icon = ft.Icons.STOP
            # 整理: 文字部分
            user_text = EndPoints.chat["chat_input_textfield"].current.value
            if user_text.strip() != "":
                user_msg.append({"type": "text", "text": user_text.strip()})
            # 整理: 附件部分
            controls = EndPoints.chat["chat_input_attachments"].current.controls
            if controls:
                for control in controls:
                    if control.data.get("type") == "image":
                        filename = control.data.get("filename")
                        img_data = EndPoints.runtime["app_util_cache"].clipboard_image_to_base64(filename=filename)
                        user_msg.append({"type": "image", "url": img_data})
            # user_msg 不能是非空
            if user_msg:
                # 渲染 user_msg
                user_msg_blk = ChatBody.build_blk_user_msg(user_msg=user_msg)
                EndPoints.chat["chat_body"].current.content.controls.append(user_msg_blk)
                # 清空内容和附件
                EndPoints.chat["chat_input_textfield"].current.value = None
                EndPoints.chat["chat_input_attachments"].current.controls.clear()
                EndPoints.runtime["app_util_cache"].clipboard_image_del(session_prefix=EndPoints.runtime["session_id_chat_current"])
                # 异步调用 (发送图标的终止条件不在这里判断, 而在 ChatBody.update_msg_stream 中来判断)
                page.run_task(ChatBody.msg_update_stream, user_msg=user_msg)
            else:
                ft_btn.icon = ft.Icons.SEND
                EndPoints.chat["chat_input_textfield"].current.value = None
                logger.warning("Input content is empty, ignoring this click action.")
                page.update()
        # 基于图标判断: 终止消息
        else:
            # 基于 session_id 来修改数据状态
            chat_session_id = EndPoints.runtime["session_id_chat_current"]
            # 已经终止过了: 忽略本次点击
            # -> 图标已切回 SEND, 正常点不到第二次; 但快速双击 / 键盘事件仍可能进来
            if EndPoints.tmp_msgs[chat_session_id]["status"] in ["error", "aborted"]:
                logger.warning(f"Chat stream already terminated (status={EndPoints.tmp_msgs[chat_session_id]['status']}), ignore this stop click. session_id={chat_session_id}")
                return
            EndPoints.tmp_msgs[chat_session_id]["status"] = "aborted"
            EndPoints.tmp_msgs[chat_session_id]["reason"] = EndPoints.runtime["app_util_lang"].translate(key="request_was_aborted")
            # 立即持久化一次: 用户可能按完停止就关程序
            EndPoints.runtime["app_util_cache"].tmp_msgs_state_update(
                session_id=chat_session_id,
                status="aborted",
                reason=EndPoints.tmp_msgs[chat_session_id]["reason"],
            )
            # 立即渲染错误块, 不等 update_msg_stream 的收尾
            # -> 收尾要先等 asyncio.gather 返回, 而工具静默期没有任何 delta, 可能要干等几秒 (实测 3.5s)
            # -> 按钮回调是同步且即时的, 放这里用户一按就能看到
            # -> 因此收尾那边只负责 error 的渲染 (aborted 已在本次处理, 避免重复)
            EndPoints.chat["chat_body"].current.content.controls.append(ChatBody.build_blk_err_msg(
                reason=EndPoints.tmp_msgs[chat_session_id]["reason"],
                status="aborted",
            ))
            # 恢复发送按钮
            ft_btn.icon = ft.Icons.SEND
            page.update()

    @classmethod
    async def callback_switch_chat_model(cls, e):
        """
        切换聊天模型 (同时也会同步修改默认的聊天模型)

        Note:
        本回调是异步函数, 原因见 LCAgents.agent_chat_update_async 的 Note:
        同步回调会独占 event loop, 而 page.update() 只是把补丁入队
        -> 补丁要等回调返回才发得出去, 界面看起来 "渲染很慢"
        """
        # 获取相关数据
        # await 之后 e.control 可能已被卸载 (切页会重建 chat_input 子树)
        # 届时 e.page 会抛 RuntimeError, 故先把 page 取出来
        page = e.page
        default_type = e.control.data.get("default_type")
        default_model = e.control.data.get("default_model")

        # 正在加载智能体时, 忽略本次点击
        # 原因: 加载异步化后, 两次点击会并发构建, 后完成者会覆盖先完成者
        # -> 会出现 "界面显示 B, 实际 agent 是 A" 的静默错数据 (比崩溃更难查)
        # 同类风格参考 callback_send_user_msg 里 "已点击暂停但未停止" 的处理
        lc_agents = EndPoints.runtime["lc_agents"]
        if lc_agents.agent_chat_loading:
            logger.warning(f"Chat agent is loading, ignore this click. default_model is {default_model}.")
            return
        
        # 先刷新界面和设置
        # 这些同步操作必须在 await 之前执行 
        # -> 补丁先入队, 一旦让出 loop 就会被立即发出去
        EndPoints.runtime["app_util_profile"].default_model_set(default_type=default_type, default_model=default_model)
        EndPoints.chat["chat_input_model_select"].current.value = default_model
        page.update()
        
        # 继续加载模型: 用 await 而非 "线程 + join"
        # -> await 期间 loop 空闲, 界面不冻结; join 会阻塞 loop, 等于没改
        err_msg = await lc_agents.agent_chat_update_async()
        if err_msg:
            AlertCommon.alert_model_config_error(message=err_msg)
            EndPoints.runtime["app_util_profile"].default_model_set(default_type=default_type, default_model=None)
            # 重新取 ref 并判空: await 期间若切过页, render_lv2() 会重建输入区, ref 可能已换绑或为 None
            model_select = EndPoints.chat["chat_input_model_select"].current
            if model_select is not None:
                model_select.value = None
            page.update()

    @classmethod
    async def callback_switch_reasoning(cls, e):
        """
        切换思考强度
        """
        # 相关变量
        page = e.page
        lc_agents = EndPoints.runtime["lc_agents"]
        reason_lv_dict = EndPoints.runtime["app_util_profile"].reasoning_level()

        logger.debug(reason_lv_dict["chat"])
        logger.debug(e.control.data["reasoning_level"])

        # 当前值 != 保存的值
        if reason_lv_dict["chat"] != e.control.data["reasoning_level"]:
            # 先刷新界面和设置
            reason_lv_dict["chat"] = e.control.data["reasoning_level"]
            EndPoints.runtime["app_util_profile"].reasoning_level_set(reason_lv_dict=reason_lv_dict)
            EndPoints.chat["chat_input_model_reason"].current.value = e.control.data["reasoning_level"]
            page.update()

            # 更新 LCAgents 对话模型的 self.extra_body_chat 字典
            EndPoints.runtime["lc_agents"].extra_body_update_reasoning_level(agent_type="chat")

            # 重新加载模型
            while lc_agents.agent_chat_loading:
                logger.warning(f"Chat model loading, retrying...")
                await asyncio.sleep(0.2)             
            err_msg = await lc_agents.agent_chat_update_async()
            if err_msg:
                AlertCommon.alert_model_config_error(message=err_msg)

    @classmethod
    async def callback_switch_web_search(cls, e):
        """
        切换是否启用 Web 搜索
        """
        # 获取 lc_agents 对象
        lc_agents = EndPoints.runtime["lc_agents"]

        # 关闭 Web 搜索
        if e.control.icon_color == ft.Colors.BLUE:
            e.control.icon_color = None
            err_msg = await lc_agents.agent_chat_update_async(web_search=False)
            if err_msg:
                AlertCommon.alert_model_config_error(message=err_msg)
        # 开启 Web 搜索
        else:
            e.control.icon_color = ft.Colors.BLUE
            err_msg = await lc_agents.agent_chat_update_async(web_search=True)
            if err_msg:
                AlertCommon.alert_model_config_error(message=err_msg)

    @classmethod
    def callback_attachment_del(cls, e):
        """
        删除指定附件文件
        """
        # 获取文件名
        filename = e.control.data["filename"]
        controls = EndPoints.chat["chat_input_attachments"].current.controls
        # 针对截图
        if e.control.data["type"] == "image":
            EndPoints.runtime["app_util_cache"].clipboard_image_del(filename=filename)
            for control in controls:
                if control.data.get("filename") == filename:
                    EndPoints.chat["chat_input_attachments"].current.controls.remove(control)
                    break