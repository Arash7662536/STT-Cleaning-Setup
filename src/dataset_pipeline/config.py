"""
Configuration management module.

Handles loading, validating, and accessing configuration from YAML files
and environment variables.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass
class ChunkingConfig:
    """Configuration for audio chunking."""
    min_duration_ms: int = 500
    output_subdir: str = "chunked"
    metadata_file: str = "metadata_chunked.csv"


@dataclass
class MergingConfig:
    """Configuration for audio merging."""
    keep_first_segment: bool = True
    output_subdir: str = "merged"
    metadata_file: str = "metadata_merged.csv"


@dataclass
class ValidationConfig:
    """Configuration for transcription validation."""
    primary_port: int = 8000
    secondary_port: int = 8001
    primary_model: str = "openai/whisper-large-v3"
    secondary_model: str = "openai/whisper-large-v3-turbo"
    boundary_window: int = 2
    language: str = "fa"
    max_workers: int = 8
    output_metadata: str = "metadata_validated.csv"
    flagged_file: str = "flagged_files.csv"


@dataclass
class StepsConfig:
    """Configuration for pipeline steps."""
    chunking: bool = True
    merging: bool = False
    validation: bool = True


@dataclass
class LoggingConfig:
    """Configuration for logging."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = "pipeline.log"
    console: bool = True


@dataclass
class Config:
    """Main configuration class."""
    input_dir: str
    output_dir: str
    steps: StepsConfig = field(default_factory=StepsConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    merging: MergingConfig = field(default_factory=MergingConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create Config from dictionary."""
        return cls(
            input_dir=data.get("input_dir", "data/input"),
            output_dir=data.get("output_dir", "data/output"),
            steps=StepsConfig(**data.get("steps", {})),
            chunking=ChunkingConfig(**data.get("chunking", {})),
            merging=MergingConfig(**data.get("merging", {})),
            validation=ValidationConfig(**data.get("validation", {})),
            logging=LoggingConfig(**data.get("logging", {})),
        )

    @classmethod
    def from_yaml(cls, config_path: str) -> "Config":
        """Load configuration from YAML file."""
        try:
            config_path = Path(config_path)
            if not config_path.exists():
                raise FileNotFoundError(f"Config file not found: {config_path}")

            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            # Override with environment variables if present
            data = cls._apply_env_overrides(data)

            logger.info(f"Configuration loaded from {config_path}")
            return cls.from_dict(data)

        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise

    @staticmethod
    def _apply_env_overrides(config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to config."""
        # Example: DATASET_INPUT_DIR, DATASET_OUTPUT_DIR, etc.
        env_mappings = {
            "DATASET_INPUT_DIR": ("input_dir",),
            "DATASET_OUTPUT_DIR": ("output_dir",),
            "DATASET_MAX_WORKERS": ("validation", "max_workers"),
            "WHISPER_PRIMARY_PORT": ("validation", "primary_port"),
            "WHISPER_SECONDARY_PORT": ("validation", "secondary_port"),
        }

        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Navigate nested dict
                current = config_data
                for key in config_path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]

                # Convert to appropriate type
                last_key = config_path[-1]
                if last_key in ["max_workers", "primary_port", "secondary_port"]:
                    value = int(value)
                current[last_key] = value
                logger.info(f"Config override from {env_var}: {'.'.join(config_path)} = {value}")

        return config_data


def setup_logging(config: LoggingConfig, log_dir: str = "logs") -> None:
    """Setup logging based on configuration."""
    level = getattr(logging, config.level.upper(), logging.INFO)

    # Create logs directory
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    handlers = []

    # Console handler
    if config.console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(config.format))
        handlers.append(console_handler)

    # File handler
    if config.file:
        log_file = Path(log_dir) / config.file
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(config.format))
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=level,
        format=config.format,
        handlers=handlers,
        force=True  # Override any existing configuration
    )

    logger.info(f"Logging configured: level={config.level}, file={config.file}")
