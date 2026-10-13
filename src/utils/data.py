import os
import yaml
from pathlib import Path
from typing import Any, Dict, List
from src.endpoints import EndPoints
from src.utils.logging import logger


class FileDataUtils:
    """
    用户的文件级数据工具类
    """
    def __init__(self):
        # App 运行时的根目录
        self.app_path_root = EndPoints.runtime["app_path_root"]
        # App 数据字典
        self.app_data_dict = {
            "sort_chat": None,      # 聊天界面的会话列表
            "sort_agent": None,     # 智能体界面的会话列表
        }

    def data_init(self, data_type: str, data_cont: Dict | List | None = None):
        """
        初始化指定类型的数据文件

        Args:
        - data_type:  对应的数据类型, 目前可选值: "sort_chat", "sort_agent"
        - data_cont:  初始化的数据, 数据类型可以是 Dict / List
        """
        try:
            logger.debug(f"initializing default data_type file: {data_type}")
            filepath = os.path.abspath(os.path.join(self.app_path_root, f"storage/data/{data_type}.yaml"))
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            self.data_save(data_type=data_type, data_cont=data_cont)
        except Exception as e:
            logger.error(e)

    def data_save(self, data_type: str, data_cont: Dict | List | None = None):
        """
        将数据保存到指定类型的数据文件里

        Args:
        - data_type:  对应的数据类型, 目前可选值: "sort_chat", "sort_agent"
        - data_cont:  初始化的数据, 数据类型可以是 Dict / List
        """
        # 基于 data_type 来拼接文件的绝对路径
        filepath = os.path.abspath(os.path.join(self.app_path_root, f"storage/data/{data_type}.yaml"))
        ###################################################
        # 如果 data_cont 为 None, 则初始化对应类型的空数据
        if data_cont is None:
            if data_type in ["sort_chat", "sort_agent"]:
                data_cont = []
            else:
                data_cont = {}
        ###################################################
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                yaml.dump(
                    data_cont,
                    f,
                    allow_unicode=True,         # 允许输出非 ASCII 字符, 而不是将其转义为 Unicode 序列 (例如 \uXXXX)
                    default_flow_style=False,   # 强制 YAML 输出使用 "块风格(block style)", 即每个键值对占一行, 嵌套结构通过缩进表示
                    sort_keys=False,            # 字典键不自动按字母排序输出, 保持原始插入顺序
                    indent=2,                   # 设置缩进空格数为 2
                    width=float('inf')          # 限制行最大宽度, 设为 float('inf') 意味着不强制换行
                )
            # 同步缓存数据
            self.app_data_dict[data_type] = data_cont
            logger.debug(f"write data_type file: {data_type} success.")
        except Exception as e:
            logger.error(e)

    def data_read(self, data_type: str):
        """
        读取指定类型的数据文件

        Args:
        - data_type: 对应的数据类型
        """
        try:
            # 从缓存中读取
            if self.app_data_dict[data_type] is not None:
                return self.app_data_dict[data_type]
            # 从文件中读取
            filepath = os.path.abspath(os.path.join(self.app_path_root, f"storage/data/{data_type}.yaml"))
            with open(filepath, "r", encoding="utf-8") as f:
                self.app_data_dict[data_type] = yaml.safe_load(f)
                return self.app_data_dict[data_type]
        except FileNotFoundError:
            self.data_init(data_type=data_type)
            return self.app_data_dict[data_type]
        except Exception as e:
            logger.error(e)