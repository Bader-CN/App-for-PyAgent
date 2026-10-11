import datetime
import re
import requests
from html.parser import HTMLParser
from urllib.parse import quote, urljoin
from langchain.tools import tool

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
        使用关键词在必应(Bing)搜索引擎中搜索

        Notes:
        - keyword: 搜索关键词
        - 内部将 keyword 拼接为必应搜索 URL 后发送 GET 请求

        Returns:
        - str: 搜索结果的纯文本摘要, 其中每条结果的链接为可直接访问的绝对 URL
        """
        # 必应搜索入口: keyword 作为查询参数 q, quote 负责百分号编码(空格/中文)
        # 复用 with_url 的抓取与清洗逻辑: 走 .func 调用内层原函数, 避免再套一层 tool 包装
        return LC_Tools.http_request_get_with_url.func(
            url=f"https://www.bing.com/search?q={quote(keyword)}"
        )


    @tool
    @staticmethod
    def http_request_get_with_url(url: str) -> str:
        """
        使用指定的 URL 来获取网页的内容

        Notes:
        - 请优先使用 http_request_get_with_keyword 工具来获取详细的 URL
        - 待明确 URL 之后, 可以使用此工具来进一步查看网页详情
        - 脚本/样式/导航等噪声会被剔除, 页面过长时只返回开头部分

        Returns:
        - str: 网页正文的纯文本内容(保留超链接); 请求失败时返回以 "请求失败" 开头的说明
        """
        # 返回给模型的最大字符数: 防止整页 HTML 撑爆 context
        max_chars = 128000
        # 模拟浏览器 UA: 必应对无 UA 的请求可能返回简化页或验证页
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            )
        }
        # timeout 必须有: 否则站点挂起会无限阻塞, 整个 agent run 一起卡死
        # 异常不外抛: @tool 默认 handle_tool_error=False, 抛出会中断图执行,
        #            模型只会觉得工具凭空消失; 返回字符串才能让模型看到失败原因并改试别的 URL
        try:
            res = requests.get(url, headers=headers, timeout=20)
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

        # HTML -> 纯文本: 用标准库 DOM 解析, 不用正则
        # (正则删 <script> 遇到内嵌 <!-- 或未闭合标签会误吞正文)
        class _TextExtractor(HTMLParser):
            # 整块丢弃: 脚本/样式是纯噪声, nav/footer 等是页面骨架而非正文
            _SKIP_TAGS = {
                "script", "style", "noscript", "svg", "template", "iframe",
                "nav", "footer", "header", "aside", "form", "button", "select",
            }
            # 块级标签: 前后补换行, 否则段落会全部黏成一行
            _BLOCK_TAGS = {
                "p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6",
                "tr", "table", "thead", "tbody", "dl", "dt", "dd", "section", "article",
                "blockquote", "pre", "hr", "figcaption", "main",
            }

            def __init__(self, base_url):
                super().__init__(convert_charrefs=True)
                self.base_url = base_url
                self.parts = []
                self.skip_depth = 0
                # 当前 <a> 的绝对 URL; None 表示不在链接内, 或该链接不值得保留
                self.link_href = None
                # 当前 <a> 的正文在 parts 里的起始下标(用切片取, 不能 pop: 空链接时栈顶是自己)
                self.link_start = 0

            def handle_starttag(self, tag, attrs):
                if tag in self._SKIP_TAGS:
                    self.skip_depth += 1
                    return
                if tag in self._BLOCK_TAGS:
                    self.parts.append("\n")
                if tag == "a":
                    href = dict(attrs).get("href") or ""
                    # 锚点/JS 伪链接对模型无意义
                    if not href or href.startswith(("#", "javascript:")):
                        self.link_href = None
                        return
                    # 相对 URL 必须转绝对: 否则模型抄下来再喂给本工具会 404
                    self.link_href = urljoin(self.base_url, href)
                    self.link_start = len(self.parts)

            def handle_endtag(self, tag):
                if tag in self._SKIP_TAGS:
                    self.skip_depth = max(0, self.skip_depth - 1)
                    return
                if tag in self._BLOCK_TAGS:
                    self.parts.append("\n")
                if tag == "a" and self.link_href is not None:
                    link_text = "".join(self.parts[self.link_start:])
                    del self.parts[self.link_start:]
                    # 图标类空链接(如必应顶部 tab)没有可读文字, 整条丢掉
                    # 链接文字压成一行: 否则 markdown 链接跨行会断
                    link_text = link_text.replace("\n", " ").strip()
                    if link_text:
                        self.parts.append(f"[{link_text}]({self.link_href})")
                    self.link_href = None

            def handle_data(self, data):
                if not self.skip_depth and data:
                    self.parts.append(data)

        parser = _TextExtractor(res.url)
        try:
            parser.feed(res.text)
        except Exception:
            # 残缺 HTML 已解析出的部分照用, 不因尾部脏数据丢整页
            pass

        text = "".join(parser.parts)
        # [^\S\n] = 除换行外的所有空白(含 NBSP/EN SPACE 等): 必应正文里混了不少
        text = re.sub(r"[^\S\n]+", " ", text)
        text = re.sub(r" ?\n ?", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = text.strip()

        if len(text) > max_chars:
            total = len(text)
            text = text[:max_chars] + f"\n\n[内容已截断: 仅显示前 {max_chars} / {total} 字符]"

        return text