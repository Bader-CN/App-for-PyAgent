import flet as ft
from src.endpoints import EndPoints
from src.utils.logging import logger


class ChatHeader:
    """
    标题组件
    """
    # 类变量
    remove_title_bgcolor = True     # 是否可以移除 title 的背景色

    @classmethod
    def build_blk_title_textfield(cls, session_id: str, title: str):
        """
        标题的 TextField 对象

        Args:
        - session_id: 会话ID
        - title:      标题
        """
        title_textfield = ft.Container(
            ft.TextField(
                value=title,
                text_style=ft.TextStyle(weight=ft.FontWeight.BOLD),
                dense=True,
                multiline=False,
                border=ft.InputBorder.NONE, # 隐藏边框
                data={"session_id": session_id},
                on_blur=cls.callback_title_edit,
                on_click=cls.callback_title_click,
            ),
            on_hover=cls.callback_title_hover,
            border_radius=5,
            padding=ft.Padding.symmetric(horizontal=5, vertical=5),
        )
        return title_textfield

    @classmethod
    def build_blk_title_rename(cls, session_id: str):
        """
        重新生成标题
        """
        title_rename = ft.IconButton(
            icon=ft.Icons.REFRESH,
            padding=0,
            height=28,
            width=28,
            data={"session_id": session_id},
        )
        return title_rename

    @classmethod
    def build_blk_header(cls, session_id: str, title: str):
        """
        组装完整的标题组件
        Args:
        - session_id: 会话ID
        - title:      标题
        """
        blk_header = ft.Row(
            controls=[
                cls.build_blk_title_textfield(session_id, title),
                ft.Container(expand=True),
                cls.build_blk_title_rename(session_id),
            ],
        )
        # 允许取消背景色 (触发该函数一定是点击了 ChatList 里对应的会话)
        cls.remove_title_bgcolor = True
        # 渲染到界面上
        EndPoints.chat["chat_header"].current.content = blk_header

    @classmethod
    def callback_title_edit(cls, e):
        """
        标题编辑回调函数
        """
        # 获取数据
        new_title = e.control.value
        session_id = e.control.data.get("session_id")
        sessions = EndPoints.runtime["app_util_filedata"].data_read(data_type="sort_chat")
        controls = EndPoints.chat["chat_list"].current.controls
        for i in range(len(controls)):
            if controls[i].data.get("session_id") == session_id and controls[i].title.value != new_title:
                # 更新界面
                controls[i].title.value = new_title
                controls[i].data["title"] = new_title
                # 保存数据
                sessions[i]["title"] = new_title
                EndPoints.runtime["app_util_filedata"].data_save(data_type="sort_chat", data_cont=sessions)
                break
        # 去掉父控件颜色 & 允许去掉背景色
        e.control.parent.bgcolor = None
        cls.remove_title_bgcolor = True

    @classmethod
    def callback_title_click(cls, e):
        """
        点击时需要调整的内容
        """
        cls.remove_title_bgcolor = False

    @classmethod
    def callback_title_hover(cls, e):
        """
        会话标题 - 悬停时改变背景色
        """
        # 鼠标进入
        if e.data:
            e.control.bgcolor = ft.Colors.GREY_200
        # 鼠标移出
        else:
            if cls.remove_title_bgcolor:
                e.control.bgcolor = None