"""
Audio merging module.

Handles merging of audio segments in pairs.
"""

import os
import csv
import logging
from typing import List, Tuple

from pydub import AudioSegment
from tqdm import tqdm

from .config import MergingConfig
from .utils import ensure_dir


logger = logging.getLogger(__name__)


class AudioMerger:
    """Handles merging of audio segments."""

    def __init__(self, config: MergingConfig):
        """
        Initialize AudioMerger.

        Args:
            config: Merging configuration
        """
        self.config = config
        self.keep_first = config.keep_first_segment

    def run(
        self,
        input_dir: str,
        input_metadata: str,
        output_base_dir: str
    ) -> Tuple[str, str]:
        """
        Merge audio segments in pairs.

        Args:
            input_dir: Input directory with audio files
            input_metadata: Path to input metadata CSV
            output_base_dir: Base output directory

        Returns:
            Tuple of (output_dir, metadata_path)
        """
        logger.info("=" * 60)
        logger.info("STEP 2: MERGING AUDIO SEGMENTS")
        logger.info("=" * 60)

        output_dir = os.path.join(output_base_dir, self.config.output_subdir)
        ensure_dir(output_dir)

        # Read input metadata
        with open(input_metadata, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='|')
            next(reader)  # Skip header
            data = [row for row in reader if len(row) >= 2]

        if not data:
            logger.warning("No data found in metadata")
            return output_dir, None

        new_dataset = []
        new_index = 0

        # Handle first segment
        first_segment = data[0]
        remaining_segments = data[1:]

        if self.keep_first:
            logger.info(f"Keeping first segment: {first_segment[0]}")
            src_audio_path = os.path.join(input_dir, first_segment[0])
            audio = AudioSegment.from_wav(src_audio_path)

            new_filename = f"merged_{new_index:04d}.wav"
            new_path = os.path.join(output_dir, new_filename)
            audio.export(new_path, format="wav")

            new_dataset.append([new_filename, first_segment[1]])
            new_index += 1
        else:
            logger.info(f"Discarding first segment: {first_segment[0]}")

        # Merge pairs
        logger.info(f"Merging {len(remaining_segments)} segments in pairs...")

        for i in tqdm(range(0, len(remaining_segments), 2), desc="Merging"):
            item1 = remaining_segments[i]
            file1, text1 = item1[0], item1[1]

            # Check if there's a pair
            if i + 1 < len(remaining_segments):
                item2 = remaining_segments[i + 1]
                file2, text2 = item2[0], item2[1]

                # Load and merge audio
                audio1 = AudioSegment.from_wav(os.path.join(input_dir, file1))
                audio2 = AudioSegment.from_wav(os.path.join(input_dir, file2))
                combined_audio = audio1 + audio2
                combined_text = f"{text1} {text2}"
            else:
                # Odd number: keep last one as-is
                audio1 = AudioSegment.from_wav(os.path.join(input_dir, file1))
                combined_audio = audio1
                combined_text = text1

            # Save merged segment
            new_filename = f"merged_{new_index:04d}.wav"
            output_path = os.path.join(output_dir, new_filename)
            combined_audio.export(output_path, format="wav")
            new_dataset.append([new_filename, combined_text])
            new_index += 1

        # Write metadata
        metadata_path = os.path.join(output_dir, self.config.metadata_file)
        with open(metadata_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter='|')
            writer.writerow(["file_name", "text"])
            writer.writerows(new_dataset)

        logger.info(f"\n{'=' * 60}")
        logger.info("Merging Summary:")
        logger.info(f"  Input segments: {len(data)}")
        logger.info(f"  Merged files created: {len(new_dataset)}")
        logger.info(f"  Output directory: {output_dir}")
        logger.info(f"  Metadata file: {metadata_path}")
        logger.info(f"{'=' * 60}\n")

        return output_dir, metadata_path
