"""
LangChain OpenAI 思考内容 (reasoning) 热修复层

Note:
- 官方 ChatOpenAI 只对齐 OpenAI 官方规范, 不提取第三方端点新增的非标准字段
  (reasoning_content / reasoning_details)
- 若上游若原生支持了非标准字段, 本文件可删除, 并把 src/cores/lc_agents.py::LCAgents.agent_chat_update 里对 HotfixChatOpenAI 改回统一的 init_chat_model(...)
- 本模块可被任意模块直接 import (见 AGENTS.md)
- 只覆盖 OpenAI 协议; Ollama 走 langchain_ollama 自带的转换
"""
from langchain_core.messages import AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk
from langchain_openai import ChatOpenAI


# 思考块的合并键 (机制见 _convert_chunk_to_generation_chunk 的 Note 3)
# - 必须是带 "lc_" 前缀的字符串: merge_lists 只认 int 或 "lc_*" 作合并键
# - 不能是整数: 那会和 OpenAI tool_calls 的 index (从 0 开始) 撞桶
REASONING_BLOCK_INDEX = "lc_reasoning_0"


class HotfixChatOpenAI(ChatOpenAI):
    """
    ChatOpenAI 热修复子类: 让 OpenAI 兼容端点的思考增量进入 v3 流
    -> 即 astream_events(version="v3") 里的 message.reasoning

    Note:
    - 只新增一个 override, 其余行为完全继承官方实现
    """
    def _convert_chunk_to_generation_chunk(self, chunk: dict, default_chunk_class: type, base_generation_info: dict | None) -> ChatGenerationChunk | None:
        """
        把流式 delta 里的非标准 reasoning_content 增量转成 content 里的 {"type": "reasoning", ...} 块

        Notes:
        1. 先 super() 拿官方结果, 保住 tool_call_chunks / usage_metadata / finish_reason 等全部行为, 再只对 content 做最小改写
           -> 不复制官方逻辑, 升级 langchain-openai 时不易漂移
        2. reasoning 是 langchain 已知块类型: v3 管线按 (块类型, 位置) 归桶后投影到 .reasoning
           -> 逐字流式输出天然成立, 不需要额外事件
        3. index 必须是 REASONING_BLOCK_INDEX (带 "lc_" 前缀的字符串), **不能用整数 0**
           -> 作用: 多段思考在累积成最终 AIMessage 时被 merge_lists 合并成一个块
              (不带 index 时每个 delta 都会在 checkpointer 里各存一个 reasoning 块, 长思考明显膨胀)
           -> 用 0 会和**本条消息里的第 1 个工具调用撞同一桶**:
              v3 管线 (langchain_core/language_models/_compat_bridge.py::chunks_to_events)
              按块自带的 index 归桶, 而 OpenAI 的 tool_calls index 从 0 开始
           -> 撞桶的后果 (实测 langchain-core 1.8.1):
              第 1 个工具调用拿不到自己的 content-block-start, 而 id / name **只放在 start 上**
              (tool-call-delta 仅带 args) => 它的增量被整体丢弃, message.tool_calls 里没有它
              => chat_body.consume_tool_calls_args 不建块 => 流式期间该工具块不显示,
                 只有从会话列表重进 (读库重渲染) 才出现
              => 同时思考块被工具块顶掉 => 落库的 AIMessage 里思考内容丢失
        4. 纯正文 delta 不在改写范围内 -> content 仍是字符串, 与官方行为一致
        """
        generation_chunk = super()._convert_chunk_to_generation_chunk(
            chunk, default_chunk_class, base_generation_info
        )
        # 官方返回 None 表示本 chunk 无需生成内容 (beta.chat.completions.stream 的 content.delta)
        if generation_chunk is None or not isinstance(generation_chunk.message, AIMessageChunk):
            return generation_chunk

        # 本 chunk 的 delta
        # - 兼容 beta.chat.completions.stream 的 {"chunk": {"choices": [...]}} 形状 (与官方一致)
        # - usage 块没有 choices -> 原样返回
        choices = chunk.get("choices") or (chunk.get("chunk") or {}).get("choices") or []
        if not choices:
            return generation_chunk
        delta = choices[0].get("delta")
        if not isinstance(delta, dict):
            return generation_chunk

        # 本 delta 同时带工具调用时**不改写** content
        # -> 实测: content 一旦是 list, v3 管线就会走 "Responses" 解析分支,
        #    而该分支只在 content 里含 function_call 块时才还原 tool_call_chunks,
        #    于是本 delta 的工具调用增量会从事件流里整体消失 (工具名 / 参数首包丢失)
        # -> 权衡: 宁可丢弃这一个 delta 的思考增量, 也不能断工具调用流
        if delta.get("tool_calls") or generation_chunk.message.tool_call_chunks:
            return generation_chunk

        reasoning_content = delta.get("reasoning_content")
        if not reasoning_content:
            return generation_chunk

        # Patch 本体: 非标准字段 -> langchain 已知块
        # index 用 REASONING_BLOCK_INDEX 而非 0: 0 会与第 1 个工具调用撞桶 (见 Note 3)
        content: list[dict] = [{"type": "reasoning", "reasoning": reasoning_content, "index": REASONING_BLOCK_INDEX}]
        # 极少数端点会在同一个 delta 里同时给思考和正文 -> 正文也要一并带上, 否则丢字
        if delta.get("content"):
            content.append({"type": "text", "text": delta["content"]})
        generation_chunk.message.content = content
        return generation_chunk