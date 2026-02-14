# Data Directory

This directory contains input and output data for the pipeline.

## Structure

```
data/
├── input/          # Place your audio (.wav) and SRT files here
└── output/         # Pipeline outputs will be generated here
    ├── chunked/            # Step 1: Chunked audio segments
    ├── merged/             # Step 2: Merged segments (if enabled)
    ├── metadata_validated.csv  # Final validated dataset
    └── flagged_files.csv       # Files flagged for review
```

## Input Requirements

### Audio Files
- Format: WAV (recommended)
- Sample rate: Any (16kHz recommended for Whisper)
- Naming: Use descriptive names

### SRT Files
- Must correspond to audio files
- Supported naming patterns:
  - `audio.srt` (same name as audio)
  - `audio.fa.srt` (with language code)
  - `audio.en.srt` (English)

### Example

```
data/input/
├── lecture_01.wav
├── lecture_01.fa.srt
├── podcast_episode_5.wav
└── podcast_episode_5.srt
```

## Output

The pipeline generates organized outputs in subdirectories:

### Chunked Output
```
data/output/chunked/
├── lecture_01_segment_0000.wav
├── lecture_01_segment_0001.wav
├── ...
└── metadata_chunked.csv
```

### Merged Output (optional)
```
data/output/merged/
├── merged_0000.wav
├── merged_0001.wav
├── ...
└── metadata_merged.csv
```

### Validation Output
```
data/output/
├── metadata_validated.csv   # Final dataset
└── flagged_files.csv         # Needs manual review
```

## .gitignore

Audio and data files are excluded from git by default. Only `.gitkeep` files are tracked to preserve directory structure.
