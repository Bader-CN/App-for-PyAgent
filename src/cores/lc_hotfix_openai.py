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
        3. index: 0 让多段思考在累积成最终 AIMessage 时被 merge_lists 合并成一个块
           -> 不带 index 时每个 delta 都会在 checkpointer 里各存一个 reasoning 块, 长思考明显膨胀
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
        content: list[dict] = [{"type": "reasoning", "reasoning": reasoning_content, "index": 0}]
        # 极少数端点会在同一个 delta 里同时给思考和正文 -> 正文也要一并带上, 否则丢字
        if delta.get("content"):
            content.append({"type": "text", "text": delta["content"]})
        generation_chunk.message.content = content
        return generation_chunk