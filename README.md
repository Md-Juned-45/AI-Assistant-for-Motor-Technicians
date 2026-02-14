# AI Assistant for Motor Technicians (Prototype)

A voice-enabled desktop app for Indian motor repair technicians to track income, expenses, and generate reports using natural language commands.

## Features

- Natural language processing (English/Hinglish)
- Voice input/output with Google STT & TTS
- Income/expense tracking
- Real-time financial dashboard
- Business reports

## Tech Stack

- Python 3.x + CustomTkinter
- Google Gemini API
- SQLite database

## Setup

```bash
pip install customtkinter speechrecognition pyttsx3 pyaudio requests python-dotenv
```

1. Create `.env` with `GEMINI_API_KEY=your-key`
2. Run `python app.py`

## Files

- `app.py` - Main GUI application
- `database.py` - Database operations
- `llm_worker.py` - AI processing
- `.env` - API keys (not committed)

## Note

This is a prototype. Some features may be incomplete or require refinement.
