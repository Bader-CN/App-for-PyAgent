import flet as ft
from typing import Dict
from src.endpoints import EndPoints
from src.utils.logging import logger


class SettingsModelServices:
    """
    模型服务
    """

    @classmethod
    def build_blk_provider_btn_add(cls):
        """
        添加模型服务提供者按钮
        """
        blk_provider_add = ft.Button(
            content=EndPoints.runtime["app_util_lang"].translate(key="add_provider"),
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
            data={"i18n_key": "provider_add"},
            # 添加一个模型服务提供商
            on_click=cls.callback_provider_item_add
        )
        return blk_provider_add

    @classmethod
    def build_blk_provider_enable_label(cls, enable: bool):
        """
        构建启用/禁用标签

        Args:
        - enable:  是否启用的布尔值
        """
        if enable:
            return ft.Container(
                ft.Text("ON", color=ft.Colors.GREEN),
                border=ft.Border.all(color=ft.Colors.GREEN),
                border_radius=10, width=30, height=18,
                alignment=ft.Alignment.CENTER,
            )
        else:
            return ft.Container(
                ft.Text("OFF", color=ft.Colors.RED),
                border=ft.Border.all(color=ft.Colors.RED),
                border_radius=10, width=30, height=18,
                alignment=ft.Alignment.CENTER,
            )
    
    @classmethod
    def build_blk_provider_item(cls, name: str, enable: bool):
        """
        生成一个可拖拽的服务提供商实例

        Args:
        - name:     服务提供商显示名
        - enable:   是否启用
        """
        # 显示 启用/禁用
        is_enable = cls.build_blk_provider_enable_label(enable=enable)
        # 构建组件列表项
        provider = ft.ListTile(
            title=ft.Text(value=name, color=ft.Colors.BLACK, size=13),
            leading=ft.ReorderableDragHandle(
                content=ft.Icon(ft.Icons.DRAG_INDICATOR, color=ft.Colors.GREY_500),
                mouse_cursor=ft.MouseCursor.GRAB,
            ),
            trailing=is_enable,
            dense=True,
            content_padding=0,
            # 标题与 leading 和 trailing 控件之间的水平间隙
            horizontal_spacing=10,
            # 绑定事件 & 携带数据
            on_click=cls.callback_provider_details_render,
            data={"provider_name": name}
        )
        return provider

    @classmethod
    def build_blk_providers_list(cls):
        """
        构建一个包含已有服务提供者的列表
        """
        # 获取服务提供商
        all_providers = EndPoints.runtime["app_util_conf"].providers_dict()
        # 构建列表
        blk_all_providers = ft.ReorderableListView(
            show_default_drag_handles=False,
            controls=[
                cls.build_blk_provider_item(name=key, enable=val.get("enable"))
                for key, val in all_providers.items()
            ],
            ref=EndPoints.settings["providers_list"],
            on_reorder=cls.callback_providers_reorder,
        )
        return blk_all_providers
    
    @classmethod
    def build_blk_model_item(cls, provider_model: Dict):
        """
        添加一个可拖动项到模型服务列表中
        provider_model 字典格式为:
        {
            'provider': 'provider_name', 
            'model_id': 'model_id', 
            'model_name': 'model_name', 
            'model_feats': {
                'vision': False, 
                'embed': False, 
                'reranker': False,
            }
        }

        Args:
        - provider_model:   模型配置字典
        """
        # 模型能力对应的标签
        skills = []
        for skill in ["vision", "embed", "reranker"]:
            if provider_model["model_feats"].get(skill):
                skill_item = ft.Container(
                    content=ft.Text(
                        value=EndPoints.runtime["app_util_lang"].translate(key=f"model_{skill}"),
                        size=12,
                        color=ft.Colors.GREY_700,
                    ),
                    border=ft.Border.all(color=ft.Colors.GREY_700),
                    border_radius=10,
                    width=60,
                    height=20,
                    alignment=ft.Alignment.CENTER,
                )
                skills.append(skill_item)
        # 可拖动的模型列表
        blk_model = ft.ListTile(
            title=ft.Row(
                [
                    # data 用于编辑/删除时按 model_id 定位控件
                    ft.Text(provider_model.get("model_name"), size=13, data={"model_id": provider_model.get("model_id")}),
                    ft.Container(expand=True),
                    *skills,        # 解包
                    ft.Container(), # 用于占位
                ],
                
            ),
            dense=True,
            content_padding=5,
            horizontal_spacing=0,   # 标题与 leading 和 trailing 控件之间的水平间隙
            leading=ft.ReorderableDragHandle(
                content=ft.Icon(
                    ft.Icons.DRAG_INDICATOR, 
                    color=ft.Colors.GREY_500,
                    size=18,
                ),
                mouse_cursor=ft.MouseCursor.GRAB,
            ),
            trailing=ft.Row(
                controls=[
                    # 修改模型配置
                    ft.IconButton(
                        ft.Icons.EDIT_SQUARE,
                        icon_size=18,
                        width=24,
                        height=24,
                        padding=0,
                        on_click=cls.callback_model_edit,
                        data={"provider_model": provider_model}
                    ),
                    # 删除模型
                    ft.IconButton(
                        ft.Icons.CANCEL,
                        icon_size=18,
                        width=24,
                        height=24,
                        padding=0,
                        on_click=cls.callback_model_del,
                        data={"provider_model": provider_model}
                    ),
                ],
                # 是否紧密
                tight=True,
                spacing=0,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        )
        return blk_model

    @classmethod
    def callback_provider_item_add(cls, e):
        """
        添加一个模型服务提供商
        """
        # 获取当前所有的模型服务提供商
        all_providers = EndPoints.runtime["app_util_conf"].providers_dict()
        # 生成一个新的唯一的名称
        id = 1
        prefix = "new_provider_"
        while all_providers.get(f"{prefix}{id}") is not None:
            id += 1
        # 渲染界面
        EndPoints.settings["providers_list"].current.controls.append(
            cls.build_blk_provider_item(name=f"{prefix}{id}", enable=False)
        )
        # 添加 & 保存配置
        EndPoints.runtime["app_util_conf"].provider_add(provider_name=f"{prefix}{id}")
    
    @classmethod
    def callback_provider_item_del(cls, e):
        """
        删除供应商
        """
        provider_name = e.control.data.get("provider_name")
        # 删除指定供应商数据
        EndPoints.runtime["app_util_conf"].provider_del(provider_name=provider_name)
        # 同步最后一次点击
        EndPoints.runtime["last_provider_name"] = None
        # 更新界面
        EndPoints.settings["lv3_view"].current.content.controls.clear()
        controls = EndPoints.settings["providers_list"].current.controls
        for i, control in enumerate(controls):
            if control.title.value == provider_name:
                controls.pop(i)
                break

    @classmethod
    def callback_provider_details_render(cls, e: None | ft.Event = None, provider_name: None | str = None):
        """
        渲染供应商详情

        Args:
        - e: ft.Event, 通过 e.control.data.get("provider_name") 可以获取模型服务提供商的名字
        - provider_name: str, 模型服务提供商的名字

        Note:
        - e 和 provider_name 二选一, 两者互斥, 有且仅有一个是 None
        - 点击 ListTile 触发时传 e (provider_name 从 e.control.data 提取)
        - 其余调用时直接传 provider_name (e 不传)
        - 无论从哪条路径进来, 都以本次渲染的名字为准同步 last_provider_name,
          避免各处手动维护导致漂移 (改名后重建需要依赖这一点)
        """
        # 模型服务提供商的名字
        if e is not None:
            provider_name = e.control.data.get("provider_name")
        # 将 "模型服务提供商" 更新至全局变量中
        EndPoints.runtime["last_provider_name"] = provider_name
        # 基于 "模型服务提供商" 来获取当前的 provider_dict
        provider_dict = EndPoints.runtime["app_util_conf"].provider_dict(provider_name)
        # 标题组件
        blk_title = ft.Container(
            content=ft.Row(
                controls=[
                    # 服务提供商的名字
                    ft.Container(
                        content=ft.TextField(
                            value=f"{provider_name}",
                            text_style=ft.TextStyle(weight=ft.FontWeight.BOLD),
                            multiline=False,
                            dense=True,
                            ############################################################
                            # filled: 输入框「装饰容器」的底色总开关
                            # - 定义不在 TextField 上, 而在基类 FormFieldControl 里 (flet/controls/material/form_field_control.py)
                            #   所以翻 TextField 文档找不到
                            # - 值为 False 时, bgcolor / focused_bgcolor / hover_color / fill_color 全部不生效
                            #   这几个字段的 docstring 统一写着 "Will not be visible if filled is False"
                            # - 下面这套灰底正是靠 hover_color / focused_bgcolor 画出来的, 因此必须打开
                            # - 注意: Flet 1.x 的 TextField.before_update 会在 filled is None
                            #   且上述某个颜色非 None 时自动置 True, 所以本行在当前版本下是冗余的
                            #   显式写出是为了让「必须有底色容器」这个意图在代码里自解释, 不依赖隐式行为
                            filled=True,
                            ############################################################
                            # 灰色底的实现逻辑:
                            # - hover_color:        未获得焦点 & 悬浮时
                            # - focused_bgcolor:    获得焦点时
                            # - bgcolor:            默认为透明, 颜色改变由 on_focus / on_blur 来切换
                            # - 灰色底的实现理由:
                            #   - Flet 的 Flutter 端按 fillColor = fill_color ?? (focused ? focused_bgcolor : bgcolor) 选色
                            #     其中 focused 是 Flutter 端维护的布尔值
                            #     实测鼠标移出后它未必保持 true -> 灰底会消失
                            #   - 因此 on_focus 里把 bgcolor 一起抬高, 两条机制互为兜底 (focused_bgcolor/bgcolor)
                            #   - 不用 on_hover / on_click 事件拼状态
                            #     实测点击落在输入框自身范围内不会失焦
                            #
                            # Dart 三元表达式 (Flutter 端的语言)
                            # fillColor = fill_color ?? (focused ? focused_bgcolor : bgcolor)
                            # - ??: 左边是 null 就取右边, 否则取左边
                            # - ?:  三元表达式: "条件 ? 真值 : 假值"
                            bgcolor=ft.Colors.TRANSPARENT,
                            hover_color=ft.Colors.GREY_200,
                            focused_bgcolor=ft.Colors.GREY_200,
                            on_focus=cls.callback_provider_name_focus,
                            on_blur=cls.callback_provider_name_edit,
                            ############################################################
                            content_padding=ft.Padding(left=2, top=5, right=2, bottom=5),
                            margin=0,
                            border=ft.NoInputBorder(),
                            data={"provider_name": provider_name},
                        ),
                    ),
                    ft.Container(expand=True),
                    # API 类型
                    ft.PopupMenuButton(
                        # 鼠标悬浮时显示的内容
                        # https://flet.dev/docs/controls/control
                        tooltip=EndPoints.runtime["app_util_lang"].translate(key="api_type"),
                        items=[
                            ft.PopupMenuItem(
                                content=protocol,
                                on_click=cls.callback_provider_api_type_edit,
                                label_text_style=ft.TextStyle(size=13, color=ft.Colors.BLACK),
                                data={"provider_name": provider_name, "api_type": protocol},
                                height=32,
                            )
                            for protocol in EndPoints.runtime["llm_protocol"]
                        ],
                        menu_position=ft.PopupMenuPosition.UNDER,
                        content=ft.Container(
                            content=ft.Text(value=provider_dict.get("api_type"), size=13),
                            border=ft.Border.all(color=ft.Colors.GREY),
                            border_radius=10,
                            width=112,
                            height=22,
                            alignment=ft.Alignment.CENTER,
                            ref=EndPoints.settings["provider_api_type"],
                        ),
                    ),
                    # 删除按钮
                    ft.IconButton(
                        icon=ft.Icons.CANCEL,
                        padding=0,
                        height=28,
                        width=28,
                        on_click=cls.callback_provider_item_del,
                        data={"provider_name": provider_name},
                        ref=EndPoints.settings["provider_del_btn"],
                    ),
                    # 是否启用该模型提供商
                    ft.Switch(
                        height=28,
                        value=provider_dict.get("enable"),
                        on_change=cls.callback_provider_switch_btn_toggle,
                        data={"provider_name": provider_name},
                    ),
                ],
                spacing=5,
            ),
        )
        # 通用组件
        blk_common = ft.Container(
            content=ft.Column(
                controls=[
                    # API URL
                    ft.Text(
                        value=EndPoints.runtime["app_util_lang"].translate(key="api_url"), 
                    ),
                    ft.TextField(
                        value=EndPoints.runtime["app_util_conf"].provider_api_url(provider_name=provider_name),
                        text_size=13,
                        hint_text="http://<api_base_url>:<port>/v1",
                        dense=True,
                        expand=True,
                        expand_loose=True,
                        content_padding=ft.Padding(left=0, top=5, right=0, bottom=5),
                        text_style=ft.TextStyle(size=14),
                        on_blur=cls.callback_provider_api_url_save,
                        data={"provider_name": provider_name},
                    ),
                    # API KEY
                    ft.Text(
                        value=EndPoints.runtime["app_util_lang"].translate(key="api_key"), 
                    ),
                    ft.TextField(
                        value=EndPoints.runtime["app_util_conf"].provider_api_key(provider_name=provider_name),
                        text_size=13,
                        dense=True,
                        expand=True,
                        expand_loose=True,
                        content_padding=ft.Padding(left=0, top=5, right=0, bottom=5),
                        text_style=ft.TextStyle(size=14),
                        on_blur=cls.callback_provider_api_key_save,
                        data={"provider_name": provider_name},
                        password=True,
                    ),
                ],
            ),
        )
        # 模型组件
        blk_models = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(value=EndPoints.runtime["app_util_lang"].translate(key="models")),
                            ft.Container(expand=True),
                            # 添加模型按钮
                            ft.Button(
                                content=EndPoints.runtime["app_util_lang"].translate(key="add_model"),
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                                height=30,
                                on_click=cls.callback_model_add_dialog,
                            ),
                        ],
                    ),
                    ft.Container(
                        content = ft.ReorderableListView(
                            controls=[
                                # build_blk_model_item 的字典数据里需要一个 "provider" 字段
                                # 由于 provider_data 里不存在, 因此通过此方式构造一个字典来包含此字段 {**model, "provider": provider_name}
                                # "*": 将多个值打包成 "元组(tuple)" 或从元组/列表中解包
                                # "**": 将多个值打包成 "字典(dict)" 或从字典中解包
                                cls.build_blk_model_item(provider_model={**model, "provider": provider_name})
                                # 如果没有获取到 "models" 字段, 则返回一个空列表
                                for model in provider_dict.get("models", [])
                            ],
                            show_default_drag_handles=False,
                            ref=EndPoints.settings["provider_models"],
                            on_reorder=cls.callback_models_reorder,
                        ),
                        border=ft.Border.all(),
                        border_radius=4,
                        expand=True,
                    ),
                ],
            ),
            expand=True,
        )
        # 组装组件
        # ===============================
        # 防止 ft.Ref 弱引用 产生的 GC 陷阱
        # 若新旧子树的值相等, Prop.__set__ 会跳过存储, 导致新子树无强引用被 GC, ref 失效变 None
        # 解决方法是先置 None 把已存储的旧值弹出, 下一次赋值才会真正存储
        # ===============================
        EndPoints.settings["lv3_view"].current.content = None
        EndPoints.settings["lv3_view"].current.content = ft.Column(
            controls=[
                blk_title,
                ft.Divider(height=1),
                blk_common,
                blk_models,
            ],
        )
        # 指定强引用, 这几个组件可能会被 GC 掉
        EndPoints.views["settings_view"].blk_models = blk_models

    @classmethod
    def callback_provider_api_url_save(cls, e):
        """
        保存供应商 API URL
        """
        provider_name = e.control.data.get("provider_name")
        new_api_url = e.control.value.strip()
        now_api_url = EndPoints.runtime["app_util_conf"].provider_api_url(provider_name=provider_name)
        if new_api_url != now_api_url:
            EndPoints.runtime["app_util_conf"].provider_api_url_set(
                provider_name=provider_name,
                api_url=new_api_url,
            )

    @classmethod
    def callback_provider_api_key_save(cls, e):
        """
        保存供应商 API Key
        """
        provider_name = e.control.data.get("provider_name")
        new_api_key = e.control.value.strip()
        now_api_key = EndPoints.runtime["app_util_conf"].provider_api_key(provider_name=provider_name)
        if new_api_key != now_api_key:
            EndPoints.runtime["app_util_conf"].provider_api_key_set(
                provider_name=provider_name,
                api_key=new_api_key,
            )

    @classmethod
    def callback_provider_api_type_edit(cls, e):
        """
        供应商 API 的协议类型
        """
        provider_name = e.control.data.get("provider_name")
        api_type = e.control.data.get("api_type")
        # 更新数据
        provider_data = EndPoints.runtime["app_util_conf"].provider_dict(provider_name=provider_name)
        provider_data["api_type"] = api_type
        EndPoints.runtime["app_util_conf"].conf_save()
        # 刷新界面
        blk_api_type = EndPoints.settings["provider_api_type"].current
        blk_api_type.content = ft.Text(value=api_type)
        # 只改 Python 侧属性不会自动同步到 Flutter (该容器不是本次事件的 e.control)
        blk_api_type.update()

    @classmethod
    def callback_provider_name_focus(cls, e):
        """
        供应商名字(标题) - 获得焦点

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
    def callback_provider_name_edit(cls, e):
        """
        供应商名字(标题) - 修改

        Note:
        - 由 on_blur 触发 (失焦即保存)
        - 失焦时把 bgcolor 恢复透明; 若此时鼠标仍悬浮, 由 hover_color 提供灰底
        - 名字确实变化时重建整个详情区
          -> 标题 / API URL / API Key / API 类型菜单项的 data["provider_name"] 都只在这一处绑定, 重建即可全部换成新名字
        - 重建后 e.control 已脱离控件树, 再 update() 会抛 RuntimeError, 因此提前 return
        """
        # 检查数据
        old_name = e.control.data.get("provider_name")
        new_name = e.control.value
        
        # 名字未变: 只恢复底色
        if old_name == new_name:
            e.control.bgcolor = ft.Colors.TRANSPARENT
            e.control.update()
            return
        
        # 先把自身 data 改名, 防止重建过程中再次派发 blur 时重复处理
        e.control.data["provider_name"] = new_name
        # 遍历供应商列表, 更新名字
        controls = EndPoints.settings["providers_list"].current.controls
        for control in controls:
            if control.title.value == old_name:
                # 同步拖拽对象的 value / data
                control.title.value = new_name
                control.data["provider_name"] = new_name
                # 只改 Python 侧属性不会自动同步到 Flutter, 不 update 的话要等下一次整体 flush(如窗口失焦) 才显示新名字
                control.update()
                break
        # 保存数据
        # providers 是 conf 字典内部的引用, 必须原地 pop + 赋值才能写回正确顺序
        providers = EndPoints.runtime["app_util_conf"].providers_dict()
        providers[new_name] = providers.pop(old_name)
        EndPoints.runtime["app_util_conf"].conf_save()
        # 重建详情区 (内部会同步 last_provider_name)
        cls.callback_provider_details_render(provider_name=new_name)
        # 详情区是兄弟节点, 不是本次事件的 e.control, 需显式刷新
        EndPoints.settings["lv3_view"].current.update()

    @classmethod
    def callback_provider_switch_btn_toggle(cls, e):
        """
        供应商 启用/禁用 按钮
        """
        provider_name = e.control.data.get("provider_name")
        provider_data = EndPoints.runtime["app_util_conf"].provider_dict(provider_name=provider_name)
        # 取反 & 保存
        provider_data["enable"] = not provider_data["enable"]
        EndPoints.runtime["app_util_conf"].conf_save()
        # 更新界面
        controls = EndPoints.settings["providers_list"].current.controls
        for control in controls:
            if control.data.get("provider_name") == provider_name:
                # 直接更新 trailing 属性, 不替换整个 ListTile
                # 在 Flet 1.0.x 下, 直接替换无法正常刷新
                control.trailing = cls.build_blk_provider_enable_label(enable=provider_data["enable"])
                control.update()
                break

    @classmethod
    def callback_providers_reorder(cls, e: ft.OnReorderEvent):
        """
        重新排序模型服务提供商列表

        Note: 如果存在界面渲染和实际数据不同步的情况, 可以参考一下 callback_models_reorder 方法中的逻辑, 确保界面和数据强制同步
        """
        # 获取当前所有的模型服务提供商字典
        all_providers = EndPoints.runtime["app_util_conf"].providers_dict()
        # 重新排序模型服务提供商字典
        keys = list(all_providers.keys())
        keys.insert(e.new_index, keys.pop(e.old_index)) # 将 value 在给定的 index 位置插入到 sequence 中: sequence.insert(index, value, /)
        # 按新 key 顺序重建字典
        reordered = {k: all_providers[k] for k in keys}
        # all_providers 是 self.app_conf_dict["model_providers"] 的引用
        # 必须 clear()+update() 原地修改, 不能直接赋值新字典
        # 否则 self.app_conf_dict 仍指向旧对象, conf_save() 写出的顺序不变
        all_providers.clear()
        all_providers.update(reordered)
        # 保存排序后的配置
        EndPoints.runtime["app_util_conf"].conf_save()

    @classmethod
    def callback_model_add_dialog(cls, e):
        """
        添加模型 - 对话框

        Note: 
        - 此处使用到了 var := xxx 的语法糖 (海象运算符)
        - 赋值的同时将值返回
        """
        add_model_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(EndPoints.runtime["app_util_lang"].translate(key="add_model")),
            content=ft.Column(
                controls=[
                    # 模型标识ID
                    ft.Text(value=EndPoints.runtime["app_util_lang"].translate(key="model_id")),
                    model_id:=ft.TextField(
                        hint_text=EndPoints.runtime["app_util_lang"].translate(key="model_id_desc"),
                        text_style=ft.TextStyle(size=14),
                        dense=True,
                    ),
                    # 模型显示名
                    ft.Text(value=EndPoints.runtime["app_util_lang"].translate(key="model_name")),
                    model_name:=ft.TextField(
                        hint_text=EndPoints.runtime["app_util_lang"].translate(key="model_name_desc"),
                        text_style=ft.TextStyle(size=14),
                        dense=True,
                    ),
                    # 模型能力
                    ft.Text(value=EndPoints.runtime["app_util_lang"].translate(key="model_ability")),
                    ft.Row(
                        controls=[
                            # 视觉
                            vision:=ft.Checkbox(
                                label=EndPoints.runtime["app_util_lang"].translate(key="model_vision"),
                                visual_density=ft.VisualDensity.COMPACT,
                            ),
                            # 嵌入
                            embed:=ft.Checkbox(
                                label=EndPoints.runtime["app_util_lang"].translate(key="model_embed"),
                                visual_density=ft.VisualDensity.COMPACT,
                            ),
                            # 重排
                            reranker:=ft.Checkbox(
                                label=EndPoints.runtime["app_util_lang"].translate(key="model_reranker"),
                                visual_density=ft.VisualDensity.COMPACT,
                            ),
                        ],
                    ),
                ],
                height=240,
            ),
            actions=[
                ft.TextButton(
                    EndPoints.runtime["app_util_lang"].translate(key="cancel"), 
                    on_click=EndPoints.root["page"].pop_dialog,
                ),
                ft.TextButton(
                    EndPoints.runtime["app_util_lang"].translate(key="save"), 
                    on_click=cls.callback_model_add_save,
                    # 这里只传递对象, 不传递数据的原因是因为这里无法传值 (只会传递默认值)
                    data={
                        "model_id_obj": model_id,
                        "model_name_obj": model_name,
                        "model_feats_obj": {"vision": vision, "embed": embed, "reranker": reranker}
                    },
                ),
            ],
            # 建立引用
            ref=EndPoints.root["add_model_dialog"],
        )
        EndPoints.root["page"].show_dialog(add_model_dialog)

    @classmethod
    def callback_model_add_save(cls, e):
        """
        保存新增的模型配置
        """
        # 获取数据
        src_data = e.control.data
        provider = EndPoints.runtime["last_provider_name"]
        model_id = src_data.get("model_id_obj").value.strip()
        model_name = src_data.get("model_name_obj").value.strip()
        model_vision = src_data.get("model_feats_obj").get("vision").value
        model_embed = src_data.get("model_feats_obj").get("embed").value
        model_reranker = src_data.get("model_feats_obj").get("reranker").value

        # 准备检查
        controls = EndPoints.root["add_model_dialog"].current.content.controls
        alertext = None
        provider_dict = EndPoints.runtime["app_util_conf"].provider_dict(provider_name=provider)

        # 情况1: Model ID 或 Model Name 为空
        if model_id == "" or model_name == "":
             alertext = ft.Text(EndPoints.runtime["app_util_lang"].translate(key="add_model_warn_none"), color=ft.Colors.RED)
             logger.warning("Model ID or Model Name cannot be empty!")
        # 情况2: Model ID 或 Model Name 重复
        if provider_dict.get("models") is not None:
            for model in provider_dict.get("models"):
                if model_id == model.get("model_id") or model_name == model.get("model_name"):
                    alertext = ft.Text(EndPoints.runtime["app_util_lang"].translate(key="add_model_warn_unique"), color=ft.Colors.RED)
                    logger.warning("Model ID or Model Name must be unique!")
        
        # 数据非法: 渲染提示
        if alertext:
            if type(controls[-1]) is ft.Row:
                controls.append(alertext)
            else:
                controls[-1] = alertext
        # 数据合法: 更新数据
        else:
            provider_model = {
                "provider": provider,
                "model_id": model_id,
                "model_name": model_name,
                "model_feats": {
                    "vision": model_vision,
                    "embed": model_embed,
                    "reranker": model_reranker,
                },
            }
            # 保存到 config.yaml 中
            EndPoints.runtime["app_util_conf"].provider_models_add(provider_model=provider_model)
            # 更新界面
            new_model = cls.build_blk_model_item(provider_model=provider_model)
            EndPoints.settings["provider_models"].current.controls.append(new_model)
            # 推出弹框
            EndPoints.root["page"].pop_dialog()
            EndPoints.root["page"].update()

    @classmethod
    def callback_model_del(cls, e):
        """
        删除指定模型
        """
        # 提取数据
        provider_model = e.control.data.get("provider_model")
        provider = provider_model.get("provider")
        model_id = provider_model.get("model_id")
        model_name = provider_model.get("model_name")
        # 从 config.yaml 中删除
        EndPoints.runtime["app_util_conf"].provider_models_del(provider=provider, model_id=model_id)
        # 更新界面
        controls = EndPoints.settings["provider_models"].current.controls
        for control in controls:
            if type(control.title.controls[0]) is ft.Text and control.title.controls[0].value == model_name:
                controls.remove(control)
                break

    @classmethod
    def callback_model_edit(cls, e):
        """
        修改指定模型
        """
        # 提取数据
        provider_model = e.control.data.get("provider_model")
        old_model_name = provider_model.get("model_name")
        # 生成一个弹框
        edit_model_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(EndPoints.runtime["app_util_lang"].translate(key="edit_model")),
            content=ft.Column(
                controls=[
                    # 模型标识ID
                    ft.Text(value=EndPoints.runtime["app_util_lang"].translate(key="model_id")),
                    model_id:=ft.TextField(
                        value=provider_model.get("model_id"),
                        hint_text=EndPoints.runtime["app_util_lang"].translate(key="model_id_desc"),
                        text_style=ft.TextStyle(size=14),
                        dense=True,
                        disabled=True,
                        color=ft.Colors.GREY_800,
                    ),
                    # 模型显示名
                    ft.Text(value=EndPoints.runtime["app_util_lang"].translate(key="model_name")),
                    model_name:=ft.TextField(
                        value=provider_model.get("model_name"),
                        hint_text=EndPoints.runtime["app_util_lang"].translate(key="model_name_desc"),
                        text_style=ft.TextStyle(size=14),
                        dense=True,
                    ),
                    # 模型能力
                    ft.Text(value=EndPoints.runtime["app_util_lang"].translate(key="model_ability")),
                    ft.Row(
                        controls=[
                            # 视觉
                            vision:=ft.Checkbox(
                                value=provider_model["model_feats"].get("vision"),
                                label=EndPoints.runtime["app_util_lang"].translate(key="model_vision"),
                                visual_density=ft.VisualDensity.COMPACT,
                            ),
                            # 嵌入
                            embed:=ft.Checkbox(
                                value=provider_model["model_feats"].get("embed"),
                                label=EndPoints.runtime["app_util_lang"].translate(key="model_embed"),
                                visual_density=ft.VisualDensity.COMPACT,
                            ),
                            # 重排
                            reranker:=ft.Checkbox(
                                value=provider_model["model_feats"].get("reranker"),
                                label=EndPoints.runtime["app_util_lang"].translate(key="model_reranker"),
                                visual_density=ft.VisualDensity.COMPACT,
                            ),
                        ],
                    ),
                ],
                height=240,
            ),
            actions=[
                ft.TextButton(
                    EndPoints.runtime["app_util_lang"].translate(key="cancel"), 
                    on_click=EndPoints.root["page"].pop_dialog,
                ),
                ft.TextButton(
                    EndPoints.runtime["app_util_lang"].translate(key="save"), 
                    on_click=cls.callback_model_edit_save,
                    # 这里只传递对象, 不传递数据的原因是因为这里无法传值 (只会传递默认值)
                    data={
                        "model_id_obj": model_id,
                        "model_name_obj": model_name,
                        "model_feats_obj": {"vision": vision, "embed": embed, "reranker": reranker},
                        # 追加一个没有修改过的 model_name
                        "old_model_name": old_model_name,
                    },
                ),
            ],
            # 建立引用
            ref=EndPoints.root["edit_model_dialog"],
        )
        EndPoints.root["page"].show_dialog(edit_model_dialog)

    @classmethod
    def callback_model_edit_save(cls, e):
        """
        保存修改后的模型配置
        """
        # 获取数据
        src_data = e.control.data
        provider = EndPoints.runtime["last_provider_name"]
        model_id = src_data.get("model_id_obj").value.strip()
        model_name = src_data.get("model_name_obj").value.strip()
        model_vision = src_data.get("model_feats_obj").get("vision").value
        model_embed = src_data.get("model_feats_obj").get("embed").value
        model_reranker = src_data.get("model_feats_obj").get("reranker").value
        old_model_name = src_data.get("old_model_name")

        # 准备检查
        controls = EndPoints.root["edit_model_dialog"].current.content.controls
        alertext = None
        provider_dict = EndPoints.runtime["app_util_conf"].provider_dict(provider_name=provider)

        # 情况1: Model Name 为空
        if model_name == "":
            alertext = ft.Text(EndPoints.runtime["app_util_lang"].translate(key="edit_model_warn_none"), color=ft.Colors.RED)
            logger.warning("Model Name cannot be empty!")
        # 情况2: Model ID 或 Model Name 重复
        if provider_dict.get("models") is not None:
            for model in provider_dict.get("models"):
                if model_name == model.get("model_name") and model_name != old_model_name:
                    alertext = ft.Text(EndPoints.runtime["app_util_lang"].translate(key="edit_model_warn_unique"), color=ft.Colors.RED)
                    logger.warning("Model Name must be unique!")
                    break

        # 数据非法: 渲染提示
        if alertext:
            if type(controls[-1]) is ft.Row:
                controls.append(alertext)
            else:
                controls[-1] = alertext

        # 数据合法: 更新数据
        else:
            provider_model = {
                "provider": provider,
                "model_id": model_id,
                "model_name": model_name,
                "model_feats": {
                    "vision": model_vision,
                    "embed": model_embed,
                    "reranker": model_reranker,
                },
            }
            # 保存到 config.yaml 中
            EndPoints.runtime["app_util_conf"].provider_models_edit(provider_model=provider_model)
            # 更新界面
            edit_model = cls.build_blk_model_item(provider_model=provider_model)
            for i, control in enumerate(EndPoints.settings["provider_models"].current.controls):
                if control.title.controls[0].data.get("model_id") == model_id:
                    EndPoints.settings["provider_models"].current.controls[i] = edit_model
                    break
            # 推出弹框
            EndPoints.root["page"].pop_dialog()
            EndPoints.root["page"].update()

    @classmethod
    def callback_models_reorder(cls, e: ft.OnReorderEvent):
        """
        模型排序回调函数, 用于处理模型的显示顺序
        """
        # 获取当前模型列表
        provider_name = EndPoints.runtime["last_provider_name"]
        provider_dict = EndPoints.runtime["app_util_conf"].provider_dict(provider_name=provider_name)
        models = provider_dict.get("models")
        # 如果获取不到则直接结束
        if models is None:
            return
        # 重新排序模型列表
        # 注意: 此处不能用交换元素, 因为是拖拽, 位置变更后其余位置也会变化, 因此这里是 Move
        item = models.pop(e.old_index)      # 从指定 index 上取出元素
        models.insert(e.new_index, item)    # 在指定 index 上塞入元素, 在此之后的所有元素均向后移动一位
        # 强制刷新界面, 确保同步(去掉会有概率出现配置和界面不同步的现象)
        controls = EndPoints.settings["provider_models"].current.controls
        if controls:
            item_ctrl = controls.pop(e.old_index)
            controls.insert(e.new_index, item_ctrl)
        # 保存排序后的配置
        EndPoints.runtime["app_util_conf"].conf_save()