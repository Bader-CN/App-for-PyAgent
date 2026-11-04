import flet as ft

from endpoints import EndPoints
from components.chat_list import ChatList
from components.chat_input import ChatInput
from components.common import InputCommon
from utils.logging import logger


class ChatView:
    """
    视图 - 对话视图
    """
    def __init__(self):
        # 宽度定义
        self.lv1_min_width = 200
        self.lv1_max_width = 300
        # 当前宽度
        self.lv1_view_width = EndPoints.runtime["app_util_profile"].chat_view_lv1_width()
        # 对话视图基础布局
        self.lv1_view = ft.Container(ref=EndPoints.chat["lv1_view"])
        self.lv2_view = ft.Container(ref=EndPoints.chat["lv2_view"])
        self.chat_header = ft.Container(ref=EndPoints.chat["chat_header"])
        self.chat_body = ft.Container(ref=EndPoints.chat["chat_body"])
        # 输入面板在 render_lv2 中重建, 不在此处常驻 (理由见 render_lv2)
        # 可拖动的分割线
        self.vdivider = ft.GestureDetector(
            content=ft.Container(
                # 视觉宽度为 1px 的分割线
                content=ft.VerticalDivider(width=1),
                # 拖拽的热区宽度: 左右各 3px
                width=7,
                # 透明底色: 让整个热区都参与拖拽
                bgcolor=ft.Colors.TRANSPARENT,
                # 让分割线居中
                alignment=ft.Alignment.CENTER,
            ),
            # 鼠标样式可调
            # https://flet.dev/docs/types/mousecursor/#flet.MouseCursor.RESIZE_COLUMN
            mouse_cursor=ft.MouseCursor.RESIZE_COLUMN,
            # 拖动事件回调函数
            # https://flet.dev/docs/controls/gesturedetector/#flet.GestureDetector.on_pan_update
            on_pan_update=self.callback_drop_update,
            on_pan_end=self.callback_drop_end,
        )
        # 对话视图核心布局
        self.chat_view = ft.Row(
            controls=[
                self.lv1_view,
                self.vdivider,
                self.lv2_view,
            ],
            expand=True,
            spacing=0,
            ref=EndPoints.chat["chat_view"],
        )

    def render_full(self):
        """
        完整渲染设置界面, 通常用于首次刷新
        """
        self.render_lv1()
        self.render_lv2()
        logger.debug("rendering chat_view completed.")

    def render_lv1(self):
        """
        渲染对话页面的 lv1 层级视图
        """
        # 调整 lv1_view 的宽度
        self.lv1_view.width = EndPoints.runtime["app_util_profile"].chat_view_lv1_width()
        # 绘制基础视图
        # ===============================
        # 先清后赋: 防「值相等跳过」
        # 病因: Container.content 是 Prop 描述符 (flet/controls/value_types.py::Prop.__set__)
        # -> old == value 时直接 return, 赋值被静默丢弃
        # 必踩条件: ref 是 InitVar / _i 是 compare=False, 都不参与 __eq__
        # -> 同工厂、同参数、同状态重建出的子树必然值相等
        # 本处的后果: 丢弃的是整棵新 Column, 其中 sessions_list 只被 ft.Ref (弱引用) 指着
        # -> 新控件被 GC => ref.current 变 None
        # -> 下一次点会话按钮 / 取 controls 时抛 AttributeError
        # 判据: ref 指向的控件 ≠ 界面上显示的控件
        # ===============================
        self.lv1_view.content = None
        self.lv1_view.content = ft.Column(
            controls=[
                ChatList.build_blk_session_add_btn(),
                ChatList.build_blk_sessions_list(),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            margin=ft.Margin(left=10, top=10, right=7, bottom=0),
        )

    def render_lv2(self):
        """
        渲染对话页面的 lv2 层级视图
        """
        # 标题部分
        pass
        # 聊天内容
        self.chat_body.expand = True
        self.chat_body.margin = ft.Padding.symmetric(horizontal=10, vertical=0)
        # 先清后赋: 防「值相等跳过」(机制与必踩条件见 render_lv1 的注释)
        # -> 本处丢弃的是消息 Column 本身
        # -> 后续 controls.clear() / append() 都作用在 self.chat_body.content 上, 它指向哪一份, 完全取决于这次赋值有没有被存下来
        # -> 一旦「存下来的」≠「界面上显示的」, 清空 / 追加就落在看不见的树上 => 静默错数据
        self.chat_body.content = None
        self.chat_body.content = ft.Column(          
            scroll=ft.ScrollMode.AUTO,
            ############################
            # 自动跟随到底部 (原生实现, 不需手写 on_scroll 状态机)
            # - 滚离底部 -> 暂停跟随
            # - 滚回底部 -> 自动恢复
            # - auto_scroll_animation=0: token 级流式, 瞬时跳底, 避免动画滞后
            # 注意: 与 scroll_to 互斥
            auto_scroll=True,
            auto_scroll_animation=0,
            ############################
            # 交叉轴 (即宽度) 铺满: 让每个消息块拿到 maxWidth 的紧约束, 从而横向填满 chat_body
            # -> 本 Column 主轴是竖直 => 那两行管的是高度; 且 scroll 让主轴无界
            # -> Flutter 会把带 flex 的子控件当普通子控件布局, expand 连高度都撑不起来
            # 注意: 本参数不能再用来右对齐 (它会让整行等宽, 所有消息块一起被拉满)
            # -> user_msg 的右对齐 + 气泡贴身由 MessageBlockCommon.build_blk_user_msg 内层 Column 负责
            # -> 不要用 ft.Row(alignment=END) 包消息块: Row 给子控件无界主轴宽度, 长文本不换行直接溢出
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ############################
        )
        # 输入面板: 每次渲染重建
        # -> Flet 的 ref 在构造时绑定 (BaseControl.__post_init__: ref.current = self), 不会在挂载时重绑
        #    故每次重建才能保证 ref 指向当前挂载的这一份
        # -> 也顺带让模型下拉列表等 "构建期快照" 在每次切回时重新读取
        self.input_panel = InputCommon.build_blk_input_panel(tools=ChatInput.build_blk_input_tools())
        # 渲染整体布局
        self.lv2_view.expand = True
        # 先清后赋: 防「值相等跳过」(机制与必踩条件见 render_lv1 的注释)
        # -> 本处必须做: input_panel 是上面刚重建的, 且被 self.input_panel 锚定
        #    => 不会被 GC, ref.current 也不为 None; 但「值相等跳过」会让它挂不上界面
        # -> 后果: 界面挂旧面板, ref 已绑新面板 (构造期绑定 ref.current = self)
        #    客户端按 control id 上报改值 (UPDATE_CONTROL_PROPS), 只有真正下发过的那份收得到
        #    => 用户敲进旧面板, 发送时读 ref 的新面板 -> 恒为空, 且字清不掉
        # -> 触发条件: 切走再切回 chat, 且期间没有草稿 / 附件
        #    (留了草稿或附件时新旧面板不等, 赋值真会发生, 反而不触发)
        self.lv2_view.content = None
        self.lv2_view.content = ft.Column(
            controls=[
                self.chat_header,
                self.chat_body,
                self.input_panel,
            ],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            margin=ft.Margin(left=7, top=0, right=10, bottom=0),
            expand=True,
        )

    def callback_drop_update(self, e: ft.DragUpdateEvent):
        """
        回调函数, 用于在触发拖拽时更新控件宽度

        Note:
        ft.DragUpdateEvent: https://flet.dev/docs/types/dragupdateevent/
        - 移动的距离:
          - local_delta:     自拖拽开始以来, 指针在事件接收器的局部坐标系中移动的距离
          - global_delta:    自拖拽开始以来, 指针在全局坐标系中移动的距离
        - 移动的位置:
          - local_position:  指针在事件接收器的坐标系中接触屏幕时的本地位置
          - global_position: 触发此更新时指针的全局位置

        Args:
        - e: ft.DragUpdateEvent
        """
        # 防止移速过快, 导致被越过边界
        lv1_width = self.lv1_view.width
        if lv1_width + e.local_delta.x < self.lv1_min_width:
            # self.lv1_view.width / self.lv1_view_width 这两个不一样
            self.lv1_view.width = self.lv1_min_width
            self.lv1_view_width = self.lv1_min_width
        elif lv1_width + e.local_delta.x > self.lv1_max_width:
            # self.lv1_view.width / self.lv1_view_width 这两个不一样
            self.lv1_view.width = self.lv1_max_width
            self.lv1_view_width = self.lv1_max_width
        else:
            # self.lv1_view.width / self.lv1_view_width 这两个不一样
            self.lv1_view.width += e.local_delta.x
            self.lv1_view_width = self.lv1_view.width

    def callback_drop_end(self, e: ft.DragUpdateEvent):
        """
        回调函数, 用于在结束拖拽时保存最新的宽度
        """
        # 最新的宽度
        new_width = self.lv1_view_width
        # 保存的宽度
        old_width = EndPoints.runtime["app_util_profile"].chat_view_lv1_width()
        if new_width != old_width:
            EndPoints.runtime["app_util_profile"].chat_view_lv1_width_set(width=new_width)