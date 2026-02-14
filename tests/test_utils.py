"""
Tests for utility functions.
"""

import pytest
import tempfile
from pathlib import Path

from dataset_pipeline.utils import (
    find_srt_for_audio,
    ensure_dir,
    format_duration,
    safe_filename
)


class TestUtils:
    """Tests for utility functions."""

    def test_find_srt_for_audio(self):
        """Test finding SRT file for audio."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create test files
            audio_file = tmppath / "test_audio.wav"
            srt_file = tmppath / "test_audio.srt"

            audio_file.touch()
            srt_file.touch()

            # Test finding SRT
            found_srt = find_srt_for_audio(audio_file)
            assert found_srt == srt_file

    def test_find_srt_with_language_code(self):
        """Test finding SRT with language code."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            audio_file = tmppath / "test_audio.wav"
            srt_file = tmppath / "test_audio.fa.srt"

            audio_file.touch()
            srt_file.touch()

            found_srt = find_srt_for_audio(audio_file)
            assert found_srt == srt_file

    def test_find_srt_not_found(self):
        """Test when SRT file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            audio_file = tmppath / "test_audio.wav"
            audio_file.touch()

            found_srt = find_srt_for_audio(audio_file)
            assert found_srt is None

    def test_ensure_dir(self):
        """Test directory creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "new" / "nested" / "dir"

            result = ensure_dir(str(test_dir))

            assert test_dir.exists()
            assert test_dir.is_dir()
            assert result == test_dir

    def test_format_duration(self):
        """Test duration formatting."""
        assert format_duration(30000) == "30s"
        assert format_duration(90000) == "1m 30s"
        assert format_duration(125000) == "2m 5s"

    def test_safe_filename(self):
        """Test safe filename generation."""
        assert safe_filename("test:file.wav") == "test_file.wav"
        assert safe_filename("file<>name.wav") == "file__name.wav"
        assert safe_filename(" .test. ") == "test"
