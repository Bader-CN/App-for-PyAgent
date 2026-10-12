import os
import asyncio
import aiosqlite

# 等效于 from langchain_openai import ChatOpenAI
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import MessagesState
from langchain.agents import create_agent
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

from src.endpoints import EndPoints
from src.cores.lc_tools import LC_Tools
from src.utils.logging import logger


class LCAgents:
    """
    LangChain/DeepAgents 系智能体封装类 (LC=LangChain)
    包含多个智能体, 用于不同场景
    """
    def __init__(self):
        # App 运行时的根目录
        self.app_path_root = EndPoints.runtime["app_path_root"]
        # checkpointer 对象
        self.checkpointer = AsyncSqliteSaver(
            conn=aiosqlite.connect(os.path.abspath(os.path.join(self.app_path_root, "storage/data/checkpointer.db")))
        )

        # 智能体实例
        self.agent_chat = None
        self.agent_main = None
        self.agent_summary = None
        self.agent_translation = None

        # 标记位
        # agent_chat 是否正在加载
        # 供调用方在发起加载前判断, 避免并发构建
        self.agent_chat_loading = False

        # 用于读取记录的状态图
        self.state_graph_chat = None
        self.state_graph_agent = None

        # 自定义请求体参数
        self.extra_body_chat = {}
        self.extra_body_agent = {}

        # 更新额外的请求体参数
        self.extra_body_update_reasoning_level(agent_type="chat")
        self.extra_body_update_reasoning_level(agent_type="agent")

    def agent_chat_update(self, web_search=True):
        """
        更新 "Chat Agent" 实例

        Args:
        - web_search:   布尔值, 默认启用网页搜索工具
        """
        # 当前完整的模型名: <provider_name>/<model_name>
        full_model_name = EndPoints.runtime["app_util_profile"].default_model(default_type="chat_model")
        if full_model_name is None:
            self.agent_chat = None
            logger.error("default chat agent model not set!")
        else:
            try:
                logger.info("loading chat agent...")
                # 判断加载哪些工具
                tools = [LC_Tools.get_currently_datetime_and_weekday]
                if web_search:
                    tools.extend([LC_Tools.http_request_get_with_keyword, LC_Tools.http_request_get_with_url])
                # 加载模型
                provider_name, model_name = full_model_name.split("/", 1)
                llm_model = init_chat_model(
                    model_provider=EndPoints.runtime["app_util_conf"].provider_api_type(provider_name=provider_name),
                    model=model_name,
                    api_key=EndPoints.runtime["app_util_conf"].provider_api_key(provider_name=provider_name),
                    base_url=EndPoints.runtime["app_util_conf"].provider_api_url(provider_name=provider_name),
                    extra_body=self.extra_body_chat if self.extra_body_chat else None,
                )
                self.agent_chat = create_agent(
                    model=llm_model,
                    checkpointer=self.checkpointer,
                    tools=tools,
                )
                logger.success("loading chat agent finish.")
            except Exception as e:
                self.agent_chat = None
                logger.error(f"loading chat agent failed. issue is: {e}")
                return str(e)

    async def agent_chat_update_async(self, web_search=True):
        """
        以异步的方式更新 Chat Agent 智能体实例
        -> 重活交给 worker 线程, 不占 event loop, 加速界面渲染

        Note:
        - worker 线程内禁止触碰任何 ft 控件 -> 控件只能在 event loop 上读写

        Args:
        - web_search:   布尔值, 默认启用网页搜索工具
        """
        self.agent_chat_loading = True
        try:
            return await asyncio.to_thread(self.agent_chat_update, web_search=web_search)
        finally:
            self.agent_chat_loading = False

    def agent_summary_update(self):
        """
        更新汇总模型智能体
        """
        # 当前完整的模型名: <provider_name>/<model_name>
        full_model_name = EndPoints.runtime["app_util_profile"].default_model(default_type="summary_model")
        if full_model_name is None:
            logger.warning("default summary agent model not set!")
            self.agent_summary = None
        else:
            try:
                logger.info("loading summary agent...")
                # 加载模型
                provider_name, model_name = full_model_name.split("/", 1)
                self.agent_summary = init_chat_model(
                    model_provider=EndPoints.runtime["app_util_conf"].provider_api_type(provider_name=provider_name),
                    model=model_name,
                    api_key=EndPoints.runtime["app_util_conf"].provider_api_key(provider_name=provider_name),
                    base_url=EndPoints.runtime["app_util_conf"].provider_api_url(provider_name=provider_name),
                    extra_body={"reasoning_effort": "none", "allowed_openai_params": "reasoning_effort"},
                )
                logger.success("loading summary agent finish.")
            except Exception as e:
                logger.warning(f"loading summary agent failed. issue is: {e}")
                self.agent_summary = None
                return str(e)

    def state_graph_chat_update(self):
            """
            构建「读历史」专用的只读图 (空壳图), 并缓存到 self.state_graph_chat
    
            "读历史" 和 "跑对话" 是两件事, 读历史只需要三样东西:
            1. 一个能 compile 的图 (状态 schema 必须与写入方一致)
            2. 同一个 checkpointer 实例 (同一个 db 文件)
            3. thread_id
            
            注意:
            1. 节点体可以是假的, schema 不能假
               -> create_agent 创建的 AgentState.messages 走 add_messages, 与 MessagesState 同构, 所以这里能用 MessagesState
               -> create_deep_agent 创建的 DeepAgentState.messages 走 DeltaChannel, 所以必须同步换成 DeepAgentState
                  否则 aget_state 会静默返回 []
            2. 必须至少有一个节点
               -> StateGraph.validate() 要求 START 必须是某条边的起点, 不能只给 schema 不给节点
               -> 该节点永远不会被执行 (本图从不 invoke), 故 `lambda state: {}` 安全
            3. 调用 await self.state_graph_chat.aget_state({"configurable": {"thread_id": session_id}})
               -> 返回 StateSnapshot(NamedTuple)
               -> 消息在 .values 里, 一行版必须加括号: (await graph.aget_state(cfg)).values.get("messages", [])
               -> 不存在的 thread_id 不抛异常, 返回 StateSnapshot(values={}) → 安全得到 []
            4. 建立连接不是本方法的职责
               -> aget_state 内部确实会触发 checkpointer 的 setup() (aget_tuple 里 await self.setup()),
                  但那是"顺带"的副作用, 不能当依赖
               -> 连接改由 __init__ 的预热 (显式) 和 session_delete() (自愈) 各自保证, 见各自注释
            """
            # 编译图
            builder = StateGraph(MessagesState)
            builder.add_node("noop", lambda state: {})
            builder.add_edge(START, "noop")
            self.state_graph_chat = builder.compile(checkpointer=self.checkpointer)
            return self.state_graph_chat

    def state_graph_agent_update(self):
         """
         构建「读历史」专用的只读图 (空壳图), 并缓存到 self.state_graph_agent
         """
         pass

    def extra_body_update_reasoning_level(self, agent_type: str):
        """
        更新 self.extra_body_chat / self.extra_body_agent 中的思考强度

        Args:
        - agent_type:    值为 chat / agent, 即区分是聊天还是代理的思考强度
        """
        reason_lv_dict = EndPoints.runtime["app_util_profile"].reasoning_level()
        reason_lv = reason_lv_dict[agent_type]
        if agent_type == "chat":
            # Auto 情况删掉 reasoning_effort 字段
            if reason_lv == "Auto":
                self.extra_body_chat.pop("reasoning_effort", None)
                self.extra_body_chat.pop("allowed_openai_params", None)
            elif reason_lv == "Off":
                self.extra_body_chat["reasoning_effort"] = "none"
                # self.extra_body_chat["allowed_openai_params"] = ["reasoning_effort"]
            elif reason_lv == "Low":
                self.extra_body_chat["reasoning_effort"] = "low"
            elif reason_lv == "Medium":
                self.extra_body_chat["reasoning_effort"] = "medium"
            elif reason_lv == "High":
                self.extra_body_chat["reasoning_effort"] = "high"
        elif agent_type == "agent":
            # Auto 情况删掉 reasoning_effort 字段
            if reason_lv == "Auto":
                self.extra_body_agent.pop("reasoning_effort", None)
                self.extra_body_agent.pop("allowed_openai_params", None)
            elif reason_lv == "Off":
                self.extra_body_agent["reasoning_effort"] = "none"
            elif reason_lv == "Low":
                self.extra_body_agent["reasoning_effort"] = "low"
            elif reason_lv == "Medium":
                self.extra_body_agent["reasoning_effort"] = "medium"
            elif reason_lv == "High":
                self.extra_body_agent["reasoning_effort"] = "high"

    async def session_delete(self, session_id: str):
        """
        删除在 checkpointer 里的指定会话数据

        Note:
        # https://docs.langchain.com/oss/python/langgraph/add-memory#delete-all-checkpoints-for-a-thread
        # https://docs.langchain.com/oss/python/langgraph/add-memory#database-management
        # https://reference.langchain.com/python/langgraph.checkpoint.sqlite/aio/AsyncSqliteSaver/setup
        不要直接去调用 self.checkpointer.adelete_thread(config)
        -> 因为如果 checkpointer 没有连接过, 则在执行 adelete_thread(config) 时会抛出无连接的错误
        -> 必须先 await setup(): 它是 AsyncSqliteSaver 里唯一会 _ensure_connected 的方法, 且幂等
            -> 内部 `if self.is_setup: return` 守卫), 已连上时重复调用零成本
        -> setup() 与 adelete_thread 各自取放同一个 self.lock → 顺序 await 不会死锁
        """
        await self.checkpointer.setup()
        await self.checkpointer.adelete_thread(session_id)