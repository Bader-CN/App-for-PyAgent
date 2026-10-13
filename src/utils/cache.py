import io
import os
import yaml
import base64
import mimetypes
from pathlib import Path
from src.endpoints import EndPoints
from src.utils.logging import logger
from PIL import Image


class CacheUtils:
    """
    缓存工具类
    """
    def __init__(self):
        # App 运行时的根目录
        self.app_path_root = EndPoints.runtime["app_path_root"]

        # tmp_msgs 字典 & 持久化文件
        self.tmp_msgs_state_dict = {}
        self.tmp_msgs_state_file = os.path.abspath(os.path.join(self.app_path_root, "storage/data/tmp_msgs_state.yaml"))
        
        # 剪切板临时目录
        self.tmp_clipboard_dir = os.path.abspath(os.path.join(self.app_path_root, "storage/temp/clipboard"))

        # 如果文件不存在, 则创建默认 tmp_msgs 文件
        if not Path(self.tmp_msgs_state_file).exists():
            self.tmp_msgs_state_init()
        self.tmp_msgs_state_sync()      # 读取 & 同步 -> EndPoints.tmp_msgs

    def tmp_msgs_init(self, session_id: str, status: str = "stop"):
        """
        初始化指定会话的临时消息缓存 (硬重置)

        Args:
        - session_id:   会话ID
        - status:       初始状态; "stop" = 非流式 (chat_list 用), "start" = 流式进行中 (chat_body 用)

        Note:
        本方法会覆盖既有数据, 目前在如下几处被触发
        - chat_list (点击会话): if EndPoints.tmp_msgs.get(session_id) is None 时触发
        - chat_body (发送消息): 之前内容已经写入数据库, 因此重置缓存
        """
        EndPoints.tmp_msgs[session_id] = {
            "status": status,           # 缓存的会话状态, 值可以是 "start/stop/error/aborted/reasoning/tool_call/text"
            "aimsgs": [],               # 缓存的会话数据
            "reason": None,             # 异常停止的原因, 当 status 为 error/aborted 时要更新此值
            "click_count": 1,           # 每次点击该会话就+1
            "rendered_click_count": 1,  # 必须渲染完历史会话才和 click_count 同步
        }

    def tmp_msgs_del(self, session_id: str):
        """
        删除指定会话的临时缓存

        - session_id:   会话ID
        """
        # 必须得有才能删除
        if EndPoints.tmp_msgs.get(session_id, {}).get("status") in (None, "stop", "error"):
            EndPoints.tmp_msgs.pop(session_id, None)

    def tmp_msgs_state_init(self):
        """
        初始化 tmp_msgs_state 的缓存文件
        """
        try:
            Path(self.tmp_msgs_state_file).parent.mkdir(parents=True, exist_ok=True)
            self.tmp_msgs_state_save()
            logger.debug("initialize tmp_msgs state cache file.")
        except Exception as e:
            logger.error(e)

    def tmp_msgs_state_save(self):
        """
        保存 tmp_msgs state 的缓存文件
        """
        try:
            with open(self.tmp_msgs_state_file, "w", encoding="utf-8") as f:
                yaml.dump(
                    self.tmp_msgs_state_dict, 
                    f, 
                    allow_unicode=True,         # 允许输出非 ASCII 字符, 而不是将其转义为 Unicode 序列 (例如 \uXXXX)
                    default_flow_style=False,   # 强制 YAML 输出使用 "块风格(block style)", 即每个键值对占一行, 嵌套结构通过缩进表示
                    sort_keys=False,            # 字典键不自动按字母排序输出, 保持原始插入顺序
                    indent=2,                   # 设置缩进空格数为 2
                    width=float('inf')          # 限制行最大宽度, 设为 float('inf') 意味着不强制换行
                )
            logger.debug("tmp_msgs state cache file saved successfully.")
        except Exception as e:
            logger.error(e)

    def tmp_msgs_state_sync(self):
        """
        将 tmp_msgs_state 中的内容同步至 EndPoints.tmp_msgs 缓存中
        """
        try:
            # 从文件中读取缓存数据
            with open(self.tmp_msgs_state_file, "r", encoding="utf-8") as f:
                self.tmp_msgs_state_dict = yaml.safe_load(f) or {}
            # 同步至 EndPoints.tmp_msgs
            if self.tmp_msgs_state_dict:
                # 迭代副本 (list 快照)
                # -> 本字典只做单向「启动时镜像」到 EndPoints.tmp_msgs, 循环体不会改动它
                # -> list() 属通用规避: 防将来在循环体内加入 state 写操作后
                #    抛 RuntimeError: dictionary changed size during iteration
                for session_id in list(self.tmp_msgs_state_dict):
                    if EndPoints.tmp_msgs.get(session_id) is None:
                        self.tmp_msgs_init(session_id=session_id)
                    # 仅同步这两项足够
                    EndPoints.tmp_msgs[session_id]["status"] = self.tmp_msgs_state_dict[session_id]["status"]
                    EndPoints.tmp_msgs[session_id]["reason"] = self.tmp_msgs_state_dict[session_id]["reason"]
        except Exception as e:
            logger.error(e)

    def tmp_msgs_state_update(self, session_id, status, reason=None):
        """
        更新 tmp_msgs state 文件缓存: 基于指定的 session_id
        """
        if self.tmp_msgs_state_dict.get(session_id) is None:
            self.tmp_msgs_state_dict[session_id] = {"status": status, "reason": reason}
        else:
            self.tmp_msgs_state_dict[session_id]["status"] = status
            self.tmp_msgs_state_dict[session_id]["reason"] = reason
        self.tmp_msgs_state_save()

    def tmp_msgs_state_del(self, session_id):
        """
        删除 tmp_msgs state 文件缓存: 基于指定的 session_id
        """
        if self.tmp_msgs_state_dict.get(session_id) is not None:
            self.tmp_msgs_state_dict.pop(session_id, None)
            self.tmp_msgs_state_save()

    def clipboard_image_add(self, session_prefix: str, image_data):
        """
        将截图数据保存在 /storage/temp/clipboard 文件夹里

        Args:
        - session_prefix (str): 会话前缀
        - image_data (bytes):   剪切板里的原始数据
        """
        # 设定路径对象
        directory = Path(self.tmp_clipboard_dir)
        # 创建目录 (不存在则创建,含父级; 已存在则跳过)
        directory.mkdir(parents=True, exist_ok=True)
        # 基于 session_prefix 来检索是否存在该会话的截图文件
        images = [f.name for f in directory.iterdir() if f.is_file() and f.suffix == '.png' and f.name.startswith(session_prefix)]

        num = 1
        while True:
            filename = f"{session_prefix}_screenshot_{str(num)}.png"
            if filename not in images:
                image_path = os.path.abspath(os.path.join(self.tmp_clipboard_dir, filename))
                # 用 Pillow 从字节流解析图片, 再重新保存为标准 PNG
                with Image.open(io.BytesIO(image_data)) as img:
                    logger.debug(f"Clipboard image info: format={img.format}, mode={img.mode}, size={img.size}")
                    # 为了兼容性, 统一转成 RGBA 或 RGB
                    if img.mode not in ("RGB", "RGBA"):
                        img = img.convert("RGBA")
                    img.save(image_path, format="PNG")
                break
            num += 1

    def clipboard_image_get(self, session_prefix=None):
        """
        基于指定的 session_prefix 来检索临时的截图文件

        Args:
        - session_prefix (str): 会话前缀

        Return:
        - List[<filename1, filename2>...]
        """
        # 设定路径对象
        directory = Path(self.tmp_clipboard_dir)
        # 创建目录 (不存在则创建,含父级; 已存在则跳过)
        directory.mkdir(parents=True, exist_ok=True)

        if session_prefix is not None:
            images = [f.name for f in directory.iterdir() if f.is_file() and f.suffix == '.png' and f.name.startswith(session_prefix)]
        else:
            images = [f.name for f in directory.iterdir() if f.is_file() and f.suffix == '.png']

        return images

    def clipboard_image_del(self, filename=None, session_prefix=None):
        """
        删除临时目录里的剪切板文件

        Note:
        - 如果 filename 不为 None, 则删除指定文件
        - 如果 session_prefix 不为 None, 则删除指定前缀的截图文件
        - 否则删除整个剪切板临时目录

        Args:
        - filename (str):       基于指定的文件删除文件 (可选)
        - session_prefix (str): 基于指定的会话前缀来删除
        """
        # 设定路径对象
        directory = Path(self.tmp_clipboard_dir)
        # 创建目录 (不存在则创建,含父级; 已存在则跳过)
        directory.mkdir(parents=True, exist_ok=True)

        try:
            if filename is not None:
                Path(os.path.abspath(os.path.join(self.tmp_clipboard_dir, filename))).unlink()
            elif session_prefix is not None:
                files = [f.name for f in directory.iterdir() if f.is_file() and f.name.startswith(session_prefix)]
                for filename in files:
                    Path(os.path.abspath(os.path.join(self.tmp_clipboard_dir, filename))).unlink()
            else:
                directory.unlink()
        except Exception as e:
            logger.error(e)

    def clipboard_image_to_base64(self, filename: str):
        """
        将指定的截图文件转换为 Base64 URI Data
        https://docs.langchain.com/oss/python/langchain/messages#multimodal

        Args:
        - filename: 截图文件名

        Return:
        - str:  形如 "data:image/png;base64,iVBORw0KGgo..." 的数据 URI 字符串
        """
        path = Path(os.path.abspath(os.path.join(self.tmp_clipboard_dir, filename)))
        # 1.读取文件内容 (二进制模式)
        with open(path, "rb") as imgfile:
            encoded_bytes = base64.b64encode(imgfile.read())
        # 2.将字节转换为字符串 (去掉 b'...')
        encoded_str = encoded_bytes.decode('utf-8')
        # 3.自动检测图片的 MIME 类型 (例如 'image/png', 'image/jpeg')
        mime_type, _ = mimetypes.guess_type(os.path.abspath(os.path.join(self.tmp_clipboard_dir, filename)))
        if not mime_type:
            # 如果识别不出来则给个默认值
            mime_type = "application/octet-stream"
        # 4.组装成标准的 Data URI 格式
        data_uri = f"data:{mime_type};base64,{encoded_str}"

        return data_uri