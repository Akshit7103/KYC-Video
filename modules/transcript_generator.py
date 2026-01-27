"""
Transcript Generator Module
Converts speech to text using Whisper for script compliance and behavior analysis
"""

import os
import json
from datetime import timedelta


class TranscriptGenerator:
    """
    Generates transcripts from audio using OpenAI Whisper.
    Supports Hindi + English (code-mixing).
    """

    def __init__(self, model_size='base'):
        """
        Initialize Whisper model

        Args:
            model_size: Whisper model size
                - 'tiny': Fastest, least accurate (~1GB VRAM)
                - 'base': Good balance (~1GB VRAM)
                - 'small': Better accuracy (~2GB VRAM)
                - 'medium': High accuracy (~5GB VRAM)
                - 'large': Best accuracy (~10GB VRAM)
        """
        self.model_size = model_size
        self.model = None

        print(f"Initializing Whisper ({model_size} model)...")
        self._load_model()

    def _load_model(self):
        """Load Whisper model"""
        try:
            import whisper
            self.model = whisper.load_model(self.model_size)
            print(f"Whisper {self.model_size} model loaded successfully")
        except ImportError:
            print("Whisper not installed. Installing...")
            import subprocess
            subprocess.check_call(['pip', 'install', 'openai-whisper'])
            import whisper
            self.model = whisper.load_model(self.model_size)
        except Exception as e:
            print(f"Error loading Whisper model: {e}")
            raise

    def transcribe(self, audio_path, language=None, task='transcribe'):
        """
        Transcribe audio to text

        Args:
            audio_path: Path to audio file (WAV recommended)
            language: Language code ('hi' for Hindi, 'en' for English, None for auto-detect)
            task: 'transcribe' or 'translate' (to English)

        Returns:
            Dictionary with full transcript and segments
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        print(f"\nTranscribing: {audio_path}")
        print(f"Language: {language or 'auto-detect'}")

        # Transcribe with Whisper
        options = {
            'task': task,
            'verbose': False
        }

        if language:
            options['language'] = language

        result = self.model.transcribe(audio_path, **options)

        # Process segments
        segments = []
        for seg in result['segments']:
            segments.append({
                'id': seg['id'],
                'start': seg['start'],
                'end': seg['end'],
                'start_formatted': str(timedelta(seconds=int(seg['start']))),
                'end_formatted': str(timedelta(seconds=int(seg['end']))),
                'text': seg['text'].strip(),
                'confidence': seg.get('avg_logprob', 0),
                'no_speech_prob': seg.get('no_speech_prob', 0)
            })

        transcript_result = {
            'audio_path': audio_path,
            'language': result.get('language', language),
            'full_text': result['text'].strip(),
            'segments': segments,
            'word_count': len(result['text'].split()),
            'duration': segments[-1]['end'] if segments else 0
        }

        print(f"Transcription complete!")
        print(f"  Language detected: {transcript_result['language']}")
        print(f"  Word count: {transcript_result['word_count']}")
        print(f"  Segments: {len(segments)}")

        return transcript_result

    def transcribe_with_timestamps(self, audio_path, language=None):
        """
        Transcribe with word-level timestamps (if supported)

        Args:
            audio_path: Path to audio file
            language: Language code

        Returns:
            Transcript with detailed timestamps
        """
        result = self.transcribe(audio_path, language)

        # Enhance segments with timing analysis
        for i, seg in enumerate(result['segments']):
            seg['duration'] = seg['end'] - seg['start']
            seg['words_per_second'] = len(seg['text'].split()) / seg['duration'] if seg['duration'] > 0 else 0

            # Flag segments with unusual characteristics
            seg['flags'] = []

            if seg['no_speech_prob'] > 0.5:
                seg['flags'].append('possibly_silence')

            if seg['words_per_second'] > 5:
                seg['flags'].append('fast_speech')

            if seg['words_per_second'] < 0.5 and seg['duration'] > 2:
                seg['flags'].append('slow_speech_or_pause')

        return result

    def identify_speakers(self, segments, agent_keywords=None, customer_keywords=None):
        """
        Attempt to identify speaker (system TTS vs customer) based on content

        NOTE: In this implementation, recordings capture both system (TTS) voice
        reading questions and customer (human) voice responding. We identify
        speakers by content patterns rather than voice characteristics.

        Args:
            segments: List of transcript segments
            agent_keywords: Keywords typically used by system (TTS)
            customer_keywords: Keywords typically used by customer

        Returns:
            Segments with speaker identification
        """
        if agent_keywords is None:
            # System (TTS) reads: questions, instructions, declarations, greetings
            agent_keywords = [
                'welcome', 'bank', 'kyc', 'video call', 'recording',
                'please confirm', 'kindly', 'show your', 'pan card',
                'aadhaar', 'blink', 'turn your', 'smile', 'thank you',
                'declaration', 'date of birth', 'full name',
                'verification', 'confirm the following', 'please hold',
                'will be used only', 'remain confidential', 'complete',
                'as per our records', 'activated after', 'choosing'
            ]

        if customer_keywords is None:
            # Customer responds with: affirmations, personal info, short answers
            customer_keywords = [
                'yes', 'no', 'my name is', 'i am', 'correct', 'confirmed',
                'okay', 'sure', 'haan', 'ji', 'nahi', 'theek hai'
            ]

        for seg in segments:
            text = seg['text'].strip()
            text_lower = text.lower()
            word_count = len(text.split())

            # Additional heuristics for system vs customer
            is_question = text.endswith('?')
            is_instruction = any(word in text_lower for word in ['please', 'kindly', 'show', 'hold', 'turn', 'blink', 'smile'])
            is_very_short = word_count <= 3  # "Yes", "No", "7th January 2003"
            is_greeting = any(word in text_lower for word in ['hello', 'welcome', 'thank you'])

            agent_score = sum(1 for kw in agent_keywords if kw in text_lower)
            customer_score = sum(1 for kw in customer_keywords if kw in text_lower)

            # Boost scores based on heuristics
            if is_question or is_instruction or is_greeting:
                agent_score += 3
            if is_very_short and not is_instruction:
                customer_score += 2

            if agent_score > customer_score:
                seg['speaker'] = 'agent'
                seg['speaker_confidence'] = agent_score / (agent_score + customer_score + 1)
            elif customer_score > agent_score:
                seg['speaker'] = 'customer'
                seg['speaker_confidence'] = customer_score / (agent_score + customer_score + 1)
            else:
                # If unclear, use length heuristic:
                # System messages are typically longer (instructions, questions)
                # Customer responses are typically shorter (answers)
                if word_count <= 10:
                    seg['speaker'] = 'customer'
                    seg['speaker_confidence'] = 0.3
                else:
                    seg['speaker'] = 'agent'
                    seg['speaker_confidence'] = 0.3

        return segments

    def extract_qa_pairs(self, segments):
        """
        Extract question-answer pairs from transcript

        HYBRID APPROACH: System (TTS) reads questions, human responds.
        - Use timing and proximity for pairing
        - Don't rely heavily on speaker identification
        - Handle both simple Q&A and declaration patterns

        Args:
            segments: Segments with speaker identification

        Returns:
            List of Q&A pairs
        """
        qa_pairs = []
        i = 0

        while i < len(segments):
            seg = segments[i]
            text = seg['text'].strip()
            text_lower = text.lower()

            # Identify questions by pattern
            is_question = (
                text.endswith('?') or
                any(qw in text_lower for qw in [
                    'are you', 'do you', 'can you',
                    'please confirm', 'kindly confirm', 'confirm if'
                ])
            )

            # Identify question-like directives (that expect a response)
            is_directive = any(phrase in text_lower for phrase in [
                'your full name', 'your date of birth', 'your name',
                'the purpose for which', 'pan number', 'kindly confirm the pan',
                'confirm the pan', 'aadhaar number'
            ])

            # Identify declaration prompt
            is_declaration_prompt = (
                'please confirm the following' in text_lower and
                i + 1 < len(segments)
            )

            # Skip if not a question/directive/prompt
            if not (is_question or is_directive or is_declaration_prompt):
                i += 1
                continue

            question = {
                'text': text,
                'start': seg['start'],
                'end': seg['end']
            }

            # SPECIAL CASE: Declaration prompt with 3 declarations following
            if is_declaration_prompt:
                declarations = []
                j = i + 1

                # Scan next 10 segments for declaration pattern
                while j < min(i + 10, len(segments)) and len(declarations) < 3:
                    check_seg = segments[j]
                    check_text = check_seg['text'].strip().lower()

                    # Check if this segment contains declaration keywords
                    has_declaration_keywords = any(phrase in check_text for phrase in [
                        'you are not', 'will not be used', 'not acting',
                        'politically exposed', 'illegal activities'
                    ])

                    # Check if next segment is a confirmation
                    if has_declaration_keywords and j + 1 < len(segments):
                        next_seg = segments[j + 1]
                        next_text = next_seg['text'].strip().lower()

                        if next_text in ['yes', 'no', 'yes.', 'no.', 'confirmed', 'correct']:
                            declarations.append({
                                'question': question,
                                'answer': {
                                    'text': f"{segments[j]['text']} → {next_text}",
                                    'start': check_seg['start'],
                                    'end': next_seg['end']
                                },
                                'answered': True,
                                'response_delay': check_seg['start'] - question['end']
                            })
                            j += 2  # Skip both declaration and confirmation
                            continue

                    j += 1

                # Add all declarations found
                if declarations:
                    qa_pairs.extend(declarations)
                    i = j
                    continue

            # NORMAL CASE: Look for immediate next segment as answer
            answer_found = False

            # Check next segment
            if i + 1 < len(segments):
                next_seg = segments[i + 1]
                next_text = next_seg['text'].strip()
                next_lower = next_text.lower()
                word_count = len(next_text.split())

                # Answer heuristics:
                # 1. Not too long (≤20 words for customer response)
                # 2. Not another question
                # 3. Not a system instruction (no "please", "kindly", "show", "hold")
                # 4. Within 5 seconds of question
                is_too_long = word_count > 20
                is_another_question = next_text.endswith('?')
                has_system_keywords = any(word in next_lower for word in [
                    'please', 'kindly', 'show your', 'hold your', 'turn your',
                    'blink your', 'smile', 'thank you for', 'activated after'
                ])
                time_gap = next_seg['start'] - seg['end']

                if not is_too_long and not is_another_question and not has_system_keywords and time_gap < 5:
                    qa_pairs.append({
                        'question': question,
                        'answer': {
                            'text': next_text,
                            'start': next_seg['start'],
                            'end': next_seg['end']
                        },
                        'answered': True,
                        'response_delay': time_gap
                    })
                    answer_found = True
                    i += 2  # Skip both question and answer
                    continue

            # No answer found
            if not answer_found:
                qa_pairs.append({
                    'question': question,
                    'answer': None,
                    'answered': False
                })
                i += 1

        return qa_pairs

    def save_transcript(self, transcript, output_path):
        """
        Save transcript to JSON file

        Args:
            transcript: Transcript dictionary
            output_path: Output file path
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(transcript, f, indent=2, ensure_ascii=False)

        print(f"Transcript saved to: {output_path}")

    def save_transcript_text(self, transcript, output_path):
        """
        Save transcript as plain text with timestamps

        Args:
            transcript: Transcript dictionary
            output_path: Output file path
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"Transcript: {transcript['audio_path']}\n")
            f.write(f"Language: {transcript['language']}\n")
            f.write(f"Duration: {transcript['duration']:.2f} seconds\n")
            f.write("=" * 60 + "\n\n")

            for seg in transcript['segments']:
                speaker = seg.get('speaker', 'Unknown')
                f.write(f"[{seg['start_formatted']} - {seg['end_formatted']}] ({speaker})\n")
                f.write(f"{seg['text']}\n\n")

        print(f"Text transcript saved to: {output_path}")


def generate_transcript(audio_path, output_dir=None, model_size='base', language=None):
    """
    Convenience function to generate transcript

    Args:
        audio_path: Path to audio file
        output_dir: Directory to save outputs (optional)
        model_size: Whisper model size
        language: Language code (None for auto-detect)

    Returns:
        Transcript dictionary
    """
    generator = TranscriptGenerator(model_size=model_size)
    transcript = generator.transcribe_with_timestamps(audio_path, language)

    # Identify speakers
    transcript['segments'] = generator.identify_speakers(transcript['segments'])

    # Extract Q&A pairs
    transcript['qa_pairs'] = generator.extract_qa_pairs(transcript['segments'])

    # Save if output_dir provided
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

        base_name = os.path.splitext(os.path.basename(audio_path))[0]

        generator.save_transcript(
            transcript,
            os.path.join(output_dir, f"{base_name}_transcript.json")
        )

        generator.save_transcript_text(
            transcript,
            os.path.join(output_dir, f"{base_name}_transcript.txt")
        )

    return transcript


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        audio_path = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else 'outputs/transcripts'

        if os.path.exists(audio_path):
            transcript = generate_transcript(audio_path, output_dir)
            print(f"\nFull transcript:\n{transcript['full_text']}")
        else:
            print(f"Audio file not found: {audio_path}")
    else:
        print("Usage: python transcript_generator.py <audio_path> [output_dir]")
