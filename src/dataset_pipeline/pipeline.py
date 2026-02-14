"""
Main pipeline orchestrator.

Coordinates all steps of the dataset creation pipeline.
"""

import logging
from pathlib import Path
from typing import Optional

from .config import Config
from .chunker import AudioChunker
from .merger import AudioMerger
from .validator import TranscriptionValidator
from .utils import find_audio_srt_pairs, ensure_dir


logger = logging.getLogger(__name__)


class DatasetPipeline:
    """Main pipeline orchestrator."""

    def __init__(self, config: Config):
        """
        Initialize DatasetPipeline.

        Args:
            config: Pipeline configuration
        """
        self.config = config

        # Validate input directory
        if not Path(config.input_dir).exists():
            raise ValueError(f"Input directory does not exist: {config.input_dir}")

        # Create output directory
        ensure_dir(config.output_dir)

        # Initialize processors based on enabled steps
        self.chunker: Optional[AudioChunker] = None
        self.merger: Optional[AudioMerger] = None
        self.validator: Optional[TranscriptionValidator] = None

        if config.steps.chunking:
            self.chunker = AudioChunker(config.chunking)

        if config.steps.merging:
            self.merger = AudioMerger(config.merging)

        if config.steps.validation:
            self.validator = TranscriptionValidator(config.validation)

    def run(self) -> dict:
        """
        Run the complete pipeline.

        Returns:
            Dictionary with pipeline results and statistics
        """
        logger.info("=" * 80)
        logger.info("DATASET CREATION PIPELINE STARTED")
        logger.info("=" * 80)
        logger.info(f"Input directory: {self.config.input_dir}")
        logger.info(f"Output directory: {self.config.output_dir}")
        logger.info(f"Steps enabled: {[k for k, v in vars(self.config.steps).items() if v]}")
        logger.info("=" * 80)

        results = {
            "input_dir": self.config.input_dir,
            "output_dir": self.config.output_dir,
            "steps_completed": [],
            "stats": {}
        }

        # Find audio-SRT pairs
        logger.info("\n" + "=" * 80)
        logger.info("FINDING AUDIO FILES")
        logger.info("=" * 80)

        pairs = find_audio_srt_pairs(self.config.input_dir)

        if not pairs:
            logger.error("No audio-SRT pairs found. Exiting.")
            return results

        results["stats"]["audio_files_found"] = len(pairs)

        # Step 1: Chunking
        current_dir = None
        current_metadata = None

        if self.config.steps.chunking and self.chunker:
            current_dir, current_metadata = self.chunker.run(pairs, self.config.output_dir)
            results["steps_completed"].append("chunking")
            results["chunking_output_dir"] = current_dir
            results["chunking_metadata"] = current_metadata
        else:
            logger.info("\n" + "=" * 80)
            logger.info("Chunking step disabled, skipping...")
            logger.info("=" * 80)
            return results

        # Step 2: Merging (optional)
        if self.config.steps.merging and self.merger:
            current_dir, current_metadata = self.merger.run(
                current_dir,
                current_metadata,
                self.config.output_dir
            )
            results["steps_completed"].append("merging")
            results["merging_output_dir"] = current_dir
            results["merging_metadata"] = current_metadata
        else:
            logger.info("\n" + "=" * 80)
            logger.info("Merging step disabled, skipping...")
            logger.info("=" * 80)

        # Step 3: Validation
        if self.config.steps.validation and self.validator:
            validated_path, flagged_path = self.validator.run(
                current_dir,
                current_metadata,
                self.config.output_dir
            )
            results["steps_completed"].append("validation")
            results["validated_metadata"] = validated_path
            results["flagged_files"] = flagged_path
        else:
            logger.info("\n" + "=" * 80)
            logger.info("Validation step disabled, skipping...")
            logger.info("=" * 80)

        # Final summary
        logger.info("\n" + "=" * 80)
        logger.info("PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        logger.info(f"Steps completed: {', '.join(results['steps_completed'])}")
        logger.info(f"Output directory: {self.config.output_dir}")
        logger.info("=" * 80 + "\n")

        return results
