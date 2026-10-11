import flet as ft

from src.endpoints import EndPoints


class MainView:
    """
    视图 - 主视图
    基础视图, 软件主界面的底层视图
    """
    def __init__(self):
        # 主视图对象
        self.main_view = ft.Container(
            ref=EndPoints.root["main_view"],
            expand=True,
        )