"""
Production-level dataset creation pipeline for audio + SRT transcription.

This pipeline:
1. Chunks audio files based on SRT timestamps
2. Optionally merges audio segments
3. Validates transcriptions using dual Whisper models via vllm

Author: Generated for STT Project
"""

import os
import csv
import re
import logging
import yaml
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import concurrent.futures

import pysrt
from pydub import AudioSegment
from openai import OpenAI
from hazm import Normalizer
from tqdm import tqdm


class ConfigLoader:
    """Loads and validates configuration from YAML file."""

    @staticmethod
    def load(config_path: str = "config.yaml") -> dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logging.info(f"Configuration loaded from {config_path}")
            return config
        except Exception as e:
            logging.error(f"Failed to load config: {e}")
            raise


class Logger:
    """Configures logging for the pipeline."""

    @staticmethod
    def setup(config: dict):
        """Setup logging based on configuration."""
        log_config = config.get('logging', {})
        level = getattr(logging, log_config.get('level', 'INFO'))
        format_str = log_config.get('format', '%(asctime)s - %(levelname)s - %(message)s')

        handlers = []

        # Console handler
        if log_config.get('console', True):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(format_str))
            handlers.append(console_handler)

        # File handler
        if 'file' in log_config:
            file_handler = logging.FileHandler(log_config['file'], encoding='utf-8')
            file_handler.setFormatter(logging.Formatter(format_str))
            handlers.append(file_handler)

        logging.basicConfig(
            level=level,
            format=format_str,
            handlers=handlers
        )


class AudioChunker:
    """Handles audio chunking based on SRT timestamps."""

    def __init__(self, config: dict):
        self.config = config
        self.chunking_config = config['chunking']
        self.min_duration_ms = self.chunking_config['min_duration_ms']

    def process_file(self, audio_path: str, srt_path: str, output_dir: str) -> Tuple[List[Tuple], int, int]:
        """
        Process a single audio + SRT file pair.

        Returns:
            Tuple of (valid_chunks, total_processed, skipped_count)
        """
        try:
            logging.info(f"Chunking: {Path(audio_path).name}")

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
                    skipped += 1
                    continue

                # Extract audio chunk
                chunk = audio[start_ms:end_ms]

                # Clean text
                text = current_sub.text.replace('\n', ' ').strip()

                if not text:
                    skipped += 1
                    continue

                # Generate filename
                base_name = Path(audio_path).stem
                chunk_filename = f"{base_name}_segment_{i:04d}.wav"
                chunk_path = os.path.join(output_dir, chunk_filename)

                # Export audio
                chunk.export(chunk_path, format="wav")
                valid_chunks.append((chunk_filename, text))

            logging.info(f"  ✓ Created {len(valid_chunks)} chunks ({skipped} skipped)")
            return valid_chunks, len(subs), skipped

        except Exception as e:
            logging.error(f"  ✗ Error chunking {Path(audio_path).name}: {e}")
            return [], 0, 0

    def run(self, audio_srt_pairs: List[Tuple[str, str]], output_base_dir: str) -> str:
        """
        Run chunking on all audio-SRT pairs.

        Returns:
            Path to metadata file
        """
        logging.info("=" * 60)
        logging.info("STEP 1: CHUNKING AUDIO FILES")
        logging.info("=" * 60)

        output_dir = os.path.join(output_base_dir, self.chunking_config['output_subdir'])
        os.makedirs(output_dir, exist_ok=True)

        all_chunks = []
        total_processed = 0
        total_skipped = 0

        for audio_path, srt_path in audio_srt_pairs:
            chunks, processed, skipped = self.process_file(audio_path, srt_path, output_dir)
            all_chunks.extend(chunks)
            total_processed += processed
            total_skipped += skipped

        # Write metadata
        metadata_path = os.path.join(output_dir, self.chunking_config['metadata_file'])
        with open(metadata_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter='|')
            writer.writerow(["file_name", "text"])
            writer.writerows(all_chunks)

        logging.info(f"\nChunking Summary:")
        logging.info(f"  Total segments processed: {total_processed}")
        logging.info(f"  Valid chunks created: {len(all_chunks)}")
        logging.info(f"  Skipped: {total_skipped}")
        logging.info(f"  Output: {output_dir}")
        logging.info(f"  Metadata: {metadata_path}")

        return output_dir, metadata_path


class AudioMerger:
    """Handles merging of audio segments."""

    def __init__(self, config: dict):
        self.config = config
        self.merging_config = config['merging']
        self.keep_first = self.merging_config['keep_first_segment']

    def run(self, input_dir: str, input_metadata: str, output_base_dir: str) -> Tuple[str, str]:
        """
        Merge audio segments in pairs.

        Returns:
            Tuple of (output_dir, metadata_path)
        """
        logging.info("=" * 60)
        logging.info("STEP 2: MERGING AUDIO SEGMENTS")
        logging.info("=" * 60)

        output_dir = os.path.join(output_base_dir, self.merging_config['output_subdir'])
        os.makedirs(output_dir, exist_ok=True)

        # Read input metadata
        with open(input_metadata, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='|')
            next(reader)  # Skip header
            data = [row for row in reader if len(row) >= 2]

        if not data:
            logging.warning("No data found in metadata")
            return output_dir, None

        new_dataset = []
        new_index = 0

        # Handle first segment
        first_segment = data[0]
        remaining_segments = data[1:]

        if self.keep_first:
            logging.info(f"Keeping first segment: {first_segment[0]}")
            src_audio_path = os.path.join(input_dir, first_segment[0])
            audio = AudioSegment.from_wav(src_audio_path)

            new_filename = f"merged_{new_index:04d}.wav"
            new_path = os.path.join(output_dir, new_filename)
            audio.export(new_path, format="wav")

            new_dataset.append([new_filename, first_segment[1]])
            new_index += 1
        else:
            logging.info(f"Discarding first segment: {first_segment[0]}")

        # Merge pairs
        logging.info(f"Merging {len(remaining_segments)} segments in pairs...")

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
        metadata_path = os.path.join(output_dir, self.merging_config['metadata_file'])
        with open(metadata_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter='|')
            writer.writerow(["file_name", "text"])
            writer.writerows(new_dataset)

        logging.info(f"\nMerging Summary:")
        logging.info(f"  Input segments: {len(data)}")
        logging.info(f"  Merged files created: {len(new_dataset)}")
        logging.info(f"  Output: {output_dir}")
        logging.info(f"  Metadata: {metadata_path}")

        return output_dir, metadata_path


class TranscriptionValidator:
    """Validates transcriptions using dual Whisper models."""

    def __init__(self, config: dict):
        self.config = config
        self.val_config = config['validation']

        # Initialize API clients
        logging.info("Initializing Whisper API clients...")

        primary_port = self.val_config['primary_port']
        secondary_port = self.val_config['secondary_port']

        self.client_primary = OpenAI(
            base_url=f"http://localhost:{primary_port}/v1",
            api_key="EMPTY"
        )
        self.model_primary = self.val_config['primary_model']

        self.client_secondary = OpenAI(
            base_url=f"http://localhost:{secondary_port}/v1",
            api_key="EMPTY"
        )
        self.model_secondary = self.val_config['secondary_model']

        # Text normalizer
        self.normalizer = Normalizer()

        self.boundary_window = self.val_config['boundary_window']
        self.language = self.val_config['language']
        self.max_workers = self.val_config['max_workers']

        logging.info(f"  Primary: {self.model_primary} on port {primary_port}")
        logging.info(f"  Secondary: {self.model_secondary} on port {secondary_port}")

    def normalize_text(self, text: str) -> str:
        """Normalize Persian/Farsi text."""
        if not text:
            return ""
        text = str(text)
        text = self.normalizer.normalize(text)
        # Keep Persian chars, digits, and spaces
        text = re.sub(r'[^\w\s\u0600-\u06FF]+', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def get_boundaries(self, text: str) -> Tuple[List[str], List[str]]:
        """Get first N and last N words from text."""
        words = text.split()
        if len(words) <= self.boundary_window * 2:
            return words, words
        return words[:self.boundary_window], words[-self.boundary_window:]

    def transcribe(self, client: OpenAI, model_name: str, audio_path: str) -> Optional[str]:
        """Transcribe audio using Whisper model."""
        try:
            with open(audio_path, "rb") as f:
                response = client.audio.transcriptions.create(
                    model=model_name,
                    file=f,
                    language=self.language
                )
            return self.normalize_text(response.text)
        except Exception as e:
            logging.error(f"Transcription error for {Path(audio_path).name}: {e}")
            return None

    def process_single_row(self, row: List[str], dataset_dir: str) -> Optional[Tuple[str, List]]:
        """
        Process a single audio file for validation.

        Returns:
            Tuple of (status, result_list) or None
        """
        if len(row) < 2:
            return None

        filename = row[0]
        original_raw_text = row[1]
        filepath = os.path.join(dataset_dir, filename)

        if not os.path.exists(filepath):
            logging.warning(f"File not found: {filepath}")
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

    def run(self, input_dir: str, input_metadata: str, output_base_dir: str) -> Tuple[str, str]:
        """
        Run validation on all audio files.

        Returns:
            Tuple of (validated_metadata_path, flagged_files_path)
        """
        logging.info("=" * 60)
        logging.info("STEP 3: VALIDATING TRANSCRIPTIONS")
        logging.info("=" * 60)

        # Read input metadata
        with open(input_metadata, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='|')
            next(reader)  # Skip header
            rows = list(reader)

        valid_data = []
        flagged_data = []

        logging.info(f"Processing {len(rows)} files with {self.max_workers} workers...")

        # Parallel processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.process_single_row, row, input_dir) for row in rows]
            results = []
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(rows), desc="Validating"):
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
        validated_path = os.path.join(output_base_dir, self.val_config['output_metadata'])
        with open(validated_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter='|')
            writer.writerow(["file_name", "text"])
            writer.writerows(valid_data)

        # Save flagged files
        flagged_path = os.path.join(output_base_dir, self.val_config['flagged_file'])
        with open(flagged_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter='|')
            writer.writerow(["file_name", "srt", "primary_v3", "secondary_turbo", "reason"])
            writer.writerows(flagged_data)

        logging.info(f"\nValidation Summary:")
        logging.info(f"  Total files: {len(rows)}")
        logging.info(f"  Valid: {len(valid_data)}")
        logging.info(f"  Flagged: {len(flagged_data)}")
        logging.info(f"  Validated metadata: {validated_path}")
        logging.info(f"  Flagged files: {flagged_path}")

        return validated_path, flagged_path


class DatasetPipeline:
    """Main pipeline orchestrator."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = ConfigLoader.load(config_path)
        Logger.setup(self.config)

        self.input_dir = self.config['input_dir']
        self.output_dir = self.config['output_dir']

        # Initialize processors
        if self.config['steps']['chunking']:
            self.chunker = AudioChunker(self.config)
        if self.config['steps']['merging']:
            self.merger = AudioMerger(self.config)
        if self.config['steps']['validation']:
            self.validator = TranscriptionValidator(self.config)

    def find_audio_srt_pairs(self) -> List[Tuple[str, str]]:
        """
        Find all WAV files and their corresponding SRT files.

        Returns:
            List of (audio_path, srt_path) tuples
        """
        logging.info(f"Scanning for audio files in: {self.input_dir}")

        audio_files = list(Path(self.input_dir).glob("*.wav"))
        pairs = []
        missing_srt = []

        for audio_path in audio_files:
            # Look for corresponding SRT file
            srt_candidates = [
                audio_path.with_suffix('.srt'),  # Same name with .srt
                audio_path.with_suffix('.fa.srt'),  # With language code
                audio_path.with_name(audio_path.stem + '.fa.srt'),
            ]

            srt_path = None
            for candidate in srt_candidates:
                if candidate.exists():
                    srt_path = candidate
                    break

            if srt_path:
                pairs.append((str(audio_path), str(srt_path)))
                logging.debug(f"  ✓ Found pair: {audio_path.name} + {srt_path.name}")
            else:
                missing_srt.append(str(audio_path))
                logging.warning(f"  ✗ No SRT found for: {audio_path.name}")

        logging.info(f"\nFound {len(pairs)} audio-SRT pairs")
        if missing_srt:
            logging.warning(f"Missing SRT files for {len(missing_srt)} audio files")

        return pairs

    def run(self):
        """Run the complete pipeline."""
        logging.info("=" * 60)
        logging.info("DATASET CREATION PIPELINE STARTED")
        logging.info("=" * 60)
        logging.info(f"Input directory: {self.input_dir}")
        logging.info(f"Output directory: {self.output_dir}")
        logging.info(f"Steps enabled: {[k for k, v in self.config['steps'].items() if v]}")

        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)

        # Find audio-SRT pairs
        pairs = self.find_audio_srt_pairs()

        if not pairs:
            logging.error("No audio-SRT pairs found. Exiting.")
            return

        # Step 1: Chunking
        if self.config['steps']['chunking']:
            current_dir, current_metadata = self.chunker.run(pairs, self.output_dir)
        else:
            logging.info("Chunking step disabled, skipping...")
            return

        # Step 2: Merging (optional)
        if self.config['steps']['merging']:
            current_dir, current_metadata = self.merger.run(current_dir, current_metadata, self.output_dir)
        else:
            logging.info("Merging step disabled, skipping...")

        # Step 3: Validation
        if self.config['steps']['validation']:
            validated_path, flagged_path = self.validator.run(current_dir, current_metadata, self.output_dir)
        else:
            logging.info("Validation step disabled, skipping...")

        logging.info("=" * 60)
        logging.info("PIPELINE COMPLETED SUCCESSFULLY")
        logging.info("=" * 60)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Production-level dataset creation pipeline for audio + SRT transcription"
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to configuration YAML file (default: config.yaml)'
    )

    args = parser.parse_args()

    try:
        pipeline = DatasetPipeline(config_path=args.config)
        pipeline.run()
    except Exception as e:
        logging.error(f"Pipeline failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
