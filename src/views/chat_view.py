import flet as ft

from src.endpoints import EndPoints
from src.utils.logging import logger
from src.components.chat_list import ChatList
from src.components.chat_input import ChatInput


class ChatView:
    """
    视图 - 对话视图
    """
    def __init__(self):
        # 宽度定义
        self.lv1_min_width = 200
        self.lv1_max_width = 300
        self.lv1_view_width = EndPoints.runtime["app_util_profile"].chat_view_lv1_width()  # 当前宽度
        # 对话视图基础布局
        self.lv1_view = ft.Container(ref=EndPoints.chat["lv1_view"])
        self.lv2_view = ft.Container(ref=EndPoints.chat["lv2_view"])
        self.chat_header = ft.Container(ref=EndPoints.chat["chat_header"])
        self.chat_body = ft.Container(ref=EndPoints.chat["chat_body"])
        self.chat_input = ft.Container(ref=EndPoints.chat["chat_input"])
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
        logger.trace("Rendering chat_view completed.")

    def render_lv1(self):
        """
        渲染对话页面的 lv1 层级视图
        """
        # 调整 lv1_view 的宽度
        self.lv1_view.width = EndPoints.runtime["app_util_profile"].chat_view_lv1_width()
        # 绘制基础视图
        # ===============================
        # 防止 ft.Ref 弱引用 产生的 GC 陷阱
        # 如果2次赋值的内容完全相同, 则新控件不会被赋值, 而是直接被回收
        # 界面上存在的则是老控件, 此刻 ref 指向的新控件已经消失了, 所以会出现 None 的错误
        # 解决方法是先赋值一次 None, 规避掉 flet 本身的优化操作, 然后在重新赋值即可解决
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
        self.chat_body.content = None   # 防止 ft.Ref 弱引用 产生的 GC 陷阱
        self.chat_body.content = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            ############################
            # 交叉轴 (即宽度) 铺满: 让每个消息块拿到 maxWidth 的紧约束, 从而横向填满 chat_body
            # -> 本 Column 主轴是竖直 => 那两行管的是高度; 且 scroll 让主轴无界
            # -> Flutter 会把带 flex 的子控件当普通子控件布局, expand 连高度都撑不起来
            ############################
            # 注意: 本参数不能再用来右对齐
            # 消息块右对齐需改用 ft.Row(alignment=ft.MainAxisAlignment.END, controls=[blk]) 包裹
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        # 输入面板
        self.chat_input.border_radius = 10
        self.chat_input.border = ft.Border.all()
        self.chat_input.margin = ft.Margin(left=0, top=0, right=0, bottom=10)
        self.chat_input.padding = ft.Padding.symmetric(horizontal=5, vertical=5)
        # 防止 ft.Ref 弱引用 产生的 GC 陷阱
        # 如果2次赋值的内容完全相同, 则新控件不会被赋值, 而是直接被回收
        # 界面上存在的则是老控件, 此刻 ref 指向的新控件已经消失了, 所以会出现 None 的错误
        # 解决方法是先赋值一次 None, 规避掉 flet 本身的优化操作, 然后在重新赋值即可解决
        self.chat_input.content = None
        self.chat_input.content = ft.Column(
            controls=[
                ChatInput.build_blk_input_attachments(),
                ChatInput.build_blk_input_textfield(),
                ChatInput.build_blk_input_tools(),
            ],
            spacing=5,
        )
        # 渲染整体布局
        self.lv2_view.expand = True
        self.lv2_view.content = ft.Column(
            controls=[
                self.chat_header,
                self.chat_body,
                self.chat_input,
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