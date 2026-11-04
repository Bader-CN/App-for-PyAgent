import os
import yaml
from endpoints import EndPoints
from utils.logging import logger


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
            # locales 是只读资源, 随 bundle 一起打包: app_path_root 即 bundle 根 (dev 为 src/),
            # 其下直接就是 locales/, 不再带 src/ 前缀
            lang_conf_file = os.path.abspath(os.path.join(EndPoints.runtime["app_path_root"], f"locales/{lang}.yaml"))
            # 读取指定语言文件
            with open(lang_conf_file, "r", encoding="utf-8") as f:
                self.app_language_dict = yaml.safe_load(f)
        except Exception as e:
            logger.error(e)

    def translate(self, key) -> str:
        """
        根据 key 获取对应语言的翻译内容
        """
        # 守卫: 语言文件加载失败时 app_language_dict 为 None, 直接 .get 会抛
        # AttributeError ('NoneType' object has no attribute 'get'), 这里退化为 ??key??
        if self.app_language_dict is None:
            logger.warning(f"language dict is not loaded, translate({key}) returns placeholder.")
            return f"??{key}??"
        return self.app_language_dict.get(key, f"??{key}??")