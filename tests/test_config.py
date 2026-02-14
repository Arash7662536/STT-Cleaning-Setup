"""
Tests for configuration module.
"""

import pytest
import tempfile
from pathlib import Path
import yaml

from dataset_pipeline.config import Config, ChunkingConfig, ValidationConfig


class TestConfig:
    """Tests for Config class."""

    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "input_dir": "data/input",
            "output_dir": "data/output",
        }
        config = Config.from_dict(data)

        assert config.input_dir == "data/input"
        assert config.output_dir == "data/output"
        assert config.steps.chunking is True
        assert config.steps.merging is False

    def test_config_from_yaml(self):
        """Test loading config from YAML file."""
        config_data = {
            "input_dir": "test_input",
            "output_dir": "test_output",
            "steps": {
                "chunking": True,
                "merging": True,
                "validation": False
            },
            "validation": {
                "max_workers": 4,
                "primary_port": 9000
            }
        }

        # Create temporary YAML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            config = Config.from_yaml(temp_path)

            assert config.input_dir == "test_input"
            assert config.output_dir == "test_output"
            assert config.steps.merging is True
            assert config.validation.max_workers == 4
            assert config.validation.primary_port == 9000
        finally:
            Path(temp_path).unlink()

    def test_chunking_config_defaults(self):
        """Test ChunkingConfig default values."""
        config = ChunkingConfig()

        assert config.min_duration_ms == 500
        assert config.output_subdir == "chunked"
        assert config.metadata_file == "metadata_chunked.csv"

    def test_validation_config_defaults(self):
        """Test ValidationConfig default values."""
        config = ValidationConfig()

        assert config.primary_port == 8000
        assert config.secondary_port == 8001
        assert config.max_workers == 8
        assert config.language == "fa"
