"""配置处理"""

import yaml
from pathlib import Path

from configvalidator import ConfigValidator
from mergedeep import merge
# from validators import ConfigValidator


class ConfigEngine:
    _BASE_CONFIG = Path(__file__).parent.parent / 'data' / 'default_config.yml'

    def __init__(self, custom_config=None):
        self.base_config = self._load_base_config()
        self.user_config = custom_config or {}

    def _load_base_config(self):
        with open(self._BASE_CONFIG) as f:
            return yaml.safe_load(f)

    def build(self, env_vars=None):
        merged = merge({}, self.base_config, self.user_config)
        return ConfigValidator(merged, env_vars).validate()

    @classmethod
    def from_yaml(cls, yaml_path):
        with open(yaml_path) as f:
            return cls(yaml.safe_load(f))