import flet as ft


class EndPoints:
    """
    Flet GUI 暴露的端点类, 用于保存需要跨通信的组件对象
    
    注意:
    1. 不要在 class 的 init 阶段调用 root["page"], 由于导入顺序的原因, 此时导入会得到 None
    2. 所有 ft.Ref 引用对象在引用时需要添加 .current
       详情请参考 https://flet.dev/docs/cookbook/control-refs#ref-class
    """
    # 根节点对象
    root = {
        "page": None,
        "add_model_dialog": ft.Ref[ft.AlertDialog](),
        "edit_model_dialog": ft.Ref[ft.AlertDialog](),
        "navigation": ft.Ref[ft.Container](),
        "main_view": ft.Ref[ft.Container](),
    }

    # 输入界面
    input = {
        "input_panel": ft.Ref[ft.Container](),
        "input_attachments": ft.Ref[ft.Row](),
        "input_textfield": ft.Ref[ft.TextField](),
        "input_model_select": ft.Ref[ft.Text](),
        "input_model_reason": ft.Ref[ft.Text](),
        "input_send_btn": ft.Ref[ft.IconButton](),
    }

    # 对话界面
    chat = {
        "lv1_view": ft.Ref[ft.Container](),
        "lv2_view": ft.Ref[ft.Container](),
        "chat_view": ft.Ref[ft.Row](),
        "chat_list": ft.Ref[ft.ReorderableListView](),
        "chat_header": ft.Ref[ft.Container](),
        "chat_body": ft.Ref[ft.Container](),
    }

    # 设置界面
    settings = {
        "lv1_view": ft.Ref[ft.Container](),
        "lv2_view": ft.Ref[ft.Container](),
        "lv3_view": ft.Ref[ft.Container](),
        "settings_view": ft.Ref[ft.Row](),
        "switch_language": ft.Ref[ft.Text](),
        "default_chat_model": ft.Ref[ft.Text](),
        "default_agent_model": ft.Ref[ft.Text](),
        "default_summary_model": ft.Ref[ft.Text](),
        "default_translation_model": ft.Ref[ft.Text](),
        "providers_list": ft.Ref[ft.ReorderableListView](),
        "provider_models": ft.Ref[ft.ReorderableListView](),
        "provider_api_type": ft.Ref[ft.Container](),
        "provider_del_btn": ft.Ref[ft.IconButton](),
    }

    # 视图对象
    views = {
        "main_view": None,
        "chat_view": None,
        "navigation_view": None,
        "settings_view": None,
    }

    # 运行时的全局变量
    runtime = {
        # 应用运行时的根目录
        "app_path_root": None,
        # 应用运行时的配置实例对象
        "app_util_conf": None,
        # 应用运行时的语言管理工具
        # translate(key=<tag>)
        "app_util_lang": None,
        # 应用运行时的缓存实例对象
        "app_util_cache": None,
        # 用户的配置文件
        "app_util_profile": None,
        # 应用运行时的文件数据工具实例
        # data_read(data_type: str) -> "sort_chat", "sort_agent"
        "app_util_filedata": None,
        # 应用运行时的语言
        "app_language": None,
        # 支持的协议
        "llm_protocol": ["OpenAI", "Ollama"],
        # 设置界面最后点击的提供商详情
        "last_provider_name": None,
        # LangChain 智能体类的实例对象
        "lc_agents": None,
        # 标记位: 会话ID
        "session_id_chat_current": None,
        "session_id_chat_last": None,       # 用于判断是否在重复点击 & 再次切换会话界面是渲染哪条会话
        "session_id_agent_current": None,
        "session_id_agent_last": None,      # 主要用于判断是否在重复点击 & 再次切换智能体界面是渲染哪条智能体对话
    }

    # 临时消息缓存
    # -> 仅保留最后一次的流式记录, 用于流式更新
    # -> 数据结构为字典, key 为 session_id, value 为消息字典
    ##############################################################
    # {
    #   session_id_chat:  {
    #       "status": "start/stop/error/aborted/reasoning/tool_call/text", 
    #       "aimsgs": [
    #           {
    #               "type": "reasoning/tool_call/text",
    #               "reasoning" / "tool_call" / "text": ....
    #           },
    #       ],
    #       "reason": None,
    #       "click_count": 1,
    #       "rendered_click_count": 1,
    #   },
    #   session_id_agent: {
    #       "status": "start/stop/error/aborted/reasoning/tool_call/text", 
    #       "aimsgs": [
    #           {
    #               "type": "reasoning/tool_call/text",
    #               "reasoning" / "tool_call" / "text": ....
    #           },
    #       ],
    #       "reason": None,
    #       "click_count": 1,
    #       "rendered_click_count": 1,
    #   },
    # }
    ##############################################################
    tmp_msgs = {}