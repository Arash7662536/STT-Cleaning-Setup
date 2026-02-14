"""
Audio chunking module.

Handles splitting audio files based on SRT timestamps with validation.
"""

import os
import csv
import logging
from pathlib import Path
from typing import List, Tuple

import pysrt
from pydub import AudioSegment

from .config import ChunkingConfig
from .utils import ensure_dir


logger = logging.getLogger(__name__)


class AudioChunker:
    """Handles audio chunking based on SRT timestamps."""

    def __init__(self, config: ChunkingConfig):
        """
        Initialize AudioChunker.

        Args:
            config: Chunking configuration
        """
        self.config = config
        self.min_duration_ms = config.min_duration_ms

    def process_file(
        self,
        audio_path: str,
        srt_path: str,
        output_dir: str
    ) -> Tuple[List[Tuple[str, str]], int, int]:
        """
        Process a single audio + SRT file pair.

        Args:
            audio_path: Path to audio file
            srt_path: Path to SRT file
            output_dir: Output directory for chunks

        Returns:
            Tuple of (valid_chunks, total_processed, skipped_count)
        """
        try:
            logger.info(f"Chunking: {Path(audio_path).name}")

            # Load SRT and audio
            subs = pysrt.open(srt_path, encoding='utf-8')
            audio = AudioSegment.from_wav(audio_path)

            valid_chunks = []
            skipped = 0

            for i in range(len(subs)):
                current_sub = subs[i]

                # Get start time
                start_ms = current_sub.start.ordinal

                # Determine end time
                end_ms = current_sub.end.ordinal

                # Truncate if next subtitle starts before this one ends
                if i < len(subs) - 1:
                    next_start_ms = subs[i + 1].start.ordinal
                    if next_start_ms < end_ms:
                        end_ms = next_start_ms

                # Calculate duration
                duration = end_ms - start_ms

                # Validation: skip if too short
                if duration < self.min_duration_ms:
                    logger.debug(f"  Skipping segment {i}: duration {duration}ms < {self.min_duration_ms}ms")
                    skipped += 1
                    continue

                # Extract audio chunk
                chunk = audio[start_ms:end_ms]

                # Clean text
                text = current_sub.text.replace('\n', ' ').strip()

                if not text:
                    logger.debug(f"  Skipping segment {i}: empty text")
                    skipped += 1
                    continue

                # Generate filename
                base_name = Path(audio_path).stem
                chunk_filename = f"{base_name}_segment_{i:04d}.wav"
                chunk_path = os.path.join(output_dir, chunk_filename)

                # Export audio
                chunk.export(chunk_path, format="wav")
                valid_chunks.append((chunk_filename, text))

            logger.info(f"  ✓ Created {len(valid_chunks)} chunks ({skipped} skipped)")
            return valid_chunks, len(subs), skipped

        except Exception as e:
            logger.error(f"  ✗ Error chunking {Path(audio_path).name}: {e}", exc_info=True)
            return [], 0, 0

    def run(
        self,
        audio_srt_pairs: List[Tuple[str, str]],
        output_base_dir: str
    ) -> Tuple[str, str]:
        """
        Run chunking on all audio-SRT pairs.

        Args:
            audio_srt_pairs: List of (audio_path, srt_path) tuples
            output_base_dir: Base output directory

        Returns:
            Tuple of (output_dir, metadata_path)
        """
        logger.info("=" * 60)
        logger.info("STEP 1: CHUNKING AUDIO FILES")
        logger.info("=" * 60)

        output_dir = os.path.join(output_base_dir, self.config.output_subdir)
        ensure_dir(output_dir)

        all_chunks = []
        total_processed = 0
        total_skipped = 0

        for audio_path, srt_path in audio_srt_pairs:
            chunks, processed, skipped = self.process_file(audio_path, srt_path, output_dir)
            all_chunks.extend(chunks)
            total_processed += processed
            total_skipped += skipped

        # Write metadata
        metadata_path = os.path.join(output_dir, self.config.metadata_file)
        with open(metadata_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter='|')
            writer.writerow(["file_name", "text"])
            writer.writerows(all_chunks)

        logger.info(f"\n{'=' * 60}")
        logger.info("Chunking Summary:")
        logger.info(f"  Total segments processed: {total_processed}")
        logger.info(f"  Valid chunks created: {len(all_chunks)}")
        logger.info(f"  Skipped: {total_skipped}")
        logger.info(f"  Output directory: {output_dir}")
        logger.info(f"  Metadata file: {metadata_path}")
        logger.info(f"{'=' * 60}\n")

        return output_dir, metadata_path
