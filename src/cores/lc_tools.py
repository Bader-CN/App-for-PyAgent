import base64
import binascii
import datetime
import re
import requests
from urllib.parse import parse_qs, quote, urljoin, urlparse
from bs4 import BeautifulSoup
from langchain.tools import tool

from src.endpoints import EndPoints
from src.utils.logging import logger


class LC_Tools:
    """
    LangChain 内嵌工具类
    """
    @tool
    @staticmethod
    def get_currently_datetime_and_weekday() -> dict:
        """
        获取当前的时间和日期

        Notes:
        - 不需要输入任何参数
        - 返回内容包含当前是星期几

        Returns:
        - Dict: {"current_date": formated_now, "weekday": full_weekday}
        """
        # 当前时间
        current_date = datetime.datetime.now()
        # 格式化后的时间
        formated_now = current_date.strftime("%Y-%m-%d %H:%M:%S")
        # 完整星期名
        full_weekday = current_date.strftime("%A")

        return {"current_date": formated_now, "weekday": full_weekday}

    @tool
    @staticmethod
    def http_request_get_with_keyword(keyword: str) -> str:
        """
        使用关键词在搜索引擎中搜索
        请优先使用此工具, 待确认 URL 链接后再使用 http_request_get_with_url 来获取详细内容

        Notes:
        - keyword: 搜索关键词
        - 内部将 keyword 拼接为对应引擎的搜索 URL 后发送 GET 请求

        Returns:
        - str: 搜索结果的 Markdown 编号列表(标题 + 可直接访问的绝对 URL + 摘要);
               请求失败时返回以 "请求失败" 开头的说明
        """
        profile = EndPoints.runtime["app_util_profile"]

        # 搜索引擎: 配置值大小写/前后空白不定, 归一化后再查表
        engine = (profile.web_search_engine() or "").strip().lower()
        if engine not in HTML_Utils.WEB_SEARCH_ENTRY:
            logger.warning(
                f"unknown web search engine: {engine}, "
                f"falling back to {HTML_Utils.WEB_SEARCH_ENGINE_DEFAULT}"
            )
            engine = HTML_Utils.WEB_SEARCH_ENGINE_DEFAULT
        # {keyword} 占位: quote 负责百分号编码(空格/中文)
        url = HTML_Utils.WEB_SEARCH_ENTRY[engine].format(keyword=quote(keyword))

        # 代理: 仅在设置页开启「搜索代理」且地址非空时启用, 否则传 None 走直连
        proxies = None
        if profile.web_search_proxy():
            proxy_addr = (profile.proxy_address() or "").strip()
            if proxy_addr:
                proxies = {"http": proxy_addr, "https": proxy_addr}
                # no_proxy 让设置页的忽略规则生效(requests 的 merge_environment_settings 会消费它)
                proxy_ignore = (profile.proxy_ignore() or "").strip()
                if proxy_ignore:
                    proxies["no_proxy"] = proxy_ignore
            else:
                # 开了开关却没填地址: 直连而非报错, 否则搜索工具直接不可用
                logger.warning("web search proxy is enabled but address is empty, direct connection")

        # 模拟浏览器 UA: 无 UA 的请求可能被当作 bot 拦截(必应还会返回简化页或验证页)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            )
        }
        # timeout 必须有: 否则站点挂起会无限阻塞, 整个 agent run 一起卡死
        # 异常不外抛: @tool 默认 handle_tool_error=False, 抛出会中断图执行, 模型只会觉得工具凭空消失; 
        # 返回字符串才能让模型看到失败原因并改试别的 URL
        try:
            res = requests.get(url, headers=headers, timeout=20, proxies=proxies)
            # requests 在响应头未声明 charset 时会猜成 ISO-8859-1 -> 中文站乱码, 用探测结果纠正
            if res.encoding == "ISO-8859-1":
                res.encoding = res.apparent_encoding
            res.raise_for_status()
        except requests.exceptions.RequestException as e:
            return f"请求失败: {type(e).__name__}: {e}"

        # 非文本响应(图片/PDF/压缩包等)直接拒: 否则 res.text 是二进制乱码, 白烧 token
        ctype = res.headers.get("Content-Type", "").split(";")[0]
        if not any(kind in ctype for kind in ("html", "xml", "json", "text")):
            return f"该 URL 返回非文本内容 (Content-Type: {ctype}), 无法作为文本阅读"

        # 内容处理全部在 HTML_Utils, 本工具只负责"取":
        # base_url 传 res.url(重定向后的最终地址), 而非请求时的原始 URL
        if engine == "duckduckgo":
            return HTML_Utils.http_content_format_keyword_ddg(res.text, res.url)
        return HTML_Utils.http_content_format_keyword_bing(res.text, res.url)


    @tool
    @staticmethod
    def http_request_get_with_url(url: str) -> str:
        """
        使用指定的 URL 来获取网页的内容

        Notes:
        - 请优先使用 http_request_get_with_keyword 相关工具来获取详细的 URL
        - 待明确 URL 之后, 可以使用此工具来进一步查看网页详情
        - 脚本/样式/导航等噪声会被剔除, 页面过长时只返回开头部分

        Returns:
        - str: 网页正文的纯文本内容(保留超链接); 请求失败时返回以 "请求失败" 开头的说明
        """
        profile = EndPoints.runtime["app_util_profile"]

        # 代理: 仅在设置页开启「搜索代理」且地址非空时启用, 否则传 None 走直连
        # 与 http_request_get_with_keyword 内的同款判断保持一致(刻意为每处调用就地自解释)
        proxies = None
        if profile.web_search_proxy():
            proxy_addr = (profile.proxy_address() or "").strip()
            if proxy_addr:
                proxies = {"http": proxy_addr, "https": proxy_addr}
                # no_proxy 让设置页的忽略规则生效(requests 的 merge_environment_settings 会消费它)
                proxy_ignore = (profile.proxy_ignore() or "").strip()
                if proxy_ignore:
                    proxies["no_proxy"] = proxy_ignore
            else:
                # 开了开关却没填地址: 直连而非报错, 否则抓取工具直接不可用
                logger.warning("web search proxy is enabled but address is empty, direct connection")

        # 模拟浏览器 UA: 必应对无 UA 的请求可能返回简化页或验证页
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            )
        }
        # timeout 必须有: 否则站点挂起会无限阻塞, 整个 agent run 一起卡死
        # 异常不外抛: @tool 默认 handle_tool_error=False, 抛出会中断图执行, 模型只会觉得工具凭空消失; 
        # 返回字符串才能让模型看到失败原因并改试别的 URL
        try:
            res = requests.get(url, headers=headers, timeout=20, proxies=proxies)
            # requests 在响应头未声明 charset 时会猜成 ISO-8859-1 -> 中文站乱码, 用探测结果纠正
            if res.encoding == "ISO-8859-1":
                res.encoding = res.apparent_encoding
            res.raise_for_status()
        except requests.exceptions.RequestException as e:
            return f"请求失败: {type(e).__name__}: {e}"

        # 非文本响应(图片/PDF/压缩包等)直接拒: 否则 res.text 是二进制乱码, 白烧 token
        ctype = res.headers.get("Content-Type", "").split(";")[0]
        if not any(kind in ctype for kind in ("html", "xml", "json", "text")):
            return f"该 URL 返回非文本内容 (Content-Type: {ctype}), 无法作为文本阅读"

        # 内容处理全部在 HTML_Utils, 本工具只负责"取":
        # base_url 传 res.url(重定向后的最终地址), 而非请求时的原始 URL
        return HTML_Utils.http_content_format_url(res.text, res.url)


class HTML_Utils:
    """
    HTML 解析的底层工具集合, 该内容不向 LangChain 暴露

    参数设计: 
    各方法均接收 (http_content, base_url) 双参数而非单个字符串或单个 URL
    - http_content: 页面正文本身(解析的原料)
    - base_url:     正文的出处(元数据), 缺了相对链接无法 urljoin 还原

    调用方应:
    - 传 requests 重定向后的 res.url 而非请求时的原始 URL (基准域可能已变)
    - 不传整个 Response 对象, 那会让本类绑死 requests, 失去"纯处理层"可单测的性质
    """
    WEB_SEARCH_ENTRY = {
        "bing":       "https://www.bing.com/search?q={keyword}",
        "duckduckgo": "https://lite.duckduckgo.com/lite/?q={keyword}",
    }
    # 配置缺失 / 引擎名不认识时的回退项: 必应对纯 HTTP 客户端最稳
    WEB_SEARCH_ENGINE_DEFAULT = "bing"
    # 整块丢弃: 脚本/样式是纯噪声, nav/footer 等是页面骨架而非正文
    SKIP_TAGS = {
        "script", "style", "noscript", "svg", "template", "iframe",
        "nav", "footer", "header", "aside", "form", "button", "select",
    }
    # 块级标签: 前后补换行, 否则段落会全部黏成一行
    BLOCK_TAGS = {
        "p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6",
        "tr", "table", "thead", "tbody", "dl", "dt", "dd", "section", "article",
        "blockquote", "pre", "hr", "figcaption", "main",
    }
    # 返回给模型的最大字符数: 防止整页 HTML 撑爆 context
    MAX_CHARS = 128000

    @staticmethod
    def collapse_whitespace(text):
        """
        压缩 DOM 抽取后的残留空白
        """
        # [^\S\n] = 除换行外的所有空白(含 NBSP/EN SPACE 等)
        text = re.sub(r"[^\S\n]+", " ", text)
        text = re.sub(r" ?\n ?", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def unwrap_redirect_bing(url):
        """
        还原必应结果链接中的跳转地址

        必应给纯 HTTP 客户端的结果 URL 形如:
        https://www.bing.com/ck/a?...&u=a1<base64url(真实URL)>
        模型若直接抄这种链接再喂给 http_request_get_with_url, 拿到的是必应的跳转页而非目标页
        因此解析 SERP 时必须先解码出真实 URL

        解码步骤: u 参数去掉 "a1" 前缀 -> 补 "=" 填充到 4 的倍数 -> urlsafe_b64decode -> utf-8
        任何一步失败(必应改版 / 非跳转链)都原样返回入参, 不抛异常
        """
        parts = urlparse(url)
        if "bing.com" not in parts.netloc or "/ck/" not in parts.path:
            return url
        encoded = parse_qs(parts.query).get("u", [""])[0]
        if not encoded.startswith("a1"):
            return url
        encoded = encoded[2:]
        try:
            padded = encoded + "=" * (-len(encoded) % 4)
            return base64.urlsafe_b64decode(padded).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            return url

    @staticmethod
    def unwrap_redirect_ddg(url):
        """
        还原 DuckDuckGo 结果链接中的跳转地址

        DDG 给的结果 URL 形如(注意以 // 开头, 调用方需先 urljoin 补 scheme):
        //duckduckgo.com/l/?uddg=https%3A%2F%2Fpytorch.org%2F&rut=<hash>
        uddg 参数就是 URL 编码后的真实地址, parse_qs 取值时已自动解码一层, 比必应的 base64 跳转简单。
        解码失败(非跳转链 / DDG 改版)原样返回入参, 不抛异常。
        """
        parts = urlparse(url)
        if "duckduckgo.com" not in parts.netloc or "/l/" not in parts.path:
            return url
        return parse_qs(parts.query).get("uddg", [url])[0] or url

    @staticmethod
    def http_content_format_keyword_bing(http_content, base_url):
        """
        在关键字检索时, 对获取到的 HTTP 内容进行整理

        针对必应搜索结果页 (SERP) 做定向抽取: 每个 li.b_algo 提取标题 / 真实 URL / 摘要
        输出 Markdown 编号列表 (相比通用正文抽取, 结果更干净、token 更省)
        若一个结果都没命中 (必应改版或验证页), 回退到通用抽取兜底, 避免返回空
        """
        soup = BeautifulSoup(http_content, "html.parser")
        items = soup.select("ol#b_results > li.b_algo")
        if not items:
            # 结构没命中不等于抓到了垃圾页: 退回通用抽取, 让模型至少能看到页面内容
            return HTML_Utils.http_content_format_url(http_content, base_url)

        lines = []
        for i, li in enumerate(items, start=1):
            link_tag = li.select_one("h2 a[href]")
            if link_tag is None:
                continue
            title = link_tag.get_text(" ", strip=True)
            # 相对地址先转绝对, 再解必应跳转: 两步顺序不能反(ck/a 本身可能以相对形式出现)
            href = urljoin(base_url, link_tag["href"])
            href = HTML_Utils.unwrap_redirect_bing(href)
            snippet_tag = li.select_one("p")
            snippet = snippet_tag.get_text(" ", strip=True) if snippet_tag else ""
            line = f"{i}. [{title}]({href})"
            if snippet:
                line += f"\n   {snippet}"
            lines.append(line)

        if not lines:
            return HTML_Utils.http_content_format_url(http_content, base_url)
        return "\n\n".join(lines)

    @staticmethod
    def http_content_format_keyword_ddg(http_content, base_url):
        """
        在 DuckDuckGo 关键字检索时, 对获取到的 HTTP 内容进行整理

        针对 DDG lite 结果页做定向抽取: a.result-link 取标题与真实 URL,
        摘要在相邻的 td.result-snippet。输出 Markdown 编号列表。
        若一个结果都没命中(改版或反爬页), 回退到通用抽取兜底, 避免返回空。
        """
        soup = BeautifulSoup(http_content, "html.parser")
        links = soup.select("a.result-link")
        if not links:
            # 结构没命中不等于抓到了垃圾页: 退回通用抽取, 让模型至少能看到页面内容
            return HTML_Utils.http_content_format_url(http_content, base_url)

        lines = []
        for i, a_tag in enumerate(links, start=1):
            title = a_tag.get_text(" ", strip=True)
            if not title:
                continue
            # href 以 // 开头(协议相对), 必须先 urljoin 补 scheme 才能解出 uddg
            href = HTML_Utils.unwrap_redirect_ddg(urljoin(base_url, a_tag.get("href") or ""))
            # 摘要按 DOM 结构配对(link 所在 tr 的下一个兄弟 tr), 而非按列表下标:
            # 某条结果缺摘要时按下标会整体错位, 按结构只丢那一条
            snippet = ""
            link_row = a_tag.find_parent("tr")
            next_row = link_row.find_next_sibling("tr") if link_row else None
            if next_row is not None:
                snippet_tag = next_row.select_one("td.result-snippet")
                snippet = snippet_tag.get_text(" ", strip=True) if snippet_tag else ""
            line = f"{i}. [{title}]({href})"
            if snippet:
                line += f"\n   {snippet}"
            lines.append(line)

        if not lines:
            return HTML_Utils.http_content_format_url(http_content, base_url)
        return "\n\n".join(lines)

    @staticmethod
    def http_content_format_url(http_content, base_url):
        """
        在指定 URL 抓取时, 对获取到的 HTTP 内容进行整理

        通用正文抽取(bs4 DOM 解析, 不用正则):
        丢弃脚本/样式/页面骨架, 块级标签补换行, 超链接转 Markdown 并绝对化, 压缩空白, 超长截断
        """
        soup = BeautifulSoup(http_content, "html.parser")

        # 噪声标签整块移除(decompose 连同子树一起删)
        for tag in soup.find_all(list(HTML_Utils.SKIP_TAGS)):
            tag.decompose()

        # <a> -> [文字](绝对URL): 空 href / 锚点 / JS 伪链接对模型无意义, 只留文字
        for a_tag in soup.find_all("a"):
            href = a_tag.get("href") or ""
            # 链接文字压成一行: 否则 markdown 链接跨行会断; 图标类空链接没有可读文字, 整条丢掉
            link_text = a_tag.get_text(" ", strip=True)
            if href and not href.startswith(("#", "javascript:")) and link_text:
                # 相对 URL 必须转绝对: 否则模型抄下来再喂给本工具会 404
                a_tag.replace_with(f"[{link_text}]({urljoin(base_url, href)})")
            else:
                a_tag.replace_with(link_text)

        # 块级标签前后补换行, 否则段落会全部黏成一行
        for tag in soup.find_all(list(HTML_Utils.BLOCK_TAGS)):
            tag.insert_before("\n")
            tag.insert_after("\n")

        text = HTML_Utils.collapse_whitespace(soup.get_text())

        if len(text) > HTML_Utils.MAX_CHARS:
            total = len(text)
            text = text[:HTML_Utils.MAX_CHARS] + f"\n\n[内容已截断: 仅显示前 {HTML_Utils.MAX_CHARS} / {total} 字符]"

        return text
