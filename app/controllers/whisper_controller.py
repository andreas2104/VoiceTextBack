import whisper

model = whisper.load_model('base')

def transcribe_audio(file_path):
    try:
        result = model.transcribe(file_path)
        return result.get("text", "")
    except Exception as e:
        print(f"Error during transcription: {e}")
        return ""