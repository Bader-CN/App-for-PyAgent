# AGENTS.md

Flet 桌面应用，通过 LangChain / LangGraph 与 LLM 对话，纯 Python。DeepAgents 已加入依赖但**尚未接入**（`src/cores/lc_agents.py` 中 `create_deep_agent` / `FilesystemBackend` 仅 import）。

## 当前状态（2026-10）

| 模块 | 状态 |
|---|---|
| chat 对话 | 可用：多轮对话、流式思考/工具调用/正文、中止、重试、标题总结、截图粘贴、checkpointer 持久化 |
| settings | 可用：语言、默认模型、模型服务（provider / model 增删改拖拽） |
| docs | **占位**：导航到 docs 只清空会话 ID，主视图为空白 |
| agent（deep agent） | **占位**：`agent_main` / `agent_translation` / `state_graph_agent_update` 均未实现 |
| 复制 / 标题刷新 / 添加附件按钮 | **占位**：`callback_msg_copy` 为 `pass`，`build_blk_title_rename` / `build_blk_input_tool_add_attachments` 无 `on_click` |

## Run

```shell
flet run -r src/main.py      # dev, 热重载（从仓库根目录运行）
flet run src/main.py         # 演示
```

- 入口 `src/main.py` → `ft.run(main)`；启动时把仓库根加入 `sys.path`，所有模块用绝对导入 `from src.xxx import ...`。
- `pyproject.toml` 是依赖与 Flet 配置的唯一来源：`[tool.flet.app] path = "src"` 指定应用目录，构建产物 `.flet/` 生成在 `src/` 下。
- 测试：`.venv\Scripts\python.exe -m pytest tests/ -v`（仓库自带 `.venv`）或 `python -m pytest tests/ -v`；`[tool.pytest.ini_options].pythonpath = ["."]`（绝对导入要求仓库根在 `sys.path`），`asyncio_mode = "auto"`。当前 14 项全部通过。
- **`tests/` 被 `.gitignore` 忽略**（与 `storage/` 一样），不受版本控制。
- **LangChain OpenAI 的 `reasoning_content` 支持已内置于仓库**（`src/cores/lc_hotfix_openai.py`），无需再改 site-packages；README 里的手工 patch 是等价说明（README 的运行路径仍写作 `main.py`，已过时）。

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

端点分组（只列当前实际存在的键）：

| 分组 | 键 | 说明 |
|---|---|---|
| `root` | `page` / `navigation` / `main_view` | `page` 是 `ft.Page` 本身，其余为 `ft.Ref` |
| `root` | `add_model_dialog` / `edit_model_dialog` | 两个模型弹框的 ref |
| `input` | `input_panel` / `input_attachments` / `input_textfield` / `input_model_select` / `input_model_reason` / `input_send_btn` | 输入面板全局 ref，chat / agent 共用，依赖 session 互斥 + 每次重建 |
| `chat` | `lv1_view` / `lv2_view` / `chat_view` / `chat_list` / `chat_header` / `chat_body` | 对话视图与子块 |
| `settings` | `lv1_view` / `lv2_view` / `lv3_view` / `settings_view` | 设置视图布局 |
| `settings` | `switch_language` / `default_chat_model` / `default_agent_model` / `default_summary_model` / `default_translation_model` | 设置页显示值的控件 ref |
| `settings` | `providers_list` / `provider_models` / `provider_api_type` / `provider_del_btn` | 模型服务页内部控件 |
| `views` | `main_view` / `chat_view` / `navigation_view` / `settings_view` | **View 实例**，可调 `.render_full()` |
| `runtime` | `app_path_root` / `app_util_conf` / `app_util_cache` / `app_util_profile` / `app_util_filedata` / `app_util_lang` | 初始化于 `main.main()` |
| `runtime` | `app_language` / `llm_protocol` / `last_provider_name` / `lc_agents` | 运行期可变状态 |
| `runtime` | `session_id_chat_current` / `session_id_chat_last` / `session_id_agent_current` / `session_id_agent_last` | 会话互斥标记 |
| `tmp_msgs` | 普通 dict（不是 `ft.Ref`） | key 为 `session_id`，见下方结构 |

- `EndPoints.views["settings_view"]` 是 **View 实例**；`EndPoints.settings["settings_view"]` 是该 View 内 `ft.Ref[ft.Row]`（控件本体），二者不同。
- `runtime` 里的 `session_id_chat_current` / `session_id_agent_current`：chat 与 agent **至多一个非 None**；`*_last` 用于判断重复点击与切回时渲染哪条会话。
- ⚠️ **不要在 `__init__` 阶段访问 `EndPoints.root["page"]`**：导入顺序导致此时为 `None`；同理 `app_util_lang` 等 runtime 工具在 `main()` 中才就绪。
- 所有 `ft.Ref` 取值需加 `.current`。
- `EndPoints.tmp_msgs[session_id]` 字段：`status`（`start` / `reasoning` / `tool_call` / `text` / `stop` / `error` / `aborted`）、`aimsgs`（流式块列表）、`reason`（错误首行）、`detail`（完整错误文本）、`click_count` / `rendered_click_count`（面板同步判定）。

### `src/components/common.py` — 无状态 UI 积木层

跨组件复用的**无状态积木**集中放这里，任何组件可直接 import。现有分组：

| 类 | 职责 | 当前成员 |
|---|---|---|
| `AlertCommon` | 弹窗提示 | `alert_model_config_error` / `alert_model_config_none` |
| `MessageUtilsCommon` | LangChain 消息对象 → 渲染数据（不造 ft 控件） | `format_ai_msg_content` / `format_tool_msg_markdown` / `format_user_msg_markdown` / `session_id_current` |
| `MessageBlockCommon` | 纯消息块渲染（回调由调用方注入） | `build_blk_user_msg` / `build_blk_ai_reasoning` / `build_blk_ai_tool_call` / `build_blk_ai_text` / `build_blk_ai_text_finally` / `build_blk_ai_summary` / `build_blk_err_msg` |
| `InputCommon` | 输入面板 + 附件栏 | `build_blk_input_panel(tools)` / `build_blk_input_textfield` / `build_blk_input_attachments` / `build_blk_input_attachment` / `refresh_input_attachments` / `callback_attachment_del` |

准入标准（**二者缺一不可**）：

| # | 条件 | 说明 |
|---|---|---|
| 1 | **无状态** | 不持有实例状态 / `ft.Ref`；不读写 `EndPoints.chat` / `EndPoints.settings` |
| 2 | **可复用** | 同一块 UI 已在多处出现，或已预见会被多处调用 |

- 层级：`common.py` → `<Subject>Common` 类 → 方法名与组件层保持同一套约定（`build_blk_*` / `callback_*`）；`MessageUtilsCommon` 只做数据归一化，不带 `build_blk_`。
- `MessageUtilsCommon.format_user_msg_markdown(text)`：用户纯文本 → Markdown。给每个非空行尾补两个空格（CommonMark 硬换行），`\r\n` / `\r` 先归一化，围栏代码块（三反引号 / 三波浪线）内部不处理。`build_blk_user_msg` 在交给 `ft.Markdown` 前必须经过它，否则单个 `\n` 会被折叠成空格。
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

- 遍历实现为 `SettingsGeneral.refresh_i18n(control)`：**递归**走 `content` / `controls` / `items` / `title` / `subtitle` / `leading` / `trailing`，命中带 `i18n_key` 的控件后按类型回写（`ft.Text.value` / `ft.Button.content`（仅文本时）/ `ft.IconButton.tooltip`）。因此 Lv2 的嵌套层级变化不影响刷新，新控件只要挂上 `i18n_key` 即可自动生效。
- 遍历范围仍只到 Lv2 为止：Lv3（模型服务详情）与其他组件（chat 头 / 输入面板）**不会自动刷新**；要么重新渲染，要么重启。
- 设置 Lv2 的“默认模型”板块目前未挂 `i18n_key`，切换语言不会刷新，需要补 `data={"i18n_key": ...}`。
- 整个过程包在 `try/except` 中只打 `logger.warning`，新增控件漏挂 `i18n_key` 不会报错，只会保持旧语言。
- 翻译 key 为**扁平 key-value**，文件在 `src/locales/{lang}.yaml`（`en`、`zh_cn`）；`LanguageUtils.translate` 缺失时返回 `??key??`。

## 对话数据流（chat）

### 持久化与读历史

- **checkpointer**：`LCAgents.__init__` 创建 `AsyncSqliteSaver(conn=aiosqlite.connect("storage/data/checkpointer.db"))`；连接是惰性的，删除前必须 `await setup()`。
- **读历史**：用「空壳只读图」`LCAgents.state_graph_chat`（`MessagesState` + 一个 `noop` 节点）`await graph.aget_state(cfg)`，消息在 `.values["messages"]`。状态 schema 必须与写入方一致（`create_agent` → `MessagesState`；`create_deep_agent` → `DeepAgentState`）。`state_graph_agent_update` 目前是空实现。
- **会话元数据**：顺序与标题存 `storage/data/sort_chat.yaml`（经 `FileDataUtils`，`data_type="sort_chat"`）。
- **状态镜像**：`storage/data/tmp_msgs_state.yaml` 存 `status` / `reason` / `detail`，启动时由 `CacheUtils.tmp_msgs_state_sync` 镜像进 `EndPoints.tmp_msgs`。

### 发送与流式消费（`ChatBody.msg_update_stream`）

1. 封装 `HumanMessage`（uuid 作 id），调用 `astream_events({"messages": [human_msg]}, version="v3", config={"configurable": {"thread_id": session_id}})`。
2. `tmp_msgs_init(session_id, status="start")` 整体替换 dict，并保存 `round_msgs` 对象身份用于收尾核对。
3. 两条独立投影并发消费（共享同一个 pump）：
   - `astream.messages` → 每条 message 内再 `asyncio.gather(consume_reasoning, consume_tool_calls_args, consume_text)`
   - `astream.tool_calls` → `consume_tool_calls_output`（回填工具结果，**只允许订阅一次**）
4. 每个消费者都：检查 `status in ("error", "aborted")` → `await astream.abort()`；维护 `is_current` / `is_synced`；只有两者同时成立才碰界面。
5. `status` 状态机：`start` → `reasoning` / `tool_call` / `text` → `stop`（正常）或 `error` / `aborted`（异常 / 用户停止）。
6. `msg_aborted_post_processing` **首个错误优先**：`status` 已是 `error` / `aborted` 时只 `abort()` 返回，避免多个消费者各渲染一个错误块。

### 收尾（`msg_update_stream` 尾部）

- **身份核对**：`EndPoints.tmp_msgs.get(session_id) is not round_msgs` → 本轮已被新轮次顶掉，整体放弃收尾（不写 stop、不切面板、不重复渲染）。
- **error / aborted**：
  - `msg_aborted_save` 把 `aimsgs` 重建为一条 `AIMessage` 写回 checkpointer：复用本轮已落库 AIMessage 的 `id`（否则会追加而不是替换）、`RemoveMessage` 删除多余半成品、`tool_calls=[]`、`as_node="model"`、`response_metadata={"finish_reason": "stop", "output_version": "v1"}`。
  - 持久化 `tmp_msgs_state.yaml`。
  - `error` 的块在这里渲染；`aborted` 已在 `ChatInput` 停止回调里即时渲染（避免工具静默期干等）。
- **正常结束**：
  - `status="stop"`，删除状态镜像。
  - `len(aimsgs) > 2`：把中间块搬进 `build_blk_ai_summary()`（AI Summary），最后一块替换为 `build_blk_ai_text_finally`；否则只替换最后一块。
  - 滚动到底 + `page.update()`，发送按钮图标恢复 `SEND`。
  - 若列表标题仍是 `new_session`，`run_task(callback_msg_title_summary)` 生成标题。

### 重试（`ChatBody.callback_msg_retry`）

- 只允许在一轮已结束时触发（`status in stop/error/aborted`），否则忽略；开头立刻把 `status` 置为 `start` 抢占，防止双击发出两个流。
- 界面：倒序找最近的 `user_msg` 块，用**正索引** `controls[:len(controls) - idx + 1]` 保留它，退掉其后的块（不要写 `-idx + 1`：`idx=1` 时会退化成 `[:0]` 清空面板）。
- 删库：读 `state_graph_chat` 快照，用 `{"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *keep]}` + `as_node="model"` 把最近一轮删掉；**删库必须早于重发**。
- 删库失败：`status` 还原为 `error`，追加错误块并 `return`（此时 `user_msg` 块仍在，重试按钮仍可用）。
- 成功后 `await msg_update_stream(user_msg=...)`。

### 会话列表与切换

- **新建 / 删除 / 拖拽排序**：`ChatList.callback_session_add` / `callback_session_del` / `callback_sessions_reorder`，UI 与 `sort_chat.yaml` 同步。
- **删除**：`tmp_msgs_del`（只在 `status` 为 `None/stop/error` 时真删）+ `tmp_msgs_state_del` + `LCAgents.session_delete`（`setup()` → `adelete_thread`）。
- **切换 / 重复点击**：`callback_session_msgs_render` 用 `session_id_chat_last` + `session_id_chat_current` 判定重复点击；切换时清空 `chat_body`、更新互斥标记、`click_count += 1`（首次则 `tmp_msgs_init`）、渲染 header、刷新附件、`run_task(session_msgs_render)`。
- **渲染历史**：`session_msgs_render` 用 `HumanMessage` 把消息切成「用户块 + 消息段」；`_session_msgs_merge` 判定是否折叠进 AI Summary（AI 消息 ≥2、末条是 AIMessage、末块是 text 才折叠）；`_session_msgs_group_render` 先渲染 AIMessage，再按 `tool_call_id` 把 ToolMessage 回填到工具块（用 id 而不是位置，容忍中止补写后的乱序）。
- **流式补录**：若当前会话 `status` 非终态，`ChatBody.msg_update_rebuild(aimsgs)` 补上未落库的块，并把 `rendered_click_count` 同步为 `click_count`。若 `status` 是 `error/aborted`，再补一个错误块。

### 其他约定

- **会话 ID 互斥**：`session_id_chat_current` 与 `session_id_agent_current` 至多一个非 None；停在 docs/settings 时都为 None。ID 格式为 `<user>_chat_<uuid>` / `<user>_agent_<uuid>`，附件按 `startswith(session_prefix)` 天然隔离。
- **重试 / 中止保存留在 `ChatBody`**：它们读写 `tmp_msgs` 状态机并跨组件改面板，不满足 common 准入；agent 侧将来各写一套，但 `as_node` 显式、`tool_calls=[]` 等机制注释只保留一份。

## 视图层级

- **MainView** — 只有一个 `ft.Container`（`EndPoints.root["main_view"]`），导航切换时替换其 `content`。
- **NavigationView** — 左侧 40px IconButton 导航栏（chat / docs / settings），`data={"selected_tag": ...}` 切换，`last_selected_button` 去重。
  - `chat`：注入 `chat_view` → `render_full()` → 若列表为空先新建会话 → 按 `session_id_chat_last` 恢复上次会话（没有则渲染第一项）。
  - `docs`：**只清空 chat / agent 的 `*_current`**，主视图保持空白（占位）。
  - `settings`：清空会话 ID → 注入 `settings_view` → `render_full()`。
- **SettingsView** — 三级布局：Lv1（Button 分类菜单）→ Lv2（板块内容）→ Lv3（模型服务详情，追加到 `settings_view.controls` 尾部）。
  - `render_lv2` 用 `last_selected_tag` 去重。
  - `render_lv2_content` 开头把 `settings_view.controls` 截回前 3 项，以清掉 Lv3。
  - `callback_provider_details_render` 把 `blk_models` 存到 `EndPoints.views["settings_view"].blk_models`，防止 GC。
- **ChatView** — Lv1（会话列表）+ 可拖拽分割线 + Lv2（`chat_header` / `chat_body` / 输入面板）。
  - 分割线：`GestureDetector` 7px 热区，`lv1_width` 限制在 200–300，`on_pan_end` 写入 `profile.yaml`。
  - `chat_body` 的 `ft.Column` 用 `scroll=AUTO` + `horizontal_alignment=STRETCH`；横向铺满由 STRETCH 负责（`expand` 在滚动列里无效）。
  - 输入面板在 `render_lv2` **每次重建**（`InputCommon.build_blk_input_panel(tools=ChatInput.build_blk_input_tools())`），并对 `chat_body` / 输入面板**先清后赋**。

## 组件设计约定

- 工厂方法用 `build_blk_***` 前缀，`@classmethod`；调用一次后存进 View 实例变量，**不要反复调用**
- ⚠️ 若工厂返回的子树内含 `ref` 且被挂到**每次重建**的容器上，赋值时务必**先清后赋**（见上方自检清单）
- `build_blk_*` 用于**可复用**的块；**单次使用且由回调触发**的渲染允许内联构建（命名 `callback_*_render`）
- 跨组件通信走 `EndPoints`（有状态）；**无状态积木可直接 import**
- 当前组件工厂：`chat_list` / `chat_header` / `chat_body` / `chat_input`（对话）、`settings_general`（国际化）、`settings_model_services`（模型服务）、`settings_default_models`（默认模型）、`common`（`AlertCommon` / `MessageUtilsCommon` / `MessageBlockCommon` / `InputCommon`）
- 输入面板分层：`InputCommon` 负责面板/附件等通用积木，`ChatInput` 只保留差异面（`agent_type = "chat"`、工具菜单、发送/切模型/切思考/切搜索）。
- `ChatBody` 内部按职责分三类方法：`msg_*`（流程 / 持久化）、`consume_*`（流式消费）、`callback_*`（UI 回调）；`chat_list` 的内部辅助函数用 `_session_msgs_*` 下划线前缀。
- 可能耗时或需要 `await` 的回调（切换模型 / 思考）写成 `async def`；阻塞型重活放到 `asyncio.to_thread`，**worker 线程内禁止触碰 ft 控件**。
- `await` 之后 `e.control` / `e.page` 可能已失效（切页会重建子树）：先取出 `page = e.page`，之后重新从 `EndPoints` 取 ref 并判空。

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
  - 模型名格式为 `<provider>/<model_name>`（`ProfileUtils.default_model` 返回）；`agent_chat_update` 从 `ConfigUtils` 取 api_type / key / url 后装配。
  - 工具按 `web_search` 开关装配：始终有 `get_currently_datetime_and_weekday`；开启时再加 `http_request_get_with_keyword` / `http_request_get_with_url`。
  - `OpenAI` 协议走 `HotfixChatOpenAI`（见下）；其余（如 `Ollama`）走 `init_chat_model`。
  - `create_agent(model=..., checkpointer=..., tools=...)` 构建 chat 智能体；`agent_main` / `agent_translation` / `state_graph_agent_update` 仍是占位（deep agent 待接入）。
  - `AsyncSqliteSaver` checkpointer 在 `__init__` 创建（惰性连接）。
  - `agent_chat_update` 是同步实现，失败返回错误字符串、成功返回 `None`；`agent_chat_update_async` 用 `asyncio.to_thread` 把重活挪出 event loop。**worker 线程内禁止触碰任何 `ft` 控件**；`agent_chat_loading` 期间调用方应忽略重复切换。
  - `extra_body_update_reasoning_level` 按 profile 的思考强度拼 `reasoning_effort`（`Auto` 时移除 `reasoning_effort` / `allowed_openai_params`；`Off` → `"none"`；`Low/Medium/High` 对应小写值）。
  - `agent_summary_update` 使用 `reasoning_effort="none"` + `allowed_openai_params` 的非思考配置。
  - `state_graph_chat_update` 构建 `MessagesState` + `noop` 节点的只读图；`state_graph_agent_update` 为空。
  - `session_delete` 先 `await setup()` 再 `adelete_thread`。
- **`lc_hotfix_openai.py` — `HotfixChatOpenAI(ChatOpenAI)`**
  - 只覆盖 `_convert_chunk_to_generation_chunk`，把流式 delta 的 `reasoning_content` 转成 `{"type": "reasoning", "reasoning": ..., "index": 0}` 块；同 delta 有正文时再追加 `{"type": "text", ...}`。
  - `index: 0` 必需：否则每个 delta 各存一个 reasoning 块。
  - 同一 delta 带 `tool_calls` 时不改写 content（否则 v3 管线走 Responses 分支，工具增量从事件流消失）。
  - 不要用 `init_chat_model` 注入子类：其私有表 + `lru_cache` 固定 `ChatOpenAI`。
- **`lc_tools.py` — `LC_Tools`**：LangChain `@tool` 工具（当前：时间日期、Bing 关键词搜索、URL 抓取转纯文本）。
  - 工具内**异常不外抛**（返回字符串让模型看到失败原因），HTTP 请求必须带 `timeout`（当前 20s）。
  - HTML → 纯文本用标准库 `HTMLParser`（不用正则），保留绝对化链接，返回上限 128000 字符。
  - `http_request_get_with_keyword` 先拼 Bing URL，再通过 `.func` 复用 URL 抓取逻辑（避免二次 `@tool` 包装）。

## 工具层（`src/utils/`）

| 工具 | 文件 | 职责 |
|---|---|---|
| `ConfigUtils` | `config.py` | 读写 `storage/conf/config.yaml`：模型服务商（`model_providers`）及其模型 |
| `ProfileUtils` | `config.py` | 读写 `storage/conf/profile.yaml`：语言、默认模型、思考强度、`chat_view` 宽度等用户偏好 |
| `CacheUtils` | `cache.py` | `tmp_msgs` 初始化/删除、`tmp_msgs_state.yaml` 镜像（`status` / `reason` / `detail`）、剪切板截图（`storage/temp/clipboard/`） |
| `FileDataUtils` | `data.py` | 读写 `storage/data/{sort_chat,sort_agent}.yaml`（会话顺序/标题），带内存缓存 |
| `LanguageUtils` | `i18n.py` | 从 `src/locales/{lang}.yaml` 加载扁平 key-value 翻译 |
| loguru | `logging.py` | 输出到 stderr，级别 `TRACE` |

- `ConfigUtils`：`models_list_enable()` 返回 `["<provider>/<model_name>", ...]`（只含已启用 provider）；`providers_dict()` 返回**内部字典引用**（原地修改才会写回）；`provider_api_url/key/type` 读写单个字段，`provider_models_add/edit/del` 维护模型列表。
- `ProfileUtils`：`default_model(type)` 在 provider 被禁用时返回 `None`；`language()` 会同步 `EndPoints.runtime["app_language"]`；`language_set()` 同时重载 `LanguageUtils`。
- `CacheUtils`：截图文件名 `<session_prefix>_screenshot_<n>.png`，按前缀隔离；`tmp_msgs_del` 只在 `status` 为 `None/stop/error` 时真正删除（`aborted` 会保留缓存）。
- `FileDataUtils`：`data_read` 首次读文件后缓存在 `app_data_dict`，文件不存在时自动 `data_init` 建空列表。

### 配置文件形状

`storage/conf/config.yaml`：

```yaml
general_settings:
  language: zh_cn            # 当前未被实际读取（语言以 profile.yaml 为准）
model_providers:
  <provider_name>:
    api_url: http://<host>:<port>/v1
    api_key: sk-****
    api_type: OpenAI          # OpenAI / Ollama
    enable: true
    models:
      - model_id: xxx
        model_name: yyy
        model_feats: {vision: true, embed: false, reranker: false}
```

`storage/conf/profile.yaml`：

```yaml
general_settings: {language: zh_cn}
default_models:
  chat_model: <provider>/<model_name>
  agent_model: null
  summary_model: null
  translation_model: null
chat_view: {lv1_view_width: 250}
reasoning_level: {chat: Auto, agent: Auto}   # Off / Low / Medium / High / Auto
```

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

### `ft.Markdown` 的换行 / 代码块

- Markdown 把单个 `\n` 当软换行折叠成空格；用户输入的换行必须走 `MessageUtilsCommon.format_user_msg_markdown`（行尾补两个空格），或改用 `ft.Text(selectable=True)`。
- 围栏代码块（三反引号 / 三波浪线）内部原样渲染，不要补硬换行。
- `ft.Markdown` 会把 `<...>` 当 HTML 吞掉，错误详情这类原始文本用 `ft.Text`。

### 滚动列里的 `expand`

`ft.Column(scroll=...)` 的主轴无界，子控件上的 `expand=True` 既撑不起高度也不撑宽度。横向铺满靠 `horizontal_alignment=ft.CrossAxisAlignment.STRETCH`；需要右对齐时用 `ft.Row(alignment=ft.MainAxisAlignment.END, controls=[...])` 包一层。

### `ExpansionTile` 的边框与高度

`ExpansionTile` 自身不能直接画边框，用 `shape` / `collapsed_shape=ft.RoundedRectangleBorder(side=..., radius=...)`。`tile_padding` / `dense` 控制行高；`maintain_state=True` 防止展开后重建闪烁。思考块用 `ft.Text` 的 `on_size_change` 把自然高度 `min` 到上限，外层 `Column(scroll=HIDDEN, auto_scroll=True)` 跟随。

### `ReorderableListView`

用 `show_default_drag_handles=False` + 每项自带 `ft.ReorderableDragHandle`，`on_reorder` 里对**后端数据**和**界面 controls** 各做一次 `pop` + `insert`（模型列表若不手动同步会出现界面与配置不一致）。`insert(index, value)` 是移动语义，不要用交换。

### `ListTile` 局部更新

Flet 0.85 下直接替换整个 `ListTile` 有时不刷新；只改某个字段（如 `trailing`）后调用 `control.update()` 更稳（见 `callback_provider_switch_btn_toggle`）。

## LangChain 注意事项

LangChain OpenAI 不支持 Non-standard response fields（`reasoning_content` / `reasoning` / `reasoning_details`）。本项目**不改 site-packages**，而是在 `src/cores/lc_hotfix_openai.py` 用子类覆盖 `_convert_chunk_to_generation_chunk`（等效 README 的 Patch ①）。

- **发送侧 Patch ② 已无需再做**：`langchain_openai` 的 `_get_request_payload` 会在出站时剔除 `reasoning` / `tool_call` / `invalid_tool_call` 块。
- **必须带 `index: 0`**，否则长思考会在 checkpointer 里堆积多个 reasoning 块。
- **同 delta 带 `tool_calls` 时跳过改写**，否则工具增量会从 v3 事件流消失。
- 已知遗留：content 变为 list 后，后续纯文本 delta 可能以裸字符串 append，应用侧读回时由 `MessageUtilsCommon.format_ai_msg_content` 归一化。
- **v1 content block**：`reasoning` / `text` / `tool_call` 是当前读写的统一形状；写入中止消息时显式带 `response_metadata.output_version="v1"`，避免再次按 provider 规则翻译。
- **`aupdate_state` 必须显式 `as_node="model"`**：checkpoint 的 `versions_seen` 可能同时有 model / tools，LangGraph 推断会抛 `InvalidUpdateError: Ambiguous update`。
- **删除最近一轮**：`{"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *keep]}`；`REMOVE_ALL_MESSAGES` 的重设语义见 `callback_msg_retry` 注释。
- **中止补写**：`tool_calls=[]` 必须留空；复用半成品 AIMessage 的 `id` 才能原地替换。
- 测试：`tests/test_lc_hotfix_openai.py`（离线，含 v3 契约与基线对照）。

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
| `tests/` | `test_lc_hotfix_openai.py`（纯离线，14 项）；**被 .gitignore 忽略** |
| `storage/conf/` | `config.yaml`（模型服务）、`profile.yaml`（用户偏好），运行时自动生成 |
| `storage/data/` | `sort_chat.yaml` / `sort_agent.yaml`（预留给 agent）/ `tmp_msgs_state.yaml` / `checkpointer.db` |
| `storage/temp/` | `clipboard/` 剪切板截图临时文件 |

## 依赖

Python >= 3.10。依赖与打包配置统一在 `pyproject.toml`（`[project].dependencies` 运行依赖 / `[dependency-groups].dev` 开发依赖 / `[tool.flet]`），安装步骤见 [README.md](./README.md)。

运行依赖：`flet` / `langchain` / `langchain-openai` / `langchain-ollama` / `langgraph` / `langgraph-checkpoint-sqlite` / `deepagents` / `PyYAML` / `loguru` / `pillow` / `requests` / `aiosqlite`。

## 当前缺口 / 已知问题

- `docs` 页只有导航占位，没有内容视图。
- deep agent（agent 界面 / `agent_main` / `agent_translation` / `state_graph_agent_update`）未接入。
- 复制按钮（`callback_msg_copy`）、标题刷新按钮（`build_blk_title_rename` 无 `on_click`）、添加附件按钮（`build_blk_input_tool_add_attachments` 无 `on_click`）均为占位。
- `InputCommon.build_blk_input_attachment` 的 `display_name` 只在文件名含 `_screenshot_` 时赋值；其他附件类型会 `UnboundLocalError`（当前只接截图，未触发）。
- `msg_aborted_save` 未判断 `agent_chat is None`，会走到 `aupdate_state` 抛 `AttributeError` 并被 `except` 吞掉 → aborted 内容静默不入库。
- `msg_update_stream` 正常结束分支直接取 `aimsgs[-1]`；模型没有产出任何块时会 `IndexError`。
- `callback_msg_title_summary` 依赖 `last_user_msg` / `last_ai_msg` 同时存在，否则 `summary_msgs` 未定义。
- `ProfileUtils.default_model` 对已删除的 provider 会 `AttributeError`（配置异常未做防御，符合当前策略）。
- README 的运行路径与手工 patch 说明已过时，以本文件 + `src/cores/lc_hotfix_openai.py` 为准。

## 杂项

- **无 lint / typecheck 工具链**；测试用 pytest（`[tool.pytest.ini_options]`），当前仅 `tests/test_lc_hotfix_openai.py`。
- 键盘事件在 `src/main.py`：`Shift+Enter` 发送（仅当发送按钮为 `SEND` 图标）、`Ctrl+V` 粘贴剪贴板图片；两者目前都只认 `session_id_chat_current`，agent 接入时需放宽。
- `.gitignore` 忽略 `storage/`、`tests/`、`.flet/`、`build/`、`.idea/`、`.vscode/`。
- ⛔ **不要在已有代码仓库里跑 `flet create .`**：它会覆盖 `src/main.py` 与 `.gitignore`。
- `LCAgents` 位于 `EndPoints.runtime["lc_agents"]`；`chat` 视图、`agent`（deep agent）核心仍在积极重构中。
