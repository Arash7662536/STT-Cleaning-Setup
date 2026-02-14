"""
Transcription validation module.

Validates transcriptions using dual Whisper models via vllm.
"""

import os
import csv
import re
import logging
from pathlib import Path
from typing import List, Tuple, Optional
import concurrent.futures

from openai import OpenAI
from hazm import Normalizer
from tqdm import tqdm

from .config import ValidationConfig


logger = logging.getLogger(__name__)


class TranscriptionValidator:
    """Validates transcriptions using dual Whisper models."""

    def __init__(self, config: ValidationConfig):
        """
        Initialize TranscriptionValidator.

        Args:
            config: Validation configuration
        """
        self.config = config

        # Initialize API clients
        logger.info("Initializing Whisper API clients...")

        self.client_primary = OpenAI(
            base_url=f"http://localhost:{config.primary_port}/v1",
            api_key="EMPTY",
            timeout=60.0
        )
        self.model_primary = config.primary_model

        self.client_secondary = OpenAI(
            base_url=f"http://localhost:{config.secondary_port}/v1",
            api_key="EMPTY",
            timeout=60.0
        )
        self.model_secondary = config.secondary_model

        # Text normalizer
        self.normalizer = Normalizer()

        self.boundary_window = config.boundary_window
        self.language = config.language
        self.max_workers = config.max_workers

        logger.info(f"  Primary: {self.model_primary} on port {config.primary_port}")
        logger.info(f"  Secondary: {self.model_secondary} on port {config.secondary_port}")

    def normalize_text(self, text: str) -> str:
        """
        Normalize Persian/Farsi text.

        Args:
            text: Input text

        Returns:
            Normalized text
        """
        if not text:
            return ""
        text = str(text)
        text = self.normalizer.normalize(text)
        # Keep Persian chars, digits, and spaces
        text = re.sub(r'[^\w\s\u0600-\u06FF]+', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def get_boundaries(self, text: str) -> Tuple[List[str], List[str]]:
        """
        Get first N and last N words from text.

        Args:
            text: Input text

        Returns:
            Tuple of (first_words, last_words)
        """
        words = text.split()
        if len(words) <= self.boundary_window * 2:
            return words, words
        return words[:self.boundary_window], words[-self.boundary_window:]

    def transcribe(
        self,
        client: OpenAI,
        model_name: str,
        audio_path: str
    ) -> Optional[str]:
        """
        Transcribe audio using Whisper model.

        Args:
            client: OpenAI client
            model_name: Model name
            audio_path: Path to audio file

        Returns:
            Transcribed text or None on error
        """
        try:
            with open(audio_path, "rb") as f:
                response = client.audio.transcriptions.create(
                    model=model_name,
                    file=f,
                    language=self.language
                )
            return self.normalize_text(response.text)
        except Exception as e:
            logger.error(f"Transcription error for {Path(audio_path).name}: {e}")
            return None

    def process_single_row(
        self,
        row: List[str],
        dataset_dir: str
    ) -> Optional[Tuple[str, List]]:
        """
        Process a single audio file for validation.

        Args:
            row: CSV row [filename, text]
            dataset_dir: Directory containing audio files

        Returns:
            Tuple of (status, result_list) or None
        """
        if len(row) < 2:
            return None

        filename = row[0]
        original_raw_text = row[1]
        filepath = os.path.join(dataset_dir, filename)

        if not os.path.exists(filepath):
            logger.warning(f"File not found: {filepath}")
            return None

        # Normalize SRT text
        original_srt = self.normalize_text(original_raw_text)

        # Step 1: Transcribe with primary model (Large V3)
        pred_primary = self.transcribe(self.client_primary, self.model_primary, filepath)

        if pred_primary is None:
            return ("FLAG", [filename, original_raw_text, "Error", "Error", "Primary Model Failed"])

        # Check boundary match
        srt_start, srt_end = self.get_boundaries(original_srt)
        prim_start, prim_end = self.get_boundaries(pred_primary)

        match_start = (srt_start == prim_start)
        match_end = (srt_end == prim_end)

        # Perfect match: keep original
        if match_start and match_end:
            return ("VALID", [filename, original_raw_text])

        # Step 2: Disagreement - ask secondary model (Turbo)
        pred_secondary = self.transcribe(self.client_secondary, self.model_secondary, filepath)

        if pred_secondary is None:
            return ("FLAG", [filename, original_raw_text, pred_primary, "Error", "Secondary Model Failed"])

        sec_start, sec_end = self.get_boundaries(pred_secondary)

        # Check model consensus
        models_agree_start = (prim_start == sec_start)
        models_agree_end = (prim_end == sec_end)

        # Consensus logic
        consensus = True
        if not match_start and not models_agree_start:
            consensus = False
        if not match_end and not models_agree_end:
            consensus = False

        if consensus:
            # Models agree: trust primary model (higher accuracy)
            return ("VALID", [filename, pred_primary])
        else:
            # Disagreement: flag for manual review
            return ("FLAG", [filename, original_raw_text, pred_primary, pred_secondary, "Model Disagreement"])

    def run(
        self,
        input_dir: str,
        input_metadata: str,
        output_base_dir: str
    ) -> Tuple[str, str]:
        """
        Run validation on all audio files.

        Args:
            input_dir: Directory containing audio files
            input_metadata: Path to input metadata CSV
            output_base_dir: Base output directory

        Returns:
            Tuple of (validated_metadata_path, flagged_files_path)
        """
        logger.info("=" * 60)
        logger.info("STEP 3: VALIDATING TRANSCRIPTIONS")
        logger.info("=" * 60)

        # Read input metadata
        with open(input_metadata, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='|')
            next(reader)  # Skip header
            rows = list(reader)

        valid_data = []
        flagged_data = []

        logger.info(f"Processing {len(rows)} files with {self.max_workers} workers...")

        # Parallel processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(self.process_single_row, row, input_dir)
                for row in rows
            ]
            results = []
            for future in tqdm(
                concurrent.futures.as_completed(futures),
                total=len(rows),
                desc="Validating"
            ):
                results.append(future.result())

        # Sort results
        for res in results:
            if res is None:
                continue
            status, data = res
            if status == "VALID":
                valid_data.append(data)
            else:
                flagged_data.append(data)

        # Save validated metadata
        validated_path = os.path.join(output_base_dir, self.config.output_metadata)
        with open(validated_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter='|')
            writer.writerow(["file_name", "text"])
            writer.writerows(valid_data)

        # Save flagged files
        flagged_path = os.path.join(output_base_dir, self.config.flagged_file)
        with open(flagged_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter='|')
            writer.writerow(["file_name", "srt", "primary_v3", "secondary_turbo", "reason"])
            writer.writerows(flagged_data)

        logger.info(f"\n{'=' * 60}")
        logger.info("Validation Summary:")
        logger.info(f"  Total files: {len(rows)}")
        logger.info(f"  Valid: {len(valid_data)}")
        logger.info(f"  Flagged: {len(flagged_data)}")
        logger.info(f"  Success rate: {len(valid_data)/len(rows)*100:.1f}%")
        logger.info(f"  Validated metadata: {validated_path}")
        logger.info(f"  Flagged files: {flagged_path}")
        logger.info(f"{'=' * 60}\n")

        return validated_path, flagged_path
