import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from .validators import validate_config_schema, ConfigValidationError

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


@dataclass
class AnalysisProfile:
    name: str = "default"
    description: str = "Default analysis profile"
    export_format: str = "csv"
    compute_hashes: bool = False
    verbosity: int = 0
    debug: int = 0
    chunk_size: int = 1000
    enable_anomaly_detection: bool = False
    file_size_threshold_mb: int = 100
    date_filter_start: Optional[str] = None
    date_filter_end: Optional[str] = None
    file_types_include: Optional[list] = None
    file_types_exclude: Optional[list] = None
    min_file_size: Optional[int] = None
    max_file_size: Optional[int] = None
    include_deleted: bool = True
    include_system_files: bool = True
    custom_fields: Optional[list] = None


class ConfigManager:
    def __init__(self):
        self.logger = logging.getLogger("analyzeMFT.config")
        self.config_dir = self._get_config_dir()
        self.profiles: Dict[str, AnalysisProfile] = {}
        self._load_default_profiles()

    def _get_config_dir(self) -> Path:
        pass

    def _load_default_profiles(self) -> None:
        pass

    def load_config_file(self, config_path: Union[str, Path]) -> Dict[str, Any]:
        pass

    def load_profile_from_config(
        self, config: Dict[str, Any], profile_name: str = "custom"
    ) -> AnalysisProfile:
        pass

    def save_profile(
        self, profile: AnalysisProfile, config_path: Union[str, Path]
    ) -> None:
        pass

    def get_profile(self, name: str) -> Optional[AnalysisProfile]:
        pass

    def list_profiles(self) -> Dict[str, str]:
        pass

    def create_sample_config(self, config_path: Union[str, Path]) -> None:
        pass


def get_default_config_paths() -> list:
    pass


def find_config_file() -> Optional[Path]:
    pass
