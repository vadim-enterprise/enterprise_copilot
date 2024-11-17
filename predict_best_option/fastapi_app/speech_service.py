import speech_recognition as sr
import io
import base64
import wave
from pydub import AudioSegment

class SpeechService:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8

    async def transcribe_audio(self, audio_data: str, sample_rate: int = 44100, channels: int = 1):
        try:
            # Decode base64 audio
            audio_bytes = base64.b64decode(audio_data)

            # Convert to WAV format
            with io.BytesIO() as wav_io:
                with wave.open(wav_io, 'wb') as wav_file:
                    wav_file.setnchannels(channels)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(audio_bytes)
                
                wav_io.seek(0)
                audio = AudioSegment.from_wav(wav_io)

            # Convert to mono and set sample rate
            audio = audio.set_channels(1)
            audio = audio.set_frame_rate(16000)

            # Convert to audio data for recognition
            with io.BytesIO() as audio_io:
                audio.export(audio_io, format='wav')
                audio_io.seek(0)
                
                with sr.AudioFile(audio_io) as source:
                    audio_data = self.recognizer.record(source)
                    
                    try:
                        text = self.recognizer.recognize_google(
                            audio_data,
                            language='en-US'
                        )
                        return text
                    except sr.UnknownValueError:
                        return ""
                    except sr.RequestError as e:
                        raise Exception(f"API error: {str(e)}")

        except Exception as e:
            raise Exception(f"Transcription error: {str(e)}")