# AI Video Generator

This project provides tools to generate videos with text-to-speech and visual content:

## Features
- Q&A Video Generation with voice narration
- Text-to-Speech using pyttsx3 (offline TTS engine)
- Dynamic text visualization
- Automatic audio synchronization
- Progress tracking and diagnostics

## Requirements
- Python 3.10+
- Required packages (automatically installed in virtual environment):
  - moviepy: Video editing and composition
  - pyttsx3: Text-to-speech conversion
  - Pillow: Image processing
  - numpy: Numerical operations
  - sounddevice: Audio testing and verification
  - soundfile: Audio file handling

## Getting Started
1. Ensure you have Python 3.10+ installed
2. Set up a virtual environment and install dependencies:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Create a CSV file with your Q&A pairs (two columns: questions and answers)
4. Run the script:
   ```
   python qa_video_simple.py --csv "path/to/your/qa.csv"
   ```

## Output
The script will generate:
- A video file in the `output` directory
- Each Q&A pair will be presented with:
  - Question screen with voice narration
  - Answer screen with voice narration
  - Brief pauses between segments
- Progress information and audio verification during generation