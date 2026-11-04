import os
import sys
import threading
from pathlib import Path

from loguru import logger

logger.remove()
# logger.add(sys.stderr, level="DEBUG")
logger.add(sys.stderr, level="TRACE")

# 文件日志的文件名 (轮转时 loguru 会生成 app.2026-11-04_xx.log 之类的副本)
LOG_FILE_NAME = "app.log"


def setup_file_logging(log_dir: str, level: str = "DEBUG", rotation: str = "10 MB", retention: int = 10) -> str:
    """
    添加文件 sink, 把日志持久化到可写目录

    Note:
    1. 打包后的 bundle 是只读的, 日志**不能**写在 exe 旁边
       -> 调用方应传入 EndPoints.runtime["app_path_data"] 下的子目录 (FLET_APP_STORAGE_DATA)
    2. 级别默认 DEBUG, 与 stderr 的 TRACE 分开:
       -> stderr 供 dev 终端实时看全量; 打包版 stderr 被 Flet 接到缓存目录的 console.log
          (下次启动会覆盖 / 系统可能清理), 不适合事后排查
       -> 文件 sink 用 DEBUG 已足够定位问题, 同时避免 TRACE 把文件撑爆
    3. diagnose=False 是刻意的:
       -> True 会把异常栈的局部变量 (含 api_key / 请求头) 一并写进日志
    4. 不启用 enqueue:
       -> loguru 的 sink 本身线程安全; enqueue 走 multiprocessing.Queue, 在 serious_python 嵌入环境下多余
    5. rotation / retention 的边界: 同一目录只允许运行一个实例
       -> 多实例同时写同一文件时, Windows 下轮转重命名会失败 (loguru 捕获后只打到 stderr)

    Args:
    - log_dir:   日志目录 (不存在时递归创建)
    - level:     文件 sink 的日志级别
    - rotation:  轮转阈值 (loguru 语法: "10 MB" / "1 day" ...)
    - retention: 保留的历史日志份数 (不含当前 app.log; 实测 retention=2 + rotation 会留下 3 个文件)

    Returns:
    - str: 日志文件的绝对路径
    """
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_file = os.path.abspath(os.path.join(log_dir, LOG_FILE_NAME))
    logger.add(
        log_file,
        level=level,
        rotation=rotation,
        retention=retention,
        encoding="utf-8",
        backtrace=True,
        diagnose=False,
    )
    return log_file


def install_exception_hooks():
    """
    把「未捕获异常」也写进日志

    Note:
    - 只处理真正漏网的异常: 回调内部的异常已在各处 try/except 中 logger.exception 记录, 不会重复
    - sys.excepthook:        主线程未捕获异常 (含脚本顶层)
    - threading.excepthook:  子线程未捕获异常 (asyncio.to_thread 的工作线程走这里)
    - KeyboardInterrupt 交回默认实现, 避免 Ctrl+C 也刷一条 error
    """
    def _excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.opt(exception=(exc_type, exc_value, exc_tb)).error("uncaught exception")

    def _thread_excepthook(args):
        if issubclass(args.exc_type, KeyboardInterrupt):
            threading.__excepthook__(args)
            return
        thread_name = args.thread.name if args.thread is not None else "unknown"
        logger.opt(exception=(args.exc_type, args.exc_value, args.exc_traceback)).error(f"uncaught exception in thread: {thread_name}")

    sys.excepthook = _excepthook
    threading.excepthook = _thread_excepthook