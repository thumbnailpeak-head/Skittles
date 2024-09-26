from fastapi import APIRouter, WebSocket
import speech_recognition as sr
import pyttsx3
import io
from pydub import AudioSegment
from gtts import gTTS
from src.llm.chatgpt import chat_with_gpt4


router = APIRouter()

# Initialize the Text-to-Speech engine
tts_engine = pyttsx3.init()


# Function to convert text to speech
def text_to_speech(text):
    tts = gTTS(text)
    audio_io = io.BytesIO()
    tts.write_to_fp(audio_io)
    audio_io.seek(0)  # Move the pointer to the beginning of the file-like object
    return audio_io


# Function to convert speech to text
def speech_to_text(audio_data):
    recognizer = sr.Recognizer()
    try:
        text = recognizer.recognize_google(audio_data)
        return text
    except sr.UnknownValueError:
        return "Sorry, I did not understand that."
    except sr.RequestError as e:
        return f"Speech recognition error: {e}"


@router.websocket("/chat")
async def voice_bot(websocket: WebSocket):
    await websocket.accept()

    while True:
        try:
            # Receive audio bytes from the WebSocket
            audio_bytes = await websocket.receive_bytes()

            # Convert the received bytes into a file-like object
            audio_file = io.BytesIO(audio_bytes)

            # Convert the audio to WAV format using pydub (this ensures it's PCM WAV)
            audio = AudioSegment.from_file(audio_file)
            wav_audio = io.BytesIO()
            audio.export(wav_audio, format="wav")
            wav_audio.seek(0)

            # Use SpeechRecognition to process the audio file
            recognizer = sr.Recognizer()
            with sr.AudioFile(wav_audio) as source:
                audio = recognizer.record(source)  # Load the entire file into the recognizer
                text = speech_to_text(audio)

            response = chat_with_gpt4(f"you are a voice bot, reply to the voice {text}")
            # Send the transcription result back to the client
            await websocket.send_text(f"You said: {response}")
            # Convert the text response to speech
            tts_audio = text_to_speech(f"You said: {response}")

            # Send the audio data back to the client
            await websocket.send_bytes(tts_audio.read())
        except Exception as e:
            await websocket.send_text(f"Error: {str(e)}")
            await websocket.close()
            break


