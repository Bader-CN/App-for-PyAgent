# AGENTS.md

Flet 桌面应用，通过 LangChain（DeepAgents 待接入）与 LLM 对话，纯 Python。

## Run

```shell
flet run -r src/main.py      # dev, 热重载（从仓库根目录运行）
flet run src/main.py         # 演示
```

- 入口 `src/main.py` → `ft.run(main)`；启动时把仓库根加入 `sys.path`，所有模块用绝对导入 `from src.xxx import ...`。
- `pyproject.toml` 是依赖与 Flet 配置的唯一来源：`[tool.flet.app] path = "src"` 指定应用目录，构建产物 `.flet/` 生成在 `src/` 下。
- 测试：`python -m pytest tests/ -v`；`[tool.pytest.ini_options].pythonpath = ["."]`（绝对导入要求仓库根在 `sys.path`），`asyncio_mode = "auto"`。
- **LangChain OpenAI 的 `reasoning_content` 支持已内置于仓库**（`src/cores/lc_hotfix_openai.py`），无需再改 site-packages；README 里的手工 patch 是等价说明。

## 设计基调

- **目标用户：自己 + 懂 LLM 的人**，不是纯小白。一切设计以此为出发点。
- **宁简勿繁：** 每加一层 UI（弹框、确认步骤、向导），先问"对我自己真的必要吗？"
- **直接操作 > 模态阻断：** 能用内联编辑就内联，能用拖拽排序就拖拽，弹框是最后的选择。
- **这是个人学习项目：** 探索和讨论本身就是目的，架构决策可以改、可以重构。

## 核心架构：EndPoints 通信枢纽

**禁止 import 环，禁止直接 import 有状态实例。** 跨组件通信（读别人的 ref / View / 运行时数据）通过 `src/endpoints.py` 的 `EndPoints` 类查表完成。

| 对象 | 做法 | 示例 |
|---|---|---|
| **无状态行为**（`@classmethod` / 纯函数） | **直接 import**（Python import 本身即查表） | `MessageBlockCommon.build_blk_user_msg`、`AlertCommon.alert_model_config_error` |
| **有状态实例 / `ft.Ref` / View** | 走 `EndPoints` | `EndPoints.chat["chat_body"]`、`EndPoints.views["settings_view"]` |
| **可变全局数据** | 走 `EndPoints.runtime` | `EndPoints.runtime["app_util_lang"]` |

**无环是硬约束**（import 环是唯一硬伤）：被多处 import 的无状态模块，自己**不得反向 import** 任何 `src/components/*` 或 `src/views/*`；需要反向触发就改走 `EndPoints` ref。

```python
EndPoints.root["page"]             # ft.Page 对象
EndPoints.root["main_view"]        # ft.Ref[ft.Container]
EndPoints.chat["chat_view"]        # ft.Ref[ft.Row]
EndPoints.input["input_send_btn"]  # ft.Ref[ft.IconButton]
EndPoints.settings["switch_language"]  # ft.Ref[ft.Text]
EndPoints.runtime["session_id_chat_current"]  # 当前 chat 会话 ID
EndPoints.runtime["app_util_lang"].translate(key="xxx")  # 翻译
```

- `EndPoints.views["settings_view"]` 是 **View 实例**（可调 `.render_full()`）；`EndPoints.settings["settings_view"]` 是该 View 内 `ft.Ref[ft.Row]`（控件本体），二者不同。
- `EndPoints.input[...]` 是输入面板的全局 ref（`input_panel` / `input_attachments` / `input_textfield` / `input_model_select` / `input_model_reason` / `input_send_btn`），chat / agent 共用，依赖 session 互斥与每次重建才成立。
- `runtime` 里的 `session_id_chat_current` / `session_id_chat_last` 与 `session_id_agent_current` / `session_id_agent_last`：chat 与 agent **至多一个 current 非 None**；`*_last` 用于判断重复点击与切回时渲染哪条会话。
- ⚠️ **不要在 `__init__` 阶段访问 `EndPoints.root["page"]`**：导入顺序导致此时为 `None`。
- 所有 `ft.Ref` 取值需加 `.current`。
- `EndPoints.tmp_msgs`：仅保留**最后一次流式记录**的 UI 缓存，key 为 `session_id`；字段 `status` / `aimsgs` / `reason` / `detail` / `click_count` / `rendered_click_count`（结构见 `endpoints.py`）。

### `src/components/common.py` — 无状态 UI 积木层

跨组件复用的**无状态积木**集中放这里，任何组件可直接 import。现有分组：

| 类 | 职责 | 当前成员 |
|---|---|---|
| `AlertCommon` | 弹窗提示 | `alert_model_config_error` / `alert_model_config_none` |
| `MessageUtilsCommon` | LangChain 消息对象 → 渲染数据（不造 ft 控件） | `format_ai_msg_content` / `format_tool_msg_markdown` / `session_id_current` |
| `MessageBlockCommon` | 纯消息块渲染（回调由调用方注入） | `build_blk_user_msg` / `build_blk_ai_reasoning` / `build_blk_ai_tool_call` / `build_blk_ai_text` / `build_blk_ai_text_finally` / `build_blk_ai_summary` / `build_blk_err_msg` |
| `InputCommon` | 输入面板 + 附件栏 | `build_blk_input_panel(tools)` / `build_blk_input_textfield` / `build_blk_input_attachments` / `build_blk_input_attachment` / `refresh_input_attachments` / `callback_attachment_del` |

准入标准（**二者缺一不可**）：

| # | 条件 | 说明 |
|---|---|---|
| 1 | **无状态** | 不持有实例状态 / `ft.Ref`；不读写 `EndPoints.chat` / `EndPoints.settings` |
| 2 | **可复用** | 同一块 UI 已在多处出现，或已预见会被多处调用 |

- 层级：`common.py` → `<Subject>Common` 类 → 方法名与组件层保持同一套约定（`build_blk_*` / `callback_*`）；`MessageUtilsCommon` 只做数据归一化，不带 `build_blk_`。
- `InputCommon` 只接收调用方组装好的 `tools` 控件；工具菜单、切模型/思考/搜索、发送仍留在 `ChatInput`（差异面）。
- `MessageBlockCommon` 中带动作的块用**参数注入**回调（如 `on_retry=None`），不传就不渲染对应按钮，避免反向 import 组件。
- 触发层级在 `page` 上的弹窗（`show_dialog` / `pop_dialog`）天然满足准入。
- ⛔ **不合准入的典型**：带 `ref`、携带表单控件对象做 `data` 传递、保存后要回写状态、跨组件读写 `EndPoints.tmp_msgs` 状态机 → 留在原组件或走 `EndPoints`。

## ⚠️ `ft.Ref` 弱引用与 GC 陷阱

`ft.Ref` 内部对控件的引用是**弱引用**。当 ref 对应的控件被从 widget 树移除，且没有其他 Python 变量强引用该控件时，Python GC 会回收它，导致 `ref.current` 变为 `None`。

**基础规避：** 把控件实例保存在 View 的 `self` 属性中（View 实例经 `EndPoints.views[...]` 常驻），构建一次、复用，不要每次渲染重建。

```python
class SettingsView:
    def __init__(self):
        self.blk_switch_language = SettingsGeneral.build_blk_language_switch()

    def render_lv2(self, e=None):
        self.lv2_view.content = ft.Column(controls=[self.blk_switch_language, ...])
```

**另一个前提：`ft.Ref` 在控件构造期绑定，不是挂载期。** `BaseControl.__post_init__` 执行 `ref.current = self`；两个 View 若都在 `__init__` 构造带同一 ref 的控件，后构造者会永久覆盖前者。因此：

- `ChatView.render_lv2` **每次渲染重建输入面板**（构造即绑定 → 当前挂载的那份持有 ref）
- 将来的 `AgentView` 也必须每次导航重建，不能在 `__init__` 常驻

### 进阶陷阱：`Prop` 相等跳过让「重建 + 挂 content」也失效

即使把控件挂进 `self.xxx.content`，只要容器**每次渲染重建子树**，仍可能被 GC：

- `Container.content` 等字段是 Flet 的 `Prop` 描述符。赋值时若新旧值 **dataclass 值相等** 会直接跳过存储（`ref` 是 `InitVar` 不参与比较）——同工厂、同参数、同状态重建的两棵子树**值相等**。
- 于是新子树未被存储 → 其中的新控件无强引用 → 立即被 GC → `ref.current` 变回 `None`。
- **界面仍显示旧的（活着），ref 却指向刚丢弃的（已死）**。首次渲染正常；**切走再切回且状态未变**才触发。

**规避：先清后赋（clear-then-set）**

```python
# 先置 None 把已存储的旧值弹出，下一次赋值才会真正存储新子树 → 新控件获得强引用
# 这是针对 Flet 内部"相等跳过"的 workaround，必须配注释说明意图
self.chat_input.content = None
self.chat_input.content = ft.Column(controls=[...])
```

diff 层按**对象身份**（`src is not dst`）判定单子字段变更，所以 UI 会真正切到新子树，ref / UI / 强引用三者一致。

#### 自检清单：四条同时成立 → 必踩，写代码时就该先清后赋

| # | 特征 |
|---|---|
| 1 | 容器**每次渲染重建**子树（`content = ft.Column([...])`） |
| 2 | 子树内带 `ref`，且是 `EndPoints` 里的**全局 ref** |
| 3 | 存在**值相等**赋值的可能（同工厂、同参数、同状态重建） |
| 4 | 失败**延迟暴露**（要等某次事件回调才炸，如 `on_hover` / `on_click`） |

隐蔽性来自「病因在赋值行静默跳过，报错在几百毫秒后的另一个回调里」，中间还隔着一次切页。

#### ⛔ 反直觉：这类问题**不要**用「锚定子树保活」修

把实例存到 View 的 `self` 会**更糟**：保活让 `ref` 指向**未被存储、界面也不显示**的新控件，而事件（hover/click）来自界面上那个旧控件 → 静默错数据。
**只有先清后赋能保证 ref / 界面 / 强引用三者落在同一棵新子树上。**

已确认案例：`chat_input`（切走再切回且状态未变）、`chat_view.render_lv2`（设置 `chat_body` / `chat_input` 均先清后赋）。

## i18n 自动刷新（语言切换）

回调 `callback_language_switch` 在 `src/components/settings_general.py`。

1. 显示 i18n 文本的控件携带 `data={"i18n_key": "key_name"}` 自标识
2. 切换时遍历导航栏 → 设置 Lv1 → 设置 Lv2，通过 `data["i18n_key"]` 匹配并更新 `.tooltip` / `.content` / `.value`
3. 同步模式 Flet 自动 flush；异步需手动 `page.update()`

翻译 key 为**扁平 key-value**，文件在 `src/locales/{lang}.yaml`（`en`、`zh_cn`）。

## 对话数据流（chat）

- **消息持久化**：LangGraph checkpointer（`AsyncSqliteSaver`，`storage/data/checkpointer.db`），按 `thread_id` = `session_id` 存取。
- **读历史**：用「空壳只读图」`LCAgents.state_graph_chat`（`MessagesState` + 一个 `noop` 节点）`await graph.aget_state(cfg)`，消息在 `.values["messages"]`。状态 schema 必须与写入方一致（`create_agent` → `MessagesState`；`create_deep_agent` → `DeepAgentState`）。`state_graph_agent_update` 目前是空实现。
- **流式渲染**：`agent.astream_events(version="v3")` 的两个投影并发消费：
  - `astream.messages` → `consume_reasoning` / `consume_tool_calls_args` / `consume_text`
  - `astream.tool_calls` → `consume_tool_calls_output`（回填工具结果，只允许订阅一次）
  - 增量写入 `EndPoints.tmp_msgs[session_id]`（`status` / `aimsgs` / `reason` / `detail` / `click_count` / `rendered_click_count`），UI 据此增量刷新。
- **收尾**：`msg_update_stream` 用 `round_msgs` 对象身份判断本轮是否被新轮次顶掉；`error` / `aborted` 走 `msg_aborted_save`（把 `aimsgs` 重建为一条 `AIMessage`，复用 `lc_run_id` 原地替换半成品，`tool_calls=[]`、`as_node="model"`），正常结束则 `status="stop"` 并做 AI Summary 折叠。
- **会话列表**：顺序与标题存 `storage/data/sort_chat.yaml`（经 `FileDataUtils`，`data_type="sort_chat"`）；切换会话时 `ChatList.session_msgs_render` 读 checkpointer，`ChatBody.msg_update_rebuild` 补录未落库的流式块。
- **状态镜像**：`storage/data/tmp_msgs_state.yaml` 存 `status` / `reason` / `detail`，启动时镜像进 `EndPoints.tmp_msgs`（`CacheUtils.tmp_msgs_state_sync`）。
- **删除会话**：`LCAgents.session_delete` 先 `await checkpointer.setup()`（幂等，唯一 `_ensure_connected`），再 `adelete_thread`。
- **会话 ID 互斥**：`session_id_chat_current` 与 `session_id_agent_current` 至多一个非 None；停在 docs/settings 时都为 None。切到 chat 时清 agent，切到 docs/settings 时两者都清。ID 格式为 `<user>_chat_<uuid>` / `<user>_agent_<uuid>`，附件按 `startswith(session_prefix)` 天然隔离。
- **标题总结**：首轮正常结束后 `msg_title_summary` 用 `agent_summary` 生成标题，写回 `sort_chat.yaml` 与列表/头部。
- **重试 / 中止保存留在 `ChatBody`**：`callback_msg_retry` / `msg_aborted_save` 读写 `tmp_msgs` 状态机并跨组件改面板，不满足 common 准入；agent 侧将来各写一套，但 `as_node` 显式、`tool_calls=[]` 等机制注释只保留一份。

## 视图层级

- **MainView** — 主视图容器，导航切换时替换其 `content`
- **NavigationView** — 左侧 40px IconButton 导航栏（chat / docs / settings），用 `data={"selected_tag": ...}` 切换
- **SettingsView** — 三级布局：Lv1（Button 分类菜单）→ Lv2（板块内容）→ Lv3（嵌套详情，挂在其 `Row.controls` 尾部）
- **ChatView** — Lv1（会话列表）+ 可拖拽分割线（`GestureDetector`）+ Lv2（`chat_header` / `chat_body` / 输入面板）。输入面板在 `render_lv2` 每次重建（`InputCommon.build_blk_input_panel(tools=ChatInput.build_blk_input_tools())`），因为 ref 在构造期绑定。

导航切换：`NavigationView.render_main_view` → 清空 MainView → 注入对应 View → 调 `render_full()`；切到 docs/settings 时清空 chat / agent 的 `*_current`。

## 组件设计约定

- 工厂方法用 `build_blk_***` 前缀，`@classmethod`；调用一次后存进 View 实例变量，**不要反复调用**
- ⚠️ 若工厂返回的子树内含 `ref` 且被挂到**每次重建**的容器上，赋值时务必**先清后赋**（见上方自检清单）
- `build_blk_*` 用于**可复用**的块；**单次使用且由回调触发**的渲染允许内联构建（命名 `callback_*_render`）
- 跨组件通信走 `EndPoints`（有状态）；**无状态积木可直接 import**
- 当前组件工厂：`chat_list` / `chat_header` / `chat_body` / `chat_input`（对话）、`settings_general`（国际化）、`settings_model_services`（模型服务）、`settings_default_models`（默认模型）、`common`（`AlertCommon` / `MessageUtilsCommon` / `MessageBlockCommon` / `InputCommon`）
- 输入面板分层：`InputCommon` 负责面板/附件等通用积木，`ChatInput` 只保留差异面（`agent_type = "chat"`、工具菜单、发送/切模型/切思考/切搜索）。

### 命名约定：Subject-First 分组

**宁牺牲单函数可读性，也要大纲层次清晰。** 同一模块下函数多了以后，`subject` 放最前能让相关函数自然聚簇。

| 类别 | 结构 | 示例 |
|---|---|---|
| 工厂方法 | `build_blk_<subject>[_<sub_subject>][_<action>][_<type>]` | `build_blk_provider_item`、`build_blk_providers_list`、`build_blk_provider_add_btn` |
| 回调方法 | `callback_<subject>[_<sub_subject>]_<action>` | `callback_provider_details_save`、`callback_sessions_reorder` |
| common 积木 | 与所属类一致：`<subject>_<action>`（`AlertCommon`）或 `build_blk_*` / `callback_*`（`MessageBlockCommon` / `InputCommon`） | `alert_model_config_error`、`build_blk_err_msg` |

- `<type>` 后缀：`_btn`(Button) / `_tile`/`_item`(ListTile/列表项) / `_list`(ReorderableListView 等)
- 单数主体 = 操作单实体；复数主体 = 操作整个集合（`provider_item_add` vs `providers_reorder`）
- 特例：模块中只有一组回调且 `<subject>` 不明显时可省略（如 `callback_language_switch`）

## 智能体核心层（`src/cores/`）

- **`lc_agents.py` — `LCAgents`**（经 `EndPoints.runtime["lc_agents"]` 常驻）
  - 模型名格式为 `<provider>/<model>`，`agent_chat_update` 从 `ConfigUtils` 取 api_type / key / url 后装配
  - `OpenAI` 协议走 `HotfixChatOpenAI`（见下）；其余走 `init_chat_model`
  - `create_agent` 构建 chat 智能体；`agent_main` / `state_graph_agent_update` 仍是占位（deep agent 待接入）
  - `AsyncSqliteSaver` checkpointer（`storage/data/checkpointer.db`）
  - `agent_chat_update_async` 用 `asyncio.to_thread` 把重活挪出 event loop，**worker 线程内禁止触碰任何 `ft` 控件**；`agent_chat_loading` 期间调用方应忽略重复切换
  - `extra_body_update_reasoning_level` 按 profile 的思考强度拼 `reasoning_effort`（Auto 时移除）
  - `session_delete` 先 `setup()` 再 `adelete_thread`
- **`lc_hotfix_openai.py` — `HotfixChatOpenAI(ChatOpenAI)`**
  - 只覆盖 `_convert_chunk_to_generation_chunk`，把流式 delta 的 `reasoning_content` 转成 `{"type": "reasoning", "reasoning": ..., "index": 0}` 块
  - `index: 0` 必需：否则每个 delta 各存一个 reasoning 块
  - 同一 delta 带 `tool_calls` 时不改写 content（否则 v3 管线走 Responses 分支，工具增量从事件流消失）
  - 不要用 `init_chat_model` 注入子类：其私有表 + `lru_cache` 固定 `ChatOpenAI`
- **`lc_tools.py` — `LC_Tools`**：LangChain `@tool` 工具（当前：时间日期、Bing 关键词搜索、URL 抓取转纯文本）
  - 工具内**异常不外抛**（返回字符串让模型看到失败原因），HTTP 请求必须带 `timeout`

## 工具层（`src/utils/`）

| 工具 | 文件 | 职责 |
|---|---|---|
| `ConfigUtils` | `config.py` | 读写 `storage/conf/config.yaml`：模型服务商（`model_providers`）及其模型 |
| `ProfileUtils` | `config.py` | 读写 `storage/conf/profile.yaml`：语言、默认模型、思考强度、`chat_view` 宽度等用户偏好 |
| `CacheUtils` | `cache.py` | `tmp_msgs` 初始化/删除、`tmp_msgs_state.yaml` 镜像（`status` / `reason` / `detail`）、剪切板截图（`storage/temp/clipboard/`） |
| `FileDataUtils` | `data.py` | 读写 `storage/data/{sort_chat,sort_agent}.yaml`（会话顺序/标题） |
| `LanguageUtils` | `i18n.py` | 从 `src/locales/{lang}.yaml` 加载扁平 key-value 翻译 |
| loguru | `logging.py` | 输出到 stderr；`TRACE` 用于已完工模块，`DEBUG` 用于正在编写的模块 |

## 配置管理策略

目标用户是自己（懂 LLM 的开发者），不做防御性编程。配置异常（YAML 解析失败、key 缺失）的处理原则：

- **当前做法：** `logger.error` 警告后直接返回，**不自动重置**。`conf_init()` 只在文件首次缺失时调用。
- **未来计划：** 异常时自动备份旧配置（带时间戳 `config.yaml.bak.20260101`）再生成默认配置，设最大备份保留数、超限清理最旧的。

## Flet 布局陷阱

### `ft.IconButton` padding 默认值

`IconButton` 默认 `padding=8`，加上 `icon_size=24`，最小触摸区域被约束到 **48×48**。缩小按钮时必须同步清零 `padding`，否则内部图标被 8px 边距挤偏。

```python
ft.IconButton(ft.Icons.EDIT, icon_size=18, width=24, height=24, padding=0)
```

### `PopupMenuButton` 菜单宽度：默认受 280px 上限约束

默认宽度约束 `BoxConstraints(minWidth: 112, maxWidth: 280)`，宽度由内容驱动且最大 280px。要菜单与按钮等宽必须显式覆盖：

```python
ft.PopupMenuButton(
    content=ft.Container(..., width=300),
    size_constraints=ft.BoxConstraints(min_width=300, max_width=300),  # 映射到 Flutter constraints
    items=[...],
    menu_position=ft.PopupMenuPosition.UNDER,
)
```

- `ft.BoxConstraints` 字段为 snake_case：`min_width` / `max_width`
- 若按钮宽度会变（跟随窗口/板块），改用 `on_size_change` 动态同步
- 用于手动实现"下拉选择器"（替代无法限高的 `Dropdown` / 效果差的 `DropdownM2`）

### `PopupMenuButton` 悬浮默认提示（"Show menu"）

不设 `tooltip` 时悬浮会显示默认提示；**禁用方法：显式传空字符串 `tooltip=""`**。

- `tooltip` 是基类 `Control` 的继承属性（[文档](https://flet.dev/docs/controls/control)），各控件页面不单列，属正常
- 机制：Flet 给底层 Flutter 传 `tooltip: null` → Flutter 回退默认 `showMenuTooltip`；设 `tooltip=""` 后内层默认提示被隐藏

## LangChain 注意事项

LangChain OpenAI 不支持 Non-standard response fields（`reasoning_content` / `reasoning` / `reasoning_details`）。本项目**不改 site-packages**，而是在 `src/cores/lc_hotfix_openai.py` 用子类覆盖 `_convert_chunk_to_generation_chunk`（等效 README 的 Patch ①）。

- **发送侧 Patch ② 已无需再做**：`langchain_openai` 的 `_get_request_payload` 会在出站时剔除 `reasoning` / `tool_call` / `invalid_tool_call` 块
- **必须带 `index: 0`**，否则长思考会在 checkpointer 里堆积多个 reasoning 块
- **同 delta 带 `tool_calls` 时跳过改写**，否则工具增量会从 v3 事件流消失
- 已知遗留：content 变为 list 后，后续纯文本 delta 可能以裸字符串 append，应用侧读回时由 `MessageUtilsCommon.format_ai_msg_content` 归一化
- 测试：`tests/test_lc_hotfix_openai.py`（离线，含 v3 契约与基线对照）

## 目录结构

| 路径 | 说明 |
|---|---|
| `pyproject.toml` | 依赖与 Flet 打包配置（`[project]` / `[dependency-groups]` / `[tool.flet]`） |
| `src/main.py` | 入口（`ft.run`），绑定 `page`、初始化各 View / 工具 / `LCAgents`，注册键盘事件 |
| `src/endpoints.py` | `EndPoints` 通信枢纽（ref / View / runtime / tmp_msgs） |
| `src/views/` | 视图层（main / navigation / settings / chat） |
| `src/components/` | 组件工厂（含 `common.py` 无状态积木层） |
| `src/cores/` | 智能体核心层（`LCAgents` / `LC_Tools` / `HotfixChatOpenAI`） |
| `src/utils/` | 工具层（config / cache / data / i18n / logging） |
| `src/locales/*.yaml` | 扁平 key-value 翻译文件（en, zh_cn） |
| `src/assets/` | 各平台应用图标 `icon.png`，由 `[tool.flet]` 打包使用 |
| `tests/` | `test_lc_hotfix_openai.py`（纯离线） |
| `storage/conf/` | `config.yaml`（模型服务）、`profile.yaml`（用户偏好），运行时自动生成 |
| `storage/data/` | `sort_chat.yaml` / `tmp_msgs_state.yaml` / `checkpointer.db` |
| `storage/temp/` | 剪切板截图等临时文件 |

## 依赖

Python >= 3.10。依赖与打包配置统一在 `pyproject.toml`（`[project].dependencies` 运行依赖 / `[dependency-groups].dev` 开发依赖 / `[tool.flet]`），安装步骤见 [README.md](./README.md)。

运行依赖：`flet` / `langchain` / `langchain-openai` / `langchain-ollama` / `langgraph` / `langgraph-checkpoint-sqlite` / `deepagents` / `PyYAML` / `loguru` / `pillow` / `requests` / `aiosqlite`。

## 杂项

- **无 lint / typecheck 工具链**；测试用 pytest（`[tool.pytest.ini_options]`），当前仅 `tests/test_lc_hotfix_openai.py`。
- 键盘事件在 `src/main.py`：`Shift+Enter` 发送（仅当发送按钮为 `SEND` 图标）、`Ctrl+V` 粘贴剪贴板图片；两者目前都只认 `session_id_chat_current`，agent 接入时需放宽。
- `.gitignore` 忽略 `storage/`、`.flet/`、`build/`、`.idea/`、`.vscode/`
- ⛔ **不要在已有代码仓库里跑 `flet create .`**：它会覆盖 `src/main.py` 与 `.gitignore`。
- `LCAgents` 位于 `EndPoints.runtime["lc_agents"]`；`chat` 视图、`agent`（deep agent）核心仍在积极重构中
