"""
Dataset Pipeline Package

A production-level pipeline for creating high-quality audio datasets
from audio files and their corresponding SRT transcriptions.
"""

__version__ = "1.0.0"
__author__ = "STT Project Team"

from .pipeline import DatasetPipeline
from .chunker import AudioChunker
from .merger import AudioMerger
from .validator import TranscriptionValidator

__all__ = [
    "DatasetPipeline",
    "AudioChunker",
    "AudioMerger",
    "TranscriptionValidator",
]
