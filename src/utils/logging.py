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


def setup_logger_file(log_dir: str, level: str = "DEBUG", rotation: str = "10 MB", retention: int = 10) -> str:
    """
    添加文件 sink, 把日志持久化到可写文件中
    https://loguru.readthedocs.io/en/stable/overview.html#easier-file-logging-with-rotation-retention-compression

    Note:
    1. 级别默认 DEBUG, 与 stderr 的 TRACE 分开:
    2. diagnose=False 是刻意的 (暂定)
       -> True 会把异常栈的局部变量 (含 api_key / 请求头) 一并写进日志

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
        # 轮转方式: 10 MB
        rotation=rotation,
        # 保留个数
        retention=retention,
        encoding="utf-8",
        backtrace=True,
        diagnose=False,
    )
    return log_file


def setup_logger_exception_hooks():
    """
    把「未捕获异常」也写进日志

    Note:
    - 只处理真正漏网的异常
      -> 回调内部的异常已在各处 try/except 中 logger.exception 记录, 不会重复
    - KeyboardInterrupt 交回默认实现, 避免 Ctrl+C 也刷一条 error
    """
    def _excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        # https://loguru.readthedocs.io/en/stable/overview.html#lazy-evaluation-of-expensive-functions
        # 在生产环境中记录详细信息而又不影响性能, 可以使用 opt() 方法来实现
        logger.opt(exception=(exc_type, exc_value, exc_tb)).error("uncaught exception")

    def _thread_excepthook(args):
        if issubclass(args.exc_type, KeyboardInterrupt):
            threading.__excepthook__(args)
            return
        thread_name = args.thread.name if args.thread is not None else "unknown"
        # https://loguru.readthedocs.io/en/stable/overview.html#lazy-evaluation-of-expensive-functions
        # 在生产环境中记录详细信息而又不影响性能, 可以使用 opt() 方法来实现
        logger.opt(exception=(args.exc_type, args.exc_value, args.exc_traceback)).error(f"uncaught exception in thread: {thread_name}")

    # 只在主线程、异常一路冒泡到解释器顶层时才被调用
    sys.excepthook = _excepthook
    # Python 3.8+ 的 threading.excepthook, 接管 Thread.run() 里冒出来的异常
    threading.excepthook = _thread_excepthook