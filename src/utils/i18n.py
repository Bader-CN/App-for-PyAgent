import os
import yaml
from src.endpoints import EndPoints
from src.utils.logging import logger


class LanguageUtils:
    """
    多语言翻译类
    """
    def __init__(self):
        # 当前语言字典
        self.app_language_dict = None
        # 首次加载时更新 EndPoints.runtime["app_language"] 中的值
        if EndPoints.runtime["app_language"] is None:
            EndPoints.runtime["app_util_profile"].language()
        # 加载语言字典
        self.language_load()

    def language_load(self):
        """
        加载指定语言的翻译文件
        """
        try:
            lang = EndPoints.runtime["app_language"]
            lang_conf_file = os.path.abspath(os.path.join(EndPoints.runtime["app_path_root"], f"src/locales/{lang}.yaml"))
            # 读取指定语言文件
            with open(lang_conf_file, "r", encoding="utf-8") as f:
                self.app_language_dict = yaml.safe_load(f)
        except Exception as e:
            logger.error(e)

    def translate(self, key) -> str:
        """
        根据 key 获取对应语言的翻译内容
        """
        return self.app_language_dict.get(key, f"??{key}??")