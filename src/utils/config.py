import os
import yaml

from pathlib import Path
from typing import Any, Dict, List
from src.endpoints import EndPoints
from src.utils.logging import logger


class ConfigUtils:
    """
    App 配置文件工具类
    """
    def __init__(self):
        # App 运行时的根目录
        self.app_path_root = EndPoints.runtime["app_path_root"]
        # App 配置文件路径
        self.app_conf_file = os.path.abspath(os.path.join(self.app_path_root, "storage/conf/config.yaml"))
        # App 配置字典
        self.app_conf_dict = None
        # App 默认设置
        self.api_url = "http://<api_base_url>:<port>/v1"
        self.api_key = "sk-****"
        self.api_type = "OpenAI"

        # 如果文件不存在, 则创建默认配置
        if not Path(self.app_conf_file).exists():
            self.conf_init()
        # 读取配置文件
        self.app_conf_dict = self.conf_read()

    def conf_init(self):
            """
            初始化配置
            """
            # 初始化配置文件
            self.app_conf_dict = {
                # 通用设置
                "general_settings": {
                    "language": "zh_cn",
                },
                # 模型服务
                "model_providers": {
                    "default_provider_1": {
                        "api_url": self.api_url,
                        "api_key": self.api_key,
                        "api_type": self.api_type,
                        "enable": True,
                        "models": [
                            {
                                "model_id": "model_id",
                                "model_name": "model_name",
                                "model_feats": {"vision": True, "embed": False, "reranker": False},
                            },
                        ],
                    },
                },
            }
            # 创建目录并保存配置
            try:
                Path(self.app_conf_file).parent.mkdir(parents=True, exist_ok=True)
                self.conf_save()
                logger.warning("Initialize default configuration file.")
            except Exception as e:
                logger.error(e)

    def conf_read(self) -> Dict:
            """
            读取 YAML 文件并返回解析后的 Dict 对象
    
            Return
            - Dict: 解析后的配置信息
            """
            try:
                with open(self.app_conf_file, "r", encoding="utf-8") as f:
                    self.app_conf_dict = yaml.safe_load(f)
                    return self.app_conf_dict
            except Exception as e:
                logger.error(e)

    def conf_save(self):
        """
        写入 YAML 配置文件
        """
        try:
            with open(self.app_conf_file, "w", encoding="utf-8") as f:
                yaml.dump(
                    self.app_conf_dict, 
                    f, 
                    allow_unicode=True,         # 允许输出非 ASCII 字符, 而不是将其转义为 Unicode 序列 (例如 \uXXXX)
                    default_flow_style=False,   # 强制 YAML 输出使用 "块风格(block style)", 即每个键值对占一行, 嵌套结构通过缩进表示
                    sort_keys=False,            # 字典键不自动按字母排序输出, 保持原始插入顺序
                    indent=2,                   # 设置缩进空格数为 2
                    width=float('inf')          # 限制行最大宽度, 设为 float('inf') 意味着不强制换行
                )
            logger.success("Configuration file saved successfully.")
        except Exception as e:
            logger.error(e)

    def models_list_enable(self) -> list:
        """
        获取所有的可选模型列表
        格式: "provider_name/model_name"
        
        Return
        - List[str]: provider_name / model_name
        """
        all_models_list = []
        model_providers = self.app_conf_dict.get("model_providers")
        if model_providers is not None:
            # 必须有 provider_name
            for provider in model_providers:
                # provider_name 里必须有 models & provider_name 必须被启用
                if model_providers[provider].get("models") is not None and model_providers[provider].get("enable"):
                    for model in model_providers[provider].get("models"):
                        all_models_list.append(f"{provider}/{model.get("model_name")}")
        # 返回所有的 provider_name / model_name 列表
        return all_models_list

    def providers_dict(self) -> Dict:
        """
        获取所有模型服务提供者
        """
        model_providers = self.app_conf_dict.get("model_providers")
        if model_providers is not None:
            return model_providers
        else:
            logger.error("model_providers cannot be empty!")
            return None

    def provider_dict(self, provider_name:str) -> Dict:
        """
        获取指定 "provider_name" 的字典数据

        Notes:
        - 返回的字典中, models 这个字段可能为 None
        
        Args:
        - provider_name:   模型提供商名称

        Return:
        - Dict: 模型的字典数据: {'api_url': 'http://<api_base_url>', 'api_key': 'sk-***', 'api_type': 'openai', 'enable': True, 'models': None}
        """
        model_providers = self.app_conf_dict.get("model_providers")
        if model_providers is not None:
            return model_providers.get(provider_name)
        else:
            logger.error(f"Not found provider: {provider_name}, Please check your configuration file.")
            return None

    def provider_add(self, provider_name:str):
        """
        添加一个模型提供商

        Args:
        - provider_name:   模型提供商名称
        """
        model_providers = self.app_conf_dict.get("model_providers")
        model_providers[provider_name] = {
            "api_url": self.api_url,
            "api_key": self.api_key,
            "enable": False,
            "api_type": self.api_type,
        }
        self.conf_save()

    def provider_del(self, provider_name:str):
        """
        删除指定的模型提供商
        
        Args:
        - provider_name:   模型提供商名称
        """
        model_providers = self.app_conf_dict.get("model_providers")
        model_providers.pop(provider_name)
        self.conf_save()

    def provider_api_url(self, provider_name: str) -> str | None :
        """
        获取模型提供商的 API URL

        Args:
        - provider_name:   模型提供商名称
        """
        model_providers = self.app_conf_dict.get("model_providers")
        if model_providers is not None:
            return model_providers[provider_name].get("api_url").strip()
        else:
            logger.warning(f"API_URL of the model provider cannot be empty. provider_name is {provider_name}")
            return None

    def provider_api_url_set(self, provider_name: str, api_url: str):
        """
        设置模型提供商的 API URL

        Args:
        - provider_name:   模型提供商名称
        - api_url:         API URL
        """
        model_providers = self.app_conf_dict.get("model_providers")
        try:
            if model_providers is not None:
                model_providers[provider_name]["api_url"] = api_url.strip()
                self.conf_save()
            else:
                logger.error(f"Can't set the API URL of the model provider: {provider_name}")
        except Exception as e:
            logger.error(f"Can't set the API URL of the model provider: {provider_name}, error is {e}")

    def provider_api_key(self, provider_name: str) -> str | None :
        """
        获取模型提供商的 API Key

        Args:
        - provider_name:   模型提供商名称
        """
        model_providers = self.app_conf_dict.get("model_providers")
        if model_providers is not None:
            return model_providers[provider_name].get("api_key").strip()
        else:
            return None

    def provider_api_key_set(self, provider_name: str, api_key: str):
        """
        设置模型提供商的 API Key

        Args:
        - provider_name:   模型提供商名称
        - api_key:         API Key
        """
        model_providers = self.app_conf_dict.get("model_providers")
        try:
            if model_providers is not None:
                model_providers[provider_name]["api_key"] = api_key.strip()
                self.conf_save()
        except Exception as e:
            logger.error(f"Error setting API key for {provider_name}, error is {e}")

    def provider_api_type(self, provider_name: str):
        """
        获取模型提供商的 API Type

        Args:
        - provider_name:   模型提供商名称
        """
        model_providers = self.app_conf_dict.get("model_providers")
        if model_providers is not None:
            return model_providers[provider_name].get("api_type").strip()
        return None

    def provider_api_type_set(self, provider_name: str, api_type: str):
        """
        设置模型提供商的 API Type

        Args:
        - provider_name:   模型提供商名称
        - api_type:        API Type
        """
        model_providers = self.app_conf_dict.get("model_providers")
        try:
            if model_providers is not None:
                model_providers[provider_name]["api_type"] = api_type.strip()
                self.conf_save()
        except Exception as e:
            logger.error(f"Error setting API Type for {provider_name}, error is {e}")
    
    def provider_models_add(self, provider_model: dict):
        """
        在 "模型提供商" 中添加模型

        Args:
        - provider_model:  包含 provider 和 model 的字典
        """
        # 获取指定 provider 的模型列表
        model_providers = self.app_conf_dict.get("model_providers")
        provider_models = model_providers.get(provider_model.get("provider"))
        # 整理好数据
        model_dict = {
            "model_id": provider_model.get("model_id"),
            "model_name": provider_model.get("model_name"),
            "model_feats": {
                "vision": provider_model["model_feats"].get("vision"),
                "embed": provider_model["model_feats"].get("embed"),
                "reranker": provider_model["model_feats"].get("reranker"),
            }
        }
        # 将数据整合至 self.app_conf_dict 中
        if provider_models.get("models") is not None:
            provider_models["models"].append(model_dict)
        else:
            provider_models["models"] = [model_dict]
        # 保存配置文件
        self.conf_save()

    def provider_models_edit(self, provider_model: dict):
        """
        在 "模型提供商" 中修改指定的模型
        
        Args:
        - provider_model:  包含 provider 和 model 的字典
        """
        # 获取指定 provider 的模型列表
        model_providers = self.app_conf_dict.get("model_providers")
        provider_models = model_providers.get(provider_model.get("provider"))
        # 整理好数据
        model_dict = {
            "model_id": provider_model.get("model_id"),
            "model_name": provider_model.get("model_name"),
            "model_feats": {
                "vision": provider_model["model_feats"].get("vision"),
                "embed": provider_model["model_feats"].get("embed"),
                "reranker": provider_model["model_feats"].get("reranker"),
            }
        }
        # 修改配置
        for i, model_conf in enumerate(provider_models["models"]):
            if model_conf.get("model_id") == model_dict["model_id"]:
                provider_models["models"][i] = model_dict
                break
        # 保存配置文件
        self.conf_save()

    def provider_models_del(self, provider:str, model_id:str):
        """
        删除模型服务提供商中的指定模型

        Args:
        - provider:  服务提供商
        - model_id:  模型ID
        """
        # 获取指定 provider 的模型列表
        model_providers = self.app_conf_dict.get("model_providers")
        provider_models = model_providers.get(provider)
        models = provider_models.get("models")
        # 删除指定模型
        for i in range(len(models)):
            if models[i]["model_id"] == model_id:
                del models[i]
                logger.trace(f"The specified model has been deleted. Provider: {provider}; Model ID: {model_id}.")
                break
        # 保存配置文件
        self.conf_save()


class ProfileUtils:
    """
    User 配置文件工具类
    """
    def __init__(self):
        # App 运行时的根目录
        self.app_path_root = EndPoints.runtime["app_path_root"]
        # User 配置文件路径
        self.app_user_file = os.path.abspath(os.path.join(self.app_path_root, "storage/conf/profile.yaml"))
        # User 配置字典
        self.app_user_dict = None
        # User 默认设置

        # 如果文件不存在, 则创建默认配置
        if not Path(self.app_user_file).exists():
            self.conf_init()
        # 读取配置文件
        self.app_user_dict = self.conf_read()

    def conf_init(self):
        """
        初始化 User 配置
        """
        # 初始化配置文件
        self.app_user_dict = {
            # 通用设置
            "general_settings": {
                "language": "zh_cn",
            },
            # 默认模型
            "default_models": {
                "chat_model": None,
                "agent_model": None,
                "summary_model": None, 
                "translation_model": None,
            },
            # 用户使用习惯
            "chat_view": {"lv1_view_width": 250},
            # 思考强度
            "reasoning_level": {"chat": "Auto", "agent": "Auto"},
        }
        # 创建目录并保存配置
        try:
            Path(self.app_user_file).parent.mkdir(parents=True, exist_ok=True)
            self.conf_save()
            logger.warning("Initialize default user profile.")
        except Exception as e:
            logger.error(e)

    def conf_read(self) -> Dict:
        """
        读取 YAML 文件并返回解析后的 Dict 对象

        Return
        - Dict: 解析后的配置信息
        """
        try:
            with open(self.app_user_file, "r", encoding="utf-8") as f:
                self.app_user_dict = yaml.safe_load(f)
                return self.app_user_dict
        except Exception as e:
            logger.error(e)

    def conf_save(self):
        """
        写入 YAML 配置文件
        """
        try:
            with open(self.app_user_file, "w", encoding="utf-8") as f:
                yaml.dump(
                    self.app_user_dict, 
                    f, 
                    allow_unicode=True,         # 允许输出非 ASCII 字符, 而不是将其转义为 Unicode 序列 (例如 \uXXXX)
                    default_flow_style=False,   # 强制 YAML 输出使用 "块风格(block style)", 即每个键值对占一行, 嵌套结构通过缩进表示
                    sort_keys=False,            # 字典键不自动按字母排序输出, 保持原始插入顺序
                    indent=2,                   # 设置缩进空格数为 2
                    width=float('inf')          # 限制行最大宽度, 设为 float('inf') 意味着不强制换行
                )
            logger.success("User profile saved successfully.")
        except Exception as e:
            logger.error(e)

    def chat_view_lv1_width(self):
        """
        获取聊天视图 Lv1 层级的宽度
        """
        return self.app_user_dict["chat_view"]["lv1_view_width"]
    
    def chat_view_lv1_width_set(self, width: int):
        """
        设置聊天视图 Lv1 层级的宽度
        """
        self.app_user_dict["chat_view"]["lv1_view_width"] = width
        self.conf_save()
    
    def default_model(self, default_type: str):
        """
        获取应用的默认模型

        Args:
        - default_type:  哪一个分类的默认模型: "chat_model", "agent_model", "summary_model", "translation_model"
        """
        # 如果 "default_models" 不存在, 则先创建一个空的字典
        if "default_models" not in self.app_user_dict:
            self.app_user_dict["default_models"] = {}
        # 当前的默认模型
        provider_model = self.app_user_dict["default_models"].get(default_type)
        if provider_model is None:
            return None
        # 判断该模型是否处于启用状态
        provider_name = provider_model.split("/")[0]
        providers = EndPoints.runtime["app_util_conf"].providers_dict()
        if providers is None:
            return None
        if providers.get(provider_name).get("enable"):
            return provider_model
        else:
            return None

    def default_model_set(self, default_type: str, default_model: str):
        """
        设置应用的默认模型

        Args:
        - default_type:  哪一个分类的默认模型: "agent_model", "summary_model", "translation_model"
        - default_model: 默认模型的名字: "Provider_Name/Model_Name" 
        """
        # 如果 "default_models" 不存在, 则先创建一个空的字典
        if "default_models" not in self.app_user_dict:
            self.app_user_dict["default_models"] = {}
        # 更新 & 保存数据
        self.app_user_dict["default_models"][default_type] = default_model
        self.conf_save()

    def language(self):
        """
        获取应用语言, 如果和当前运行变量不同, 则更新运行变量
        """
        # 从配置字典中读取应用语言
        lang = self.app_user_dict["general_settings"]["language"]
        # 修改运行变量
        if lang != EndPoints.runtime["app_language"]:
            EndPoints.runtime["app_language"] = lang
        return lang
    
    def language_set(self, lang: str):
        """
        设置应用语言, 同时会更新当前运行变量
        """
        try:
            # 修改配置文件
            self.app_user_dict["general_settings"]["language"] = lang
            self.conf_save()
            # 修改运行变量 & 语言字典
            EndPoints.runtime["app_language"] = lang
            EndPoints.runtime["app_util_lang"].language_load()
            logger.trace(f"App language & dict set to {lang}")
        except Exception as e:
            logger.error(e)

    def languages_list(self) -> List[str]:
        """
        获取可用的语言列表

        Return
        - List[str]: 可用的语言列表
        """
        try:
            lang_path = Path(os.path.abspath(os.path.join(self.app_path_root, "src/locales")))
            all_langs = lang_path.glob("*.yaml")
            # https://docs.python.org/zh-cn/3/library/pathlib.html#pathlib.PurePath.stem
            # 最后一个路径组件, 除去后缀
            all_langs_list = [p.stem for p in all_langs]
            return all_langs_list
        except Exception as e:
            logger.error(e)

    def reasoning_level(self) -> Dict:
        """
        获取思考强度字典
        格式为: {"reasoning_level": {"Chat": "Auto", "Agent": "Auto"}}

        Return
        - Dict: 思考强度的完整字典
        """
        try:
            reasoning_level = self.app_user_dict["reasoning_level"]
            return reasoning_level
        except Exception as e:
            logger.error(e)

    def reasoning_level_set(self, reason_lv_dict: Dict):
        """
        更新思考强度字典

        Args:
        - reason_lv_dict: 格式为 {"reasoning_level": {"Chat": "Auto", "Agent": "Auto"}}
        """
        try:
            self.app_user_dict["reasoning_level"] = reason_lv_dict
            self.conf_save()
        except Exception as e:
            logger.error(e)
