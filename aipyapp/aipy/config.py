import sys
import time
import requests # Import requests library
import os
import re
import io
import datetime
import webbrowser
from pathlib import Path

from dynaconf import Dynaconf
from rich import print
import tomli_w
import qrcode

from .. import T, __resources_path__, get_system_language
from .trustoken import TrustToken
import traceback

__PACKAGE_NAME__ = "aipyapp"

OLD_SETTINGS_FILES = [
    Path.home() / '.aipy.toml',
    Path('aipython.toml').resolve(),
    Path('.aipy.toml').resolve(),
    Path('aipy.toml').resolve()
]

CONFIG_FILE_NAME = f"{__PACKAGE_NAME__}.toml"
USER_CONFIG_FILE_NAME = "user_config.toml"
LANG = get_system_language()

def init_config_dir():
    """
    获取平台相关的配置目录，并确保目录存在
    """
    config_dir = Path.home() / f".{__PACKAGE_NAME__}"
    # 确保目录存在
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        print(T("Permission denied to create directory: {}").format(config_dir))
        raise
    except Exception as e:
        print(T("Error creating configuration directory: {}").format(config_dir, str(e)))
        raise

    return config_dir

CONFIG_DIR = init_config_dir()

def get_config_file_path(config_dir=None, file_name=CONFIG_FILE_NAME):
    """
    获取配置文件的完整路径
    :return: 配置文件的完整路径
    """
    if config_dir:
        config_dir = Path(config_dir)
    else:
        config_dir = CONFIG_DIR

    config_file_path = config_dir / file_name

    # 如果配置文件不存在，则创建一个空文件
    if not config_file_path.exists():
        try:
            config_file_path.touch()
        except Exception as e:
            print(T("Error creating configuration directory: {}").format(config_file_path))
            raise

    return config_file_path

def lowercase_keys(d):
    """递归地将字典中的所有键转换为小写"""
    if not isinstance(d, dict):
        return d
    return {k.lower(): lowercase_keys(v) for k, v in d.items()}

def is_valid_api_key(api_key):
    """
    校验是否为有效的 API Key 格式。
    API Key 格式为字母、数字、减号、下划线的组合，长度在 8 到 128 之间
    :param api_key: 待校验的 API Key 字符串
    :return: 如果格式有效返回 True，否则返回 False
    """
    pattern = r"^[A-Za-z0-9_-]{8,128}$"
    return bool(re.match(pattern, api_key))

def get_region_api(name, config):
    """ 获取特定的内部API地址, 参考default.toml
    """
    tt_api = config.get('tt_api', {})
    conf = tt_api.get(name, {})
    url = conf.get(LANG)
    return url

class ConfigManager:
    def __init__(self, config_dir=None):
        self.lang = get_system_language()
        self.config_file = get_config_file_path(config_dir)
        self.user_config_file = get_config_file_path(config_dir, USER_CONFIG_FILE_NAME)
        self.default_config = __resources_path__ / "default.toml"
        self.config = self._load_config()
        # TODO：临时API配置
        self.config.update({
            'api': {
                'tt-map': {
                    'env': {
                        'amap_api_key': ["aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","最新高德地图 API Key"],
                    },
                    'desc': "高德地图（驾车、骑行、步行、公交路线规划，周边关键字搜索，天气查询，交通态势、店铺查询, 无法确定POI分类编码时请用关键字搜索API）"
                }
            }
        })
        
        #print(self.config.to_dict())
        coordinator_url = self.get_region_api('coordinator_url')
        self.trust_token = TrustToken(coordinator_url=coordinator_url)

    def get_work_dir(self):
        if self.config.workdir:
            return Path.cwd() / self.config.workdir
        return Path.cwd()


    def _load_config(self, settings_files=[]):
        """加载配置文件
        :param settings_files: 配置文件列表
        :return: 配置对象
        """
        if not settings_files:
            # 新版本配置文件
            settings_files = [self.default_config, self.user_config_file, self.config_file]
        # 读取配置文件
        try:
            config = Dynaconf(
                settings_files=settings_files,
                envvar_prefix="AIPY",
                merge_enabled=True,
            )

            # check if it's a valid config
            assert(config.to_dict())
        except Exception as e:
            # 配置加载异常处理
            #print(T('error_loading_config'), str(e))
            # 回退到一个空配置实例，避免后续代码因 config 未定义而出错
            config = Dynaconf(
                settings_files=[],
                envvar_prefix="AIPY",
                merge_enabled=True,
                )
        return config

    def reload_config(self):
        self.config = self._load_config()
        return self.config

    def get_config(self):
        return self.config

    def update_sys_config(self, new_config):
        """更新aipyapp.toml配置文件
        :param new_config: 新配置字典, 如 {"workdir": "/path/to/workdir"}
        """
        # 加载系统配置文件
        assert(isinstance(new_config, dict))

        config = self._load_config(settings_files=[self.config_file])
        config.update(new_config)
        
        # 保存到配置文件
        header_comments = [
            f"# Configuration file for {__PACKAGE_NAME__}",
            "# Auto-generated on " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            f"# 请勿直接修改此文件，除非您了解具体配置格式，如果自定义配置，请放到{self.user_config_file}",
            f"# Please do not edit this file directly unless you understand the format. If you want to customize the configuration, please edit {self.user_config_file}",
            ""
        ]
        footer_comments = [
            "",
            "# End of configuration file"
        ]
        #print(config.to_dict())
        cfg_dict = lowercase_keys(config.to_dict())
        
        with open(self.config_file, "w", encoding="utf-8") as f:
            # 1. 写入头部注释
            f.write("\n".join(header_comments) + "\n")

            # 2. 写入 TOML 内容到临时内存文件
            temp_buffer = io.BytesIO()
            tomli_w.dump(cfg_dict, temp_buffer, multiline_strings=True)
            toml_content = temp_buffer.getvalue().decode('utf-8')

            # 3. 写入 TOML 内容
            f.write(toml_content)

            # 4. 写入尾部注释
            f.write("\n".join(footer_comments))
        return config

    def save_tt_config(self, api_key):
        base_url = self.get_region_api('llm_base_url')
        config = {
            'llm': {
                'trustoken': {
                    'api_key': api_key,
                    'type': 'trust',
                    'base_url': base_url,
                    'model': 'auto',
                    'default': True,
                    'enable': True
                }
            }
        }
        self.update_sys_config(config)
        return config


    def check_llm(self):
        """检查是否有可用的LLM配置。
        只要有可用的配置，就不强制要求trustoken配置。
        """
        llm = self.config.get("llm")
        if not llm:
            print(T("Missing 'llm' configuration."))

        llms = {}
        for name, config in self.config.get('llm', {}).items():
            if config.get("enable", True):
                llms[name] = config

        return llms

    def fetch_config(self):
        """从tt获取配置并保存到配置文件中。
        """
        self.trust_token.fetch_token(self.save_tt_config)

    def check_config(self, gui=False):
        """检查配置文件是否存在，并加载配置。
        如果配置文件不存在，则创建一个新的配置文件。
        """
        try:
            if not self.config:
                print(T("Configuration not loaded."))
                return

            if self.check_llm():
                # 有状态为 enable 的配置文件，则不需要强制要求 trustoken 配置。
                return

            # 尝试从旧版本配置迁移
            if self._migrate_config():
                # 迁移完成后重新加载配置
                self.reload_config()

            # 如果仍然没有可用的 LLM 配置，则从网络拉取
            if not self.check_llm():
                if gui: return 'TrustToken'
                self.fetch_config()
                self.reload_config()

            if not self.check_llm():
                print(T("Missing 'llm' configuration."))
                sys.exit(1)

        except Exception as e:
            traceback.print_exc()
            sys.exit(1)

    def _migrate_config(self):
        """
        Migrates configuration from old settings files (OLD_SETTINGS_FILES)
        to the new user_config.toml and potentially creates the main aipyapp.toml
        if a TrustToken configuration is found.
        """
        combined_toml_content = ""
        migrated_files = []
        backup_files = []

        for path in OLD_SETTINGS_FILES:
            if not path.exists():
                continue


            try:
                config = Dynaconf(
                    settings_files=[path],
                )
                config_dict = config.to_dict()
                assert(config_dict)

                try:
                    content = path.read_text(encoding='utf-8')
                except UnicodeDecodeError:
                    try:
                        content = path.read_text(encoding='gbk')
                    except Exception as e:
                        print(f"Error reading file {path}: {e}")
                        continue

                combined_toml_content += content + "\n\n" # Add separator

                # 文件内容、格式都正常，则准备迁移
                migrated_files.append(str(path))
                # Backup the old file
                backup_path = path.with_name(f"{path.stem}-backup{path.suffix}")
                try:
                    path.rename(backup_path)
                    backup_files.append(str(backup_path))
                except Exception as e:
                    pass

            except Exception as e:
                pass
        if not combined_toml_content:
            return

        print(T("Found old configuration files: {}\nAttempting to migrate configuration from these files...\nAfter migration, these files will be backed up to {}, please check them.").format(', '.join(migrated_files), ', '.join(backup_files)))

        # Write combined content to user_config.toml
        try:
            with open(self.user_config_file, "w", encoding="utf-8") as f:
                f.write(f"# Migrated from: {', '.join(migrated_files)}\n")
                f.write(f"# Original files backed up to: {', '.join(backup_files)}\n\n")
                f.write(combined_toml_content)
                print(T("Successfully migrated old version user configuration to {}").format(self.user_config_file))
        except Exception as e:
            return

        # Now, load the newly created user config to find TT key
        try:
            temp_config = self._load_config(settings_files=[self.user_config_file])
            llm_config = temp_config.get('llm', {})

            for section_name, section_data in llm_config.items():
                if isinstance(section_data, dict) and self._is_tt_config(section_name, section_data):
                    api_key = section_data.get('api_key', section_data.get('api-key'))
                    if api_key:
                        #print("Token found:", api_key)
                        self.save_tt_config(api_key)
                        print(T("Successfully migrated old version trustoken configuration to {}").format(self.config_file))
                        break

        except Exception as e:
            pass
        
        return True

    def _is_tt_config(self, name, config):
        """
        判断配置是否符合特定条件
        
        参数:
            name: 配置名称
            config: 配置内容字典
        
        返回: 如果符合条件返回True
        """
        # 条件1: 配置名称包含目标关键字
        if any(keyword in name.lower() for keyword in ['trustoken', 'trust']):
            return True

        base_url = config.get('base_url', config.get('base-url', '')).lower()
        # 条件2: base_url包含目标域名
        if isinstance(config, dict) and base_url:
            if 'trustoken.' in base_url:
                return True

        # 条件3: 其他特定标记
        # type == trust, 且没有base_url.
        if isinstance(config, dict) and config.get('type') == 'trust' and not base_url:
            return True
        
        return False
    
    def get_region_api(self, name):
        """ 获取特定的内部API地址, 参考default.toml
        """
        url = get_region_api(name, self.config)
        return url
