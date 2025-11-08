import os
import csv
import argparse
from pathlib import Path
import pyttsx3
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import sounddevice as sd
import soundfile as sf
import time

def create_text_image(text, size=(1280, 720), bg_color=(0, 0, 128), text_color=(255, 255, 255)):
    image = Image.new('RGB', size, bg_color)
    draw = ImageDraw.Draw(image)
    margin = 60
    font_size = 48
    max_width = size[0] - 2 * margin
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        test_line = ' '.join(current_line)
        if len(test_line) * (font_size / 2) > max_width:
            lines.append(' '.join(current_line[:-1]))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    y_position = margin
    line_height = int(font_size * 1.5)
    for line in lines:
        draw.text((margin, y_position), line, fill=text_color, size=font_size)
        y_position += line_height
    
    return np.array(image)

def read_csv_with_encoding(file_path):
    encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                print(f"Trying {encoding} encoding...")
                reader = csv.reader(file)
                data = list(reader)
                if len(data) > 1:
                    print(f"Successfully read CSV with {encoding}")
                    return data[1:]
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not read CSV file with any encoding")

def create_audio_file(text, output_path):
    """Create audio file and test it immediately"""
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    engine.setProperty('volume', 0.9)
    
    # Save speech to WAV file
    print(f"Generating speech: {text[:50]}...")
    engine.save_to_file(text, str(output_path))
    engine.runAndWait()
    
    # Test audio file immediately
    try:
        data, samplerate = sf.read(str(output_path))
        print(f"Audio file created: {output_path}")
        print(f"Sample rate: {samplerate}Hz, Duration: {len(data)/samplerate:.2f}s")
        print("Testing audio playback...")
        
        # Play a short sample to test
        sd.play(data[:int(samplerate)], samplerate)
        sd.wait()
        
        return True
    except Exception as e:
        print(f"Error testing audio: {e}")
        return False

def create_qa_clip(question, answer, temp_dir, qa_index):
    q_audio_path = temp_dir / f'q_{qa_index}.wav'
    a_audio_path = temp_dir / f'a_{qa_index}.wav'
    
    # Generate and test audio files
    if not create_audio_file(question, q_audio_path) or not create_audio_file(answer, a_audio_path):
        raise RuntimeError("Failed to create or test audio files")
    
    try:
        # Create audio clips
        q_audio = AudioFileClip(str(q_audio_path))
        a_audio = AudioFileClip(str(a_audio_path))
        
        print(f"Audio clip durations - Q: {q_audio.duration:.2f}s, A: {a_audio.duration:.2f}s")
        
        # Create frames
        q_image = create_text_image(f"Q: {question}")
        a_image = create_text_image(f"A: {answer}", bg_color=(0, 64, 0))
        
        # Create video clips
        q_clip = ImageClip(q_image).set_duration(q_audio.duration)
        q_clip = q_clip.set_audio(q_audio)
        
        a_clip = ImageClip(a_image).set_duration(a_audio.duration)
        a_clip = a_clip.set_audio(a_audio)
        
        # Add pause between Q&A
        pause = ImageClip(create_text_image("", bg_color=(0, 0, 0))).set_duration(0.5)
        
        return [q_clip, pause, a_clip, pause]
    
    finally:
        # Clean up audio files
        try:
            for file in [q_audio_path, a_audio_path]:
                if file.exists():
                    file.unlink()
        except Exception as e:
            print(f"Warning: Could not delete temporary files: {e}")

def create_video(qa_pairs, output_dir='output'):
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    temp_path = Path('temp')
    temp_path.mkdir(exist_ok=True)
    
    try:
        all_clips = []
        
        for i, (question, answer) in enumerate(qa_pairs, 1):
            print(f"\nProcessing Q&A pair {i} of {len(qa_pairs)}...")
            clips = create_qa_clip(question.strip(), answer.strip(), temp_path, i)
            all_clips.extend(clips)
            print(f"Progress: {i}/{len(qa_pairs)} complete")
        
        print("\nCombining all clips...")
        final_video = concatenate_videoclips(all_clips)
        
        output_file = output_path / 'qa_video.mp4'
        print("\nWriting final video...")
        
        # Try different audio settings
        try:
            final_video.write_videofile(
                str(output_file),
                fps=24,
                codec='libx264',
                audio_codec='aac',
                audio_bitrate='192k',
                ffmpeg_params=[
                    '-strict', '-2',  # Allow experimental codecs
                    '-ac', '2',       # Force stereo
                    '-ar', '44100'    # Set audio sample rate
                ]
            )
        except Exception as first_error:
            print(f"First attempt failed: {first_error}")
            print("Trying alternate audio codec...")
            
            # Try with MP3 audio codec
            final_video.write_videofile(
                str(output_file),
                fps=24,
                codec='libx264',
                audio_codec='libmp3lame',
                audio_bitrate='192k',
                ffmpeg_params=['-ac', '2']
            )
        
        print(f"\nVideo file size: {output_file.stat().st_size / (1024*1024):.1f} MB")
        return str(output_file)
        
    finally:
        if temp_path.exists():
            try:
                for file in temp_path.glob('*.*'):
                    try:
                        file.unlink()
                    except:
                        pass
                temp_path.rmdir()
            except Exception as e:
                print(f"Warning: Could not clean up temporary directory: {e}")

def main():
    parser = argparse.ArgumentParser(description='Generate Q&A video from CSV')
    parser.add_argument('--csv', required=True, help='Path to the QA CSV file')
    
    args = parser.parse_args()
    
    try:
        # Test audio system first
        print("Testing audio system...")
        sd.play(np.zeros(44100), 44100)  # Play 1 second of silence
        sd.wait()
        print("Audio system test complete")
        
        if not os.path.exists(args.csv):
            print(f"Error: CSV file not found: {args.csv}")
            return
        
        print("\nReading CSV file...")
        qa_pairs = read_csv_with_encoding(args.csv)
        
        if not qa_pairs:
            print("No Q&A pairs found in CSV file")
            return
        
        output_path = create_video(qa_pairs)
        print(f"\nVideo created successfully: {output_path}")
        print("\nTesting final video file...")
        
        # Try to play a short segment of the video
        try:
            video = VideoFileClip(output_path)
            print(f"Video loaded successfully. Duration: {video.duration:.2f}s")
            print("Audio track present:", video.audio is not None)
            if video.audio:
                print(f"Audio duration: {video.audio.duration:.2f}s")
            video.close()
        except Exception as e:
            print(f"Error testing video: {e}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()