"""
Tests for audio chunker.
"""

import pytest
import tempfile
from pathlib import Path

from dataset_pipeline.chunker import AudioChunker
from dataset_pipeline.config import ChunkingConfig


class TestAudioChunker:
    """Tests for AudioChunker class."""

    @pytest.fixture
    def chunker(self):
        """Create AudioChunker instance."""
        config = ChunkingConfig(min_duration_ms=500)
        return AudioChunker(config)

    def test_chunker_initialization(self, chunker):
        """Test chunker initialization."""
        assert chunker.min_duration_ms == 500
        assert chunker.config.output_subdir == "chunked"

    # Note: Full integration tests would require actual audio and SRT files
    # For production, you would add more comprehensive tests with mock data
