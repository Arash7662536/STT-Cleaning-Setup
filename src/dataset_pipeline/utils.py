"""
Utility functions for the dataset pipeline.
"""

import os
import logging
from pathlib import Path
from typing import List, Tuple


logger = logging.getLogger(__name__)


def find_audio_srt_pairs(input_dir: str, audio_ext: str = ".wav") -> List[Tuple[str, str]]:
    """
    Find all audio files and their corresponding SRT files.

    Args:
        input_dir: Directory to search for audio files
        audio_ext: Audio file extension (default: .wav)

    Returns:
        List of (audio_path, srt_path) tuples
    """
    logger.info(f"Scanning for audio files in: {input_dir}")

    input_path = Path(input_dir)
    if not input_path.exists():
        raise ValueError(f"Input directory does not exist: {input_dir}")

    audio_files = list(input_path.glob(f"*{audio_ext}"))
    pairs = []
    missing_srt = []

    for audio_path in audio_files:
        srt_path = find_srt_for_audio(audio_path)

        if srt_path:
            pairs.append((str(audio_path), str(srt_path)))
            logger.debug(f"  ✓ Found pair: {audio_path.name} + {srt_path.name}")
        else:
            missing_srt.append(str(audio_path))
            logger.warning(f"  ✗ No SRT found for: {audio_path.name}")

    logger.info(f"\nFound {len(pairs)} audio-SRT pairs")
    if missing_srt:
        logger.warning(f"Missing SRT files for {len(missing_srt)} audio files")

    return pairs


def find_srt_for_audio(audio_path: Path) -> Path | None:
    """
    Find corresponding SRT file for an audio file.

    Tries multiple naming conventions:
    - audio.srt
    - audio.fa.srt
    - audio.{lang}.srt

    Args:
        audio_path: Path to audio file

    Returns:
        Path to SRT file or None if not found
    """
    # Try different SRT naming patterns
    srt_candidates = [
        audio_path.with_suffix('.srt'),
        audio_path.with_suffix('.fa.srt'),
        audio_path.with_name(audio_path.stem + '.fa.srt'),
        audio_path.with_name(audio_path.stem + '.en.srt'),
    ]

    for candidate in srt_candidates:
        if candidate.exists():
            return candidate

    return None


def ensure_dir(directory: str) -> Path:
    """
    Ensure directory exists, create if it doesn't.

    Args:
        directory: Directory path

    Returns:
        Path object
    """
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


def validate_file_exists(filepath: str, file_type: str = "File") -> bool:
    """
    Validate that a file exists.

    Args:
        filepath: Path to file
        file_type: Type of file for error message

    Returns:
        True if exists, raises FileNotFoundError otherwise
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"{file_type} not found: {filepath}")
    return True


def format_duration(milliseconds: int) -> str:
    """
    Format duration in milliseconds to human-readable format.

    Args:
        milliseconds: Duration in milliseconds

    Returns:
        Formatted string (e.g., "1m 30s")
    """
    seconds = milliseconds // 1000
    minutes = seconds // 60
    seconds = seconds % 60

    if minutes > 0:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def safe_filename(filename: str) -> str:
    """
    Create a safe filename by removing/replacing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Safe filename
    """
    import re
    # Remove invalid characters
    safe = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    safe = safe.strip('. ')
    return safe
