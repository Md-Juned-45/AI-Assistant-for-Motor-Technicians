# 🔧 AI Assistant for Motor Technicians

An intelligent voice-enabled desktop application designed specifically for Indian motor repair technicians to manage their business transactions, track income/expenses, and generate reports using natural language commands.

## 📋 Overview

This application combines modern AI technology (Google Gemini) with voice recognition to help motor technicians efficiently manage their daily business operations without complex data entry. Simply speak or type commands in natural language (English or Hinglish), and the AI assistant handles the rest.

## ✨ Key Features

### 💬 Natural Language Processing
- Understands casual English and Hindi-English (Hinglish) commands
- Powered by Google Gemini 1.5 Flash API for intelligent command parsing
- Context-aware conversations with memory of recent interactions

### 🎤 Voice Input & Output
- **Voice Recognition**: Google Speech-to-Text API for accurate Indian English recognition
- **Text-to-Speech**: pyttsx3 for voice responses
- Hands-free operation for busy technicians

### 💰 Transaction Management
- **Income Tracking**: Record payments from customers
  - Example: "Income 500 from Ram for motor repair"
- **Expense Tracking**: Log business expenses
  - Example: "Spent 50 on copper wire"
- **Edit Transactions**: Modify the last recorded transaction
- **Delete Records**: Remove today's transactions if needed

### 📊 Real-Time Dashboard
- Live display of today's financial summary:
  - Total Income (₹)
  - Total Expenses (₹)
  - Net Profit (₹)
- Color-coded indicators for quick insights

### 📈 Business Reports
- Comprehensive financial summaries
- Top customers by revenue
- Recent transaction history
- Exportable data for record-keeping

### 🗄️ Database Management
- SQLite database for reliable local storage
- Transaction history with timestamps
- Customer name tracking
- Detailed job descriptions

## 🛠️ Technology Stack

- **Frontend**: CustomTkinter (Modern dark-themed UI)
- **Backend**: Python 3.x
- **Database**: SQLite3 with WAL mode
- **AI/ML**: 
  - Google Gemini 1.5 Flash API
  - Google Speech-to-Text API
- **Voice**: 
  - SpeechRecognition library
  - pyttsx3 (Text-to-Speech)
  - PyAudio (Microphone access)

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- Microphone (for voice input)
- Internet connection (for AI features)

### Required Python Packages
```bash
pip install customtkinter
pip install speechrecognition
pip install pyttsx3
pip install pyaudio
pip install requests
pip install python-dotenv
```

### Setup Steps

1. **Clone or download the project**
   ```bash
   cd /path/to/project
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: Create requirements.txt with the packages listed above)*

3. **Configure Environment Variables**
   - Create a `.env` file in the project root
   - Add your Gemini API key:
     ```env
     GEMINI_API_KEY=your-gemini-api-key-here
     ```
   - Get your free API key from: https://makersuite.google.com/app/apikey
   - *(Optional)* For Google Cloud Speech-to-Text features, add GCP credentials:
     ```env
     GCP_CREDENTIALS_PATH=gcp_credentials.json
     ```

4. **Run the application**
   ```bash
   python app.py
   ```

## 🚀 Usage Guide

### Text Commands

**Recording Income:**
```
Income 1500 from Sharma Ji for motor rewinding
Received 800 from Gupta Store for fan repair
```

**Recording Expenses:**
```
Spent 250 on copper wire
Expense 100 for tools
```

**Querying Data:**
```
How much did I earn today?
Show me transactions from Sharma Ji
What were my expenses this week?
```

**Editing:**
- Click the "✏️ Edit" button to modify the last transaction
- Update the details and press Enter

**Reports:**
- Click "📊 Reports" to view comprehensive business analytics

### Voice Commands

1. Click the "🎤 Voice (Google)" button
2. Wait for the "Listening..." indicator
3. Speak your command clearly
4. The system will process and respond

### Demo Mode

Click "🚀 Demo" to populate the database with sample transactions for testing.

## 📁 Project Structure

```
.
├── app.py                          # Main application (GUI + logic)
├── database.py                     # Database operations
├── llm_worker.py                   # AI/LLM processing worker
├── .env                            # Environment variables (API keys)
├── gcp_credentials.json            # Google Cloud credentials (optional)
├── technician_records.db           # SQLite database (auto-created)
├── app.log                         # Application logs
├── vosk-model-small-en-in-0.4/     # Vosk model files (legacy)
└── venv/                           # Virtual environment
```

## 🔧 Configuration

### Environment Variables (.env)

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Your Google Gemini API key | Yes |
| `GCP_CREDENTIALS_PATH` | Path to GCP credentials JSON | No |

### Database Schema

**transactions table:**
- `id`: INTEGER PRIMARY KEY
- `type`: TEXT ('income' or 'expense')
- `amount_paise`: INTEGER (amount in paise, e.g., 50000 = ₹500)
- `customer_name`: TEXT (optional)
- `details`: TEXT (job description)
- `timestamp`: DATETIME

### API Configuration

The application uses:
1. **Gemini API**: For natural language understanding
2. **Google Speech-to-Text**: For voice recognition (requires internet)

## 🎨 UI Features

- **Dark Mode**: Easy on the eyes for long working hours
- **Modern Design**: Clean, professional interface
- **Responsive Layout**: Adapts to different screen sizes
- **Color-Coded Stats**: Green for income, red for expenses, cyan for profit
- **Scrollable Chat**: View conversation history

## 🐛 Troubleshooting

### Voice Input Not Working
- Ensure microphone is connected and permissions are granted
- Check if PyAudio is properly installed
- Verify internet connection for Google STT

### API Errors
- Verify your Gemini API key is valid
- Check internet connectivity
- Review `app.log` for detailed error messages

### Database Issues
- Delete `technician_records.db` to reset
- Check file permissions in the project directory

## 📝 Logging

Application logs are stored in `app.log` with detailed debugging information including:
- Database operations
- API calls and responses
- Voice recognition events
- Error traces

## 🔒 Security Notes

- **Environment Variables**: API keys are stored in `.env` file (not committed to git)
- **Database**: The SQLite database is stored locally and not encrypted
- **Credentials**: Store GCP credentials securely if using additional Google services
- **Never commit**: `.env`, `gcp_credentials.json`, or `technician_records.db` to version control

## 🚧 Known Limitations

- Voice recognition requires internet connection
- Gemini API has rate limits (check Google's documentation)
- Database is local only (no cloud sync)
- Limited to single-user operation

## 🔮 Future Enhancements

- [ ] Multi-user support with authentication
- [ ] Cloud database synchronization
- [ ] PDF report generation
- [ ] SMS/Email notifications for payments
- [ ] Inventory management
- [ ] Customer database with contact details
- [ ] Offline voice recognition fallback
- [ ] Mobile app companion

## 📄 License

This project is provided as-is for educational and commercial use by motor technicians.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the issues page or submit pull requests.

## 👨‍💻 Developer Notes

### Architecture
- **app.py**: Main GUI application using CustomTkinter
- **llm_worker.py**: Subprocess worker for AI processing (isolates API calls)
- **database.py**: Data access layer with validation and query functions

### Threading Model
- UI runs on main thread
- Voice recognition runs in background threads
- LLM processing uses subprocess to avoid blocking

### Error Handling
- Graceful degradation if voice libraries unavailable
- Database connection retry logic with timeouts
- Comprehensive logging for debugging

## 📞 Support

For issues or questions:
1. Check the `app.log` file for error details
2. Review the troubleshooting section
3. Ensure all dependencies are correctly installed

---

**Made with ❤️ for Indian Motor Technicians**

*Empowering small businesses with AI technology*
