"""
Command-line interface for the dataset pipeline.
"""

import sys
import argparse
import logging
from pathlib import Path

from .config import Config, setup_logging
from .pipeline import DatasetPipeline


logger = logging.getLogger(__name__)


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Production-level dataset creation pipeline for audio + SRT transcription",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default config
  %(prog)s

  # Run with custom config
  %(prog)s --config my_config.yaml

  # Override input/output directories
  %(prog)s --input data/my_audio --output data/my_output

  # Run only specific steps
  %(prog)s --skip-merging
  %(prog)s --skip-validation

For more information, see: README.md
        """
    )

    parser.add_argument(
        '--config',
        '-c',
        type=str,
        default='config/config.yaml',
        help='Path to configuration YAML file (default: config/config.yaml)'
    )

    parser.add_argument(
        '--input',
        '-i',
        type=str,
        help='Input directory (overrides config file)'
    )

    parser.add_argument(
        '--output',
        '-o',
        type=str,
        help='Output directory (overrides config file)'
    )

    parser.add_argument(
        '--skip-chunking',
        action='store_true',
        help='Skip the chunking step'
    )

    parser.add_argument(
        '--skip-merging',
        action='store_true',
        help='Skip the merging step'
    )

    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip the validation step'
    )

    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Logging level (overrides config file)'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )

    args = parser.parse_args()

    try:
        # Load configuration
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Error: Config file not found: {config_path}", file=sys.stderr)
            print(f"Hint: Copy config/config.example.yaml to config/config.yaml", file=sys.stderr)
            sys.exit(1)

        config = Config.from_yaml(str(config_path))

        # Apply command-line overrides
        if args.input:
            config.input_dir = args.input
        if args.output:
            config.output_dir = args.output

        if args.skip_chunking:
            config.steps.chunking = False
        if args.skip_merging:
            config.steps.merging = False
        if args.skip_validation:
            config.steps.validation = False

        if args.log_level:
            config.logging.level = args.log_level

        # Setup logging
        setup_logging(config.logging)

        # Run pipeline
        logger.info(f"Starting pipeline with config: {config_path}")
        pipeline = DatasetPipeline(config)
        results = pipeline.run()

        # Print summary
        print("\n" + "=" * 80)
        print("PIPELINE SUMMARY")
        print("=" * 80)
        print(f"Steps completed: {', '.join(results['steps_completed'])}")
        print(f"Output directory: {results['output_dir']}")

        if 'validated_metadata' in results:
            print(f"Validated metadata: {results['validated_metadata']}")
        if 'flagged_files' in results:
            print(f"Flagged files: {results['flagged_files']}")

        print("=" * 80)

        sys.exit(0)

    except KeyboardInterrupt:
        logger.warning("\nPipeline interrupted by user")
        sys.exit(130)

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
