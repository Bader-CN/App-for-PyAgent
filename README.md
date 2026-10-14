# 软件概述
App-for-PyAgent 是一个基于 [LangChain/DeepAgents](https://docs.langchain.com/oss/python/deepagents/overview) + [Flet GUI 框架](https://flet.dev/) 开发的纯 Python 应用
- 支持多模态
- 可以接入任意兼容 openai 和 ollama 类型的 API
- 基于 Python 语言, 可以很方便的进行扩展第三方组件

# 环境依赖
```Shell
# Flet 框架
pip install -U 'flet[all]' -i https://pypi.tuna.tsinghua.edu.cn/simple
# LangChain 相关组件
pip install -U deepagents
pip install -U langchain-openai
pip install -U langchain-ollama
pip install -U langgraph-checkpoint-sqlite
# 其余内容
pip install -U PyYAML
pip install -U pillow
pip install -U loguru
pip install -U aiosqlite
# 测试 (可选, 仅运行 tests/ 时需要)
pip install -U pytest pytest-asyncio
```

# 运行命令
```Shell
cd <App-for-DeepAgent>
# 热更新命令
flet run -r main.py
# 演示命令
flet run main.py
```

# 注意事项
1. 首次运行 `flet run` 是需要联网下载数据, 如果无法下载可尝试配置代理
    ```Shell
    # PowerShell
    $env:HTTP_PROXY="http://<server>:<port>"
    $env:HTTPS_PROXY="http://<server>:<port>"
    ```
2. LangChain 的 OpenAI 不支持 [Non-standard response fields (reasoning_content, reasoning, reasoning_details)](https://docs.langchain.com/oss/python/integrations/chat/openai)
    - 官方结论<br>
        [OpenRouter / LiteLLM / OpenAI API compatibility across providers / proxies](https://github.com/langchain-ai/langchain/issues/34328)
    - 解决办法<br>
        - 对 `langchain_openai/chat_models/base.py` 打两处补丁
        - Patch ① 响应侧 `_convert_delta_to_message_chunk`：把流式 delta 的 `reasoning_content` 增量转成 content 里的
            `{"type":"reasoning","reasoning":<增量>,"index":0}` 块. `reasoning` 是 langchain 已知块类型, v3 流式
            （`astream_events(version="v3")`）按 `index` 合并后投影到 `.reasoning`，实现思考逐字流式输出
            ```Python
            if role == "assistant" or default_class == AIMessageChunk:
                reasoning_content = _dict.get("reasoning_content")
                if reasoning_content:
                    content = [
                        {"type": "reasoning", "reasoning": reasoning_content}
                    ]
                    if _dict.get("content"):
                        content.append({"type": "text", "text": _dict["content"]})
                return AIMessageChunk(
                    content=content,
                    additional_kwargs=additional_kwargs,
                    id=id_,
                    tool_call_chunks=tool_call_chunks,
                )
            ```
        - Patch ② 发送侧 `_format_message_content`：过滤列表加入 `"reasoning"`（**必须与 Patch ① 配套**，
            否则历史消息里的 reasoning 块第二次对话会被透传给 OpenAI 兼容端点 → 400）
            ```Python
            block["type"] in ("tool_use", "thinking", "reasoning_content", "reasoning")
            ```