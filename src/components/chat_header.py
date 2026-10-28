import flet as ft
from src.endpoints import EndPoints
from src.utils.logging import logger


class ChatHeader:
    """
    标题组件
    """

    @classmethod
    def build_blk_title_textfield(cls, session_id: str, title: str):
        """
        标题的 TextField 对象

        Args:
        - session_id: 会话ID
        - title:      标题

        Note:
        - 灰色底的实现逻辑:
          - hover_color:        未获得焦点 & 悬浮时
          - focused_bgcolor:    获得焦点时
          - bgcolor:            默认为透明, 颜色改变由 on_focus / on_blur 来切换
        - 灰色底的实现理由:
          - Flet 的 Flutter 端按 fillColor = fill_color ?? (focused ? focused_bgcolor : bgcolor) 选色
            其中 focused 是 Flutter 端维护的布尔值
            实测鼠标移出后它未必保持 true -> 灰底会消失
          - 因此 on_focus 里把 bgcolor 一起抬高, 两条机制互为兜底 (focused_bgcolor/bgcolor)
          - 不用 on_hover / on_click 事件拼状态
            实测点击落在输入框自身范围内不会失焦

        Dart 三元表达式 (Flutter 端的语言)
        fillColor = fill_color ?? (focused ? focused_bgcolor : bgcolor)
        - ??: 左边是 null 就取右边, 否则取左边
        - ?:  三元表达式: "条件 ? 真值 : 假值"
        """
        title_textfield = ft.Container(
            ft.TextField(
                value=title,
                text_style=ft.TextStyle(weight=ft.FontWeight.BOLD, size=13),
                dense=True,
                multiline=False,
                filled=True,
                bgcolor=ft.Colors.TRANSPARENT,  # 默认为透明
                hover_color=ft.Colors.GREY_200,
                focused_bgcolor=ft.Colors.GREY_200,
                border=ft.NoInputBorder(),
                content_padding=ft.Padding.symmetric(horizontal=5, vertical=5),
                data={"session_id": session_id},
                on_focus=cls.callback_title_focus,
                on_blur=cls.callback_title_edit,
            ),
            margin=ft.Margin(left=1, right=0, top=5, bottom=0),
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
        # 渲染到界面上
        EndPoints.chat["chat_header"].current.content = blk_header

    @classmethod
    def callback_title_focus(cls, e):
        """
        标题 - 获得焦点

        Note:
        - 灰色底的实现逻辑:
            - hover_color:        未获得焦点 & 悬浮时
            - focused_bgcolor:    获得焦点时
            - bgcolor:            默认为透明, 颜色改变由 on_focus / on_blur 来切换
        - 灰色底的实现理由:
            - Flet 的 Flutter 端按 fillColor = fill_color ?? (focused ? focused_bgcolor : bgcolor) 选色
            其中 focused 是 Flutter 端维护的布尔值
            实测鼠标移出后它未必保持 true -> 灰底会消失
            - 因此 on_focus 里把 bgcolor 一起抬高, 两条机制互为兜底 (focused_bgcolor/bgcolor)
            - 不用 on_hover / on_click 事件拼状态
            实测点击落在输入框自身范围内不会失焦

        Dart 三元表达式 (Flutter 端的语言)
        fillColor = fill_color ?? (focused ? focused_bgcolor : bgcolor)
        - ??: 左边是 null 就取右边, 否则取左边
        - ?:  三元表达式: "条件 ? 真值 : 假值"
        """
        # 为了兜底, 这里把 bgcolor 一起抬高, 两条机制互为兜底 (focused_bgcolor/bgcolor)
        e.control.bgcolor = ft.Colors.GREY_200
        e.control.update()

    @classmethod
    def callback_title_edit(cls, e):
        """
        标题编辑回调函数

        Note:
        - 由 on_blur 触发 (失焦即保存)
        - 失焦时把 bgcolor 恢复透明; 若此时鼠标仍悬浮, 由 hover_color 提供灰底
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
                # 立即刷新列表项
                # 只改 Python 侧属性不会自动同步到 Flutter, 不 update 的话要等下一次整体 flush(如窗口失焦) 才显示新标题
                controls[i].update()
                break
            
        # 失焦: 恢复透明底色
        e.control.bgcolor = ft.Colors.TRANSPARENT
        e.control.update()