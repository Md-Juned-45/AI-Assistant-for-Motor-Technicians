import customtkinter as ctk
import threading
import subprocess
import sys
import json
import database
from datetime import datetime
import tkinter.messagebox as messagebox
import time
import logging
import sqlite3

# Configure logging for debugging
logging.basicConfig(filename='app.log', level=logging.DEBUG, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Voice functionality (graceful fallback if not available)
try:
    import vosk
    import pyaudio
    import pyttsx3
    VOICE_ENABLED = True
except ImportError:
    VOICE_ENABLED = False
    print("[Info] Voice libraries not found. Voice features will be disabled.")

class EnhancedAssistantApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        try:
            database.init_db()
        except Exception as e:
            logging.error(f"Database initialization failed: {e}", exc_info=True)
            messagebox.showerror("Error", f"Failed to initialize database: {e}")
            sys.exit(1)
        
        # Enhanced UI Setup
        self.title("🔧 AI Assistant for Motor Technicians")
        self.geometry("1000x700")
        self.minsize(800, 600)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # App State
        self.conversation_history = []
        self.last_transaction_id = None
        self.is_processing = False
        self.is_edit_mode = False
        self.daily_stats = {"income": 0, "expense": 0, "jobs": 0}
        self.db_lock = threading.Lock()  # Lock for database access
        
        # Initialize voice components
        self.setup_voice_components()
        
        # Create modern UI
        self.setup_modern_ui()
        
        # Load today's stats on startup
        self.update_daily_stats()
        
        # Add welcome message
        self.add_welcome_message()
    
    def setup_voice_components(self):
        """Initialize voice recognition and TTS components"""
        self.vosk_model = None
        self.tts_engine = None
        
        if VOICE_ENABLED:
            self.vosk_model_path = r"C:/Users/juned/MVP/vosk-model-small-en-in-0.4"  # Update to your path
            try:
                self.vosk_model = vosk.Model(self.vosk_model_path)
                print("[Success] Voice recognition model loaded")
            except Exception as e:
                logging.warning(f"Voice model not found: {e}")
                print(f"[Warning] Voice model not found: {e}. Download from https://alphacephei.com/vosk/models")
                
            try:
                self.tts_engine = pyttsx3.init()
                voices = self.tts_engine.getProperty('voices')
                for voice in voices:
                    if 'indian' in voice.name.lower() or 'english' in voice.name.lower():
                        self.tts_engine.setProperty('voice', voice.id)
                        break
                self.tts_engine.setProperty('rate', 150)
                print("[Success] Text-to-speech engine initialized")
            except Exception as e:
                logging.warning(f"TTS initialization failed: {e}")
                print(f"[Warning] TTS initialization failed: {e}")

    def setup_modern_ui(self):
        """Create a modern user interface with centered chat bubbles"""
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Top section - Stats Dashboard
        self.create_stats_dashboard()
        
        # Middle section - Modern Chat Interface
        self.create_modern_chat_interface()
        
        # Bottom section - Input controls
        self.create_input_controls()
        
        # Status bar
        self.create_status_bar()

    def create_stats_dashboard(self):
        """Create a compact stats dashboard"""
        self.stats_frame = ctk.CTkFrame(self.main_container, fg_color="#2b2b2b", corner_radius=10)
        self.stats_frame.pack(fill="x", pady=(0, 10), padx=10)
        
        stats_title = ctk.CTkLabel(self.stats_frame, text="📊 Today's Summary", 
                                 font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"))
        stats_title.pack(pady=(10, 5))
        
        self.stats_container = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        self.stats_container.pack(fill="x", padx=15, pady=5)
        
        # Income stat
        self.income_frame = ctk.CTkFrame(self.stats_container, fg_color="#3a3a3a", corner_radius=8)
        self.income_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.income_label = ctk.CTkLabel(self.income_frame, text="💰 Income", 
                                       font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        self.income_label.pack(pady=(8, 2))
        self.income_value = ctk.CTkLabel(self.income_frame, text="₹0.00", 
                                       font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), 
                                       text_color="#00ff00")
        self.income_value.pack(pady=(0, 8))
        
        # Expense stat
        self.expense_frame = ctk.CTkFrame(self.stats_container, fg_color="#3a3a3a", corner_radius=8)
        self.expense_frame.pack(side="left", fill="both", expand=True, padx=5)
        self.expense_label = ctk.CTkLabel(self.expense_frame, text="💸 Expenses", 
                                        font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        self.expense_label.pack(pady=(8, 2))
        self.expense_value = ctk.CTkLabel(self.expense_frame, text="₹0.00", 
                                        font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), 
                                        text_color="#ff6b6b")
        self.expense_value.pack(pady=(0, 8))
        
        # Net profit stat
        self.profit_frame = ctk.CTkFrame(self.stats_container, fg_color="#3a3a3a", corner_radius=8)
        self.profit_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))
        self.profit_label = ctk.CTkLabel(self.profit_frame, text="📈 Net Profit", 
                                       font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        self.profit_label.pack(pady=(8, 2))
        self.profit_value = ctk.CTkLabel(self.profit_frame, text="₹0.00", 
                                       font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), 
                                       text_color="#4ecdc4")
        self.profit_value.pack(pady=(0, 8))

    def create_modern_chat_interface(self):
        """Create a modern chat interface with centered message bubbles"""
        self.chat_frame = ctk.CTkFrame(self.main_container, fg_color="#1e1e1e", corner_radius=10)
        self.chat_frame.pack(fill="both", expand=True, pady=(0, 10), padx=10)
        
        chat_title = ctk.CTkLabel(self.chat_frame, text="💬 Assistant Chat", 
                                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"))
        chat_title.pack(pady=(10, 5))
        
        # Scrollable frame for chat messages
        self.chat_scrollable = ctk.CTkScrollableFrame(self.chat_frame, fg_color="transparent")
        self.chat_scrollable.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Configure grid for dynamic resizing
        self.chat_scrollable.grid_columnconfigure(0, weight=1)

    def add_chat_message(self, message, sender="user", show_prefix=True):
        """Add message as a centered chat bubble"""
        message_frame = ctk.CTkFrame(self.chat_scrollable, fg_color="transparent")
        message_frame.grid(sticky="ew", pady=5, padx=100)  # Center with padding
        
        if sender == "assistant":
            bg_color = "#34495e" if show_prefix else "#2b2b2b"
            fg_color = "#ecf0f1"
            prefix = "🤖 Assistant: " if show_prefix else ""
        else:
            bg_color = "#3498db"
            fg_color = "#ffffff"
            prefix = "👤 You: "
        
        message_label = ctk.CTkLabel(
            message_frame,
            text=f"{prefix}{message}",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=fg_color,
            fg_color=bg_color,
            corner_radius=10,
            wraplength=700,  # Wider wrap for centered messages
            anchor="w",
            justify="left",
            width=700  # Fixed width for centering
        )
        message_label.grid(sticky="ew", padx=10)
        
        self.chat_scrollable._parent_canvas.yview_moveto(1.0)
        
        # Speak the response if TTS is available
        if sender == "assistant" and self.tts_engine and len(message) < 200:
            threading.Thread(target=self.speak_text, args=(message,), daemon=True).start()

    def create_input_controls(self):
        """Create compact input controls"""
        self.input_main_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.input_main_frame.pack(fill="x", pady=(0, 10), padx=10)
        
        # Input row - Text input and submit
        self.input_frame = ctk.CTkFrame(self.input_main_frame, fg_color="#2b2b2b", corner_radius=10)
        self.input_frame.pack(fill="x", padx=10, pady=5)
        
        self.text_input = ctk.CTkEntry(
            self.input_frame, 
            placeholder_text="Type here (e.g., 'Income 500 from Ram for motor repair')",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            height=36,
            corner_radius=8
        )
        self.text_input.pack(side="left", fill="x", expand=True, padx=(10, 5), pady=5)
        self.text_input.bind("<Return>", self.on_submit)
        
        self.submit_button = ctk.CTkButton(
            self.input_frame, 
            text="➤", 
            width=36, 
            height=36,
            command=self.on_submit,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color="#3498db",
            hover_color="#2980b9"
        )
        self.submit_button.pack(side="right", padx=(0, 10), pady=5)
        
        # Action buttons
        self.action_frame = ctk.CTkFrame(self.input_main_frame, fg_color="transparent")
        self.action_frame.pack(fill="x", padx=10, pady=5)
        
        voice_text = "🎤 Voice" if self.vosk_model else "🎤 Voice (Off)"
        self.voice_button = ctk.CTkButton(
            self.action_frame, 
            text=voice_text, 
            width=100, 
            height=32,
            command=self.on_voice_input,
            fg_color="#e74c3c" if self.vosk_model else "gray",
            hover_color="#c0392b" if self.vosk_model else "gray",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        self.voice_button.pack(side="left", padx=(0, 5))
        if not self.vosk_model:
            self.voice_button.configure(state="disabled")
        
        self.reports_button = ctk.CTkButton(
            self.action_frame, 
            text="📊 Reports", 
            width=100, 
            height=32,
            command=self.on_view_reports,
            fg_color="#3498db",
            hover_color="#2980b9",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        self.reports_button.pack(side="left", padx=5)
        
        self.edit_button = ctk.CTkButton(
            self.action_frame, 
            text="✏️ Edit", 
            width=100, 
            height=32,
            command=self.on_edit_last,
            fg_color="#f39c12",
            hover_color="#e67e22",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        self.edit_button.pack(side="left", padx=5)
        
        self.demo_button = ctk.CTkButton(
            self.action_frame, 
            text="🚀 Demo", 
            width=100, 
            height=32,
            command=self.add_demo_data,
            fg_color="#9b59b6",
            hover_color="#8e44ad",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        self.demo_button.pack(side="right")

    def create_status_bar(self):
        """Create a sleek status bar"""
        self.status_frame = ctk.CTkFrame(self.main_container, height=24, fg_color="#2b2b2b", corner_radius=8)
        self.status_frame.pack(fill="x", side="bottom", padx=10, pady=(0, 10))
        self.status_frame.pack_propagate(False)
        
        self.status_label = ctk.CTkLabel(
            self.status_frame, 
            text="🟢 Ready - Speak naturally about your work!",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.status_label.pack(side="left", padx=10, pady=5)
        
        self.time_label = ctk.CTkLabel(
            self.status_frame,
            text=datetime.now().strftime("%I:%M %p"),
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.time_label.pack(side="right", padx=10, pady=5)
        
        self.update_time()

    def add_welcome_message(self):
        """Add a professional welcome message"""
        welcome_msg = """🎉 Welcome to your AI Assistant!

I can help you:
• Track income: "Income 500 from Ram for motor repair"
• Record expenses: "Spent 50 on copper wire"
• Answer questions: "How much did I earn today?"
• Generate reports: Click 'Reports'
• Delete today's data: "Delete todays data"

Try typing or speaking naturally!"""
        
        self.add_chat_message(welcome_msg, "assistant", show_prefix=False)

    def update_time(self):
        """Update the time display"""
        current_time = datetime.now().strftime("%I:%M %p")
        self.time_label.configure(text=current_time)
        self.after(60000, self.update_time)

    def update_daily_stats(self):
        """Update the daily statistics display"""
        with self.db_lock:
            try:
                today_transactions = database.get_today_transactions()
                income_total = 0
                expense_total = 0
                
                for transaction in today_transactions:
                    amount = transaction[2] / 100
                    if transaction[1] == 'income':
                        income_total += amount
                    else:
                        expense_total += amount
                
                net_profit = income_total - expense_total
                
                self.income_value.configure(text=f"₹{income_total:.2f}")
                self.expense_value.configure(text=f"₹{expense_total:.2f}")
                self.profit_value.configure(text=f"₹{net_profit:.2f}")
                
                if net_profit >= 0:
                    self.profit_value.configure(text_color="#00ff00")
                else:
                    self.profit_value.configure(text_color="#ff6b6b")
                    
            except Exception as e:
                logging.error(f"Error updating stats: {e}", exc_info=True)
                print(f"Error updating stats: {e}")

    def add_demo_data(self):
        """Add demo transactions with delay to avoid database lock"""
        if self.is_processing:
            return
        
        self.is_processing = True
        self.update_status("Adding demo data...", "🟡")
        self.disable_buttons()
        
        demo_transactions = [
            {"type": "income", "amount_paise": 160000, "customer": "Ram", "details": "Four 400 rpm motors"},
            {"type": "income", "amount_paise": 160000, "customer": None, "details": "Four 400 rpm motors"},
            {"type": "expense", "amount_paise": 50000, "customer": None, "details": "Copper wire purchase"},
            {"type": "income", "amount_paise": 200000, "customer": "Sharma Ji", "details": "Motor rewinding"},
        ]
        
        def insert_demo_transactions():
            with self.db_lock:
                try:
                    for transaction in demo_transactions:
                        is_valid, error_msg = database.validate_transaction_data(transaction)
                        if is_valid:
                            database.add_transaction(transaction)
                            time.sleep(0.1)
                        else:
                            self.add_chat_message(f"⚠️ Invalid demo transaction: {error_msg}", "assistant")
                    self.add_chat_message("✅ Demo data added successfully!", "assistant")
                except Exception as e:
                    logging.error(f"Error adding demo data: {e}", exc_info=True)
                    self.add_chat_message(f"❌ Error adding demo data: {str(e)}", "assistant")
                finally:
                    self.is_processing = False
                    self.update_status("Ready - Speak naturally about your work!", "🟢")
                    self.enable_buttons()
                    self.update_daily_stats()
        
        threading.Thread(target=insert_demo_transactions, daemon=True).start()

    def update_status(self, text, emoji="🟢"):
        """Update status with emoji indicators"""
        self.status_label.configure(text=f"{emoji} {text}")

    def on_submit(self, event=None):
        """Handle text input submission"""
        text = self.text_input.get().strip()
        if text and not self.is_processing:
            self.text_input.delete(0, "end")
            self.add_chat_message(text, "user")
            self.process_command(text)

    def on_voice_input(self):
        """Handle voice input with better feedback"""
        if not self.is_processing and VOICE_ENABLED and self.vosk_model:
            threading.Thread(target=self.listen_and_process_voice, daemon=True).start()
        elif not self.vosk_model:
            messagebox.showinfo("Voice Input", "Voice recognition model not available.\nDownload from https://alphacephei.com/vosk/models and place in C:\\Users\\juned\\vosk-model-small-en-in-0.4")

    def listen_and_process_voice(self):
        """Listen for voice input and process it"""
        self.after(0, self.update_status, "Listening... Speak now!", "🎤")
        self.after(0, self.disable_buttons)
        
        text = self.listen_voice()
        if text:
            self.after(0, self.add_chat_message, f"🎤 {text}", "user")
            self.process_command(text)
        else:
            self.after(0, self.update_status, "Could not understand. Please try again.", "⚠️")
            self.after(0, self.enable_buttons)

    def listen_voice(self):
        """Improved voice recognition with better error handling"""
        if not self.vosk_model:
            return None
            
        try:
            rec = vosk.KaldiRecognizer(self.vosk_model, 16000)
            p = pyaudio.PyAudio()
            
            info = p.get_host_api_info_by_index(0)
            numdevices = info.get('deviceCount')
            
            input_device = None
            for i in range(0, numdevices):
                device_info = p.get_device_info_by_host_api_device_index(0, i)
                if device_info.get('maxInputChannels') > 0:
                    input_device = i
                    break
            
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                input_device_index=input_device,
                frames_per_buffer=4096
            )
            stream.start_stream()
            
            self.after(0, self.update_status, "🎤 Listening... (speak clearly)", "🎤")
            
            silence_chunks = 0
            max_silence = 15
            
            while True:
                data = stream.read(4096, exception_on_overflow=False)
                
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "").strip()
                    if text:
                        break
                else:
                    partial_result = json.loads(rec.PartialResult())
                    partial_text = partial_result.get('partial', '').strip()
                    
                    if partial_text:
                        silence_chunks = 0
                        self.after(0, self.update_status, f"Hearing: {partial_text[:30]}...", "👂")
                    else:
                        silence_chunks += 1
                    
                    if silence_chunks > max_silence:
                        final_result = json.loads(rec.FinalResult())
                        text = final_result.get("text", "").strip()
                        break
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            return text if text else None
            
        except Exception as e:
            logging.error(f"Voice Error: {e}", exc_info=True)
            print(f"[Voice Error]: {e}")
            return None

    def speak_text(self, text):
        """Improved text-to-speech"""
        if not self.tts_engine:
            return
        try:
            clean_text = text.replace("₹", "rupees ").replace("✅", "").replace("📊", "")
            self.tts_engine.say(clean_text)
            self.tts_engine.runAndWait()
        except Exception as e:
            logging.error(f"TTS Error: {e}", exc_info=True)
            print(f"[TTS Error]: {e}")

    def process_command(self, command_text, task='parse_command', context=None):
        """Enhanced command processing with better error handling"""
        if self.is_processing:
            return
            
        self.is_processing = True
        self.update_status("Thinking... 🤔", "🤔")
        self.disable_buttons()

        worker_input = {
            'task': task,
            'history': self.conversation_history + [{'role': 'user', 'content': command_text}],
            'context': context or {}
        }

        threading.Thread(target=self._run_llm_parser, args=(command_text, worker_input), daemon=True).start()

    def _run_llm_parser(self, user_message, worker_input):
        """Run the LLM worker process"""
        try:
            python_executable = sys.executable
            process = subprocess.Popen(
                [python_executable, 'llm_worker.py'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            stdout, stderr = process.communicate(input=json.dumps(worker_input, ensure_ascii=False), timeout=60)
            
            if stderr:
                logging.error(f"LLM Worker Error: {stderr}")
                raise Exception(f"LLM Worker Error: {stderr}")
                
            response_data = json.loads(stdout.strip())
        except subprocess.TimeoutExpired:
            logging.error("LLM worker timed out")
            response_data = {'intent': 'error', 'payload': 'Request timed out. Please try again.'}
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse LLM response: {e}\nInput: {worker_input}\nOutput: {stdout}")
            response_data = {'intent': 'error', 'payload': 'Failed to parse AI response. Please try again.'}
        except Exception as e:
            logging.error(f"LLM worker error: {e}", exc_info=True)
            response_data = {'intent': 'error', 'payload': f'System error: {str(e)}'}
            
        self.after(0, self.handle_llm_response, user_message, response_data)

    def handle_llm_response(self, user_message, response_data):
        """Enhanced response handling with better user feedback"""
        intent = response_data.get('intent', 'error')
        payload = response_data.get('payload')
        assistant_response_text = ""

        try:
            if intent == 'database_query':
                if payload:
                    with self.db_lock:
                        db_results = database.query_transactions(payload)
                    if not db_results:
                        assistant_response_text = "🔍 No matching records found. Try asking about specific customers or job details."
                        self.add_chat_message(assistant_response_text, "assistant")
                        self.reset_ui_state()
                    else:
                        context_for_answer = {'user_question': user_message, 'db_results': json.dumps(db_results)}
                        self.process_command(user_message, task='formulate_answer_from_data', context=context_for_answer)
                        return
                else:
                    assistant_response_text = "🤔 I need more specific details to search for."

            elif intent == 'delete_transactions':
                retries = 3
                for attempt in range(retries):
                    try:
                        with self.db_lock:
                            deleted_count = database.delete_todays_transactions()
                        if deleted_count > 0:
                            assistant_response_text = f"✅ Successfully deleted {deleted_count} transactions from today."
                            self.update_daily_stats()
                        else:
                            assistant_response_text = "🔔 No transactions found for today to delete."
                        break
                    except sqlite3.OperationalError as e:
                        if "database is locked" in str(e) and attempt < retries - 1:
                            time.sleep(0.5)
                            continue
                        logging.error(f"Failed to delete transactions: {e}", exc_info=True)
                        assistant_response_text = f"❌ Error deleting transactions: {str(e)}"
                        break

            elif intent == 'answer':
                assistant_response_text = f"📊 {payload}"

            elif self.is_edit_mode:
                if intent == 'transaction' and payload:
                    with self.db_lock:
                        is_valid, error_msg = database.validate_transaction_data(payload)
                        if is_valid:
                            database.update_transaction(self.last_transaction_id, payload)
                            assistant_response_text = f"✅ Transaction #{self.last_transaction_id} updated!"
                            self.update_daily_stats()
                        else:
                            assistant_response_text = f"⚠️ Invalid update: {error_msg}"
                else:
                    assistant_response_text = "⚠️ Please include amount and description for the update."
                self.is_edit_mode = False
                self.submit_button.configure(text="➤")

            elif intent == 'transaction':
                if payload:
                    with self.db_lock:
                        is_valid, error_msg = database.validate_transaction_data(payload)
                        if is_valid:
                            transaction_id = database.add_transaction(payload)
                            self.last_transaction_id = transaction_id
                            
                            trans_type = payload.get('type', 'transaction').title()
                            amount = payload.get('amount_paise', 0) / 100
                            customer = payload.get('customer', 'None')
                            details = payload.get('details', 'No details')
                            
                            assistant_response_text = f"✅ {trans_type} recorded!\n"
                            assistant_response_text += f"💰 Amount: ₹{amount:.2f}\n"
                            if customer != 'None':
                                assistant_response_text += f"👤 Customer: {customer}\n"
                            assistant_response_text += f"📝 Details: {details}\n"
                            assistant_response_text += f"🆔 Transaction ID: #{transaction_id}"
                            
                            self.update_daily_stats()
                        else:
                            assistant_response_text = f"⚠️ Invalid transaction: {error_msg}"
                else:
                    assistant_response_text = "⚠️ Please include an amount (e.g., 'income 500 from Ram for motor repair')."

            elif intent == 'update_transaction':
                if payload and self.last_transaction_id:
                    with self.db_lock:
                        is_valid, error_msg = database.validate_transaction_data(payload)
                        if is_valid:
                            database.update_transaction(self.last_transaction_id, payload)
                            assistant_response_text = f"✅ Transaction #{self.last_transaction_id} updated!"
                            self.update_daily_stats()
                        else:
                            assistant_response_text = f"⚠️ Invalid update: {error_msg}"
                else:
                    assistant_response_text = "⚠️ No recent transaction to update, or I couldn't understand the changes."

            elif intent == 'greeting':
                assistant_response_text = "🙏 Namaste! Ready to track your motor repair business. What would you like to do?"
                
            elif intent == 'question':
                assistant_response_text = "💡 I can help you:\n• Log income/expenses\n• Track customer payments\n• Generate reports\n• Answer transaction queries\n• Delete today's data (say 'delete todays data')\n\nWhat's next?"
                
            elif intent == 'error':
                assistant_response_text = f"❌ Error: {payload}\n\nTry rephrasing or contact support."
            else:
                assistant_response_text = "🤔 Not sure how to help. Try:\n• 'Income 500 from Ram for motor repair'\n• 'Spent 100 on copper wire'\n• 'How much did I earn today?'\n• 'Delete todays data'"

            self.add_chat_message(assistant_response_text, "assistant")
            
            self.conversation_history.append({'role': 'user', 'content': user_message})
            self.conversation_history.append({'role': 'assistant', 'content': json.dumps(response_data)})
            self.conversation_history = self.conversation_history[-6:]
            
        except Exception as e:
            logging.error(f"Error handling LLM response: {e}", exc_info=True)
            assistant_response_text = f"❌ Unexpected error: {str(e)}"
            self.add_chat_message(assistant_response_text, "assistant")
            
        finally:
            self.reset_ui_state()

    def reset_ui_state(self):
        """Reset UI to ready state"""
        self.is_processing = False
        self.update_status("Ready - Speak naturally about your work!", "🟢")
        self.enable_buttons()

    def disable_buttons(self):
        """Disable all interactive buttons"""
        self.submit_button.configure(state="disabled")
        self.edit_button.configure(state="disabled")
        self.voice_button.configure(state="disabled")
        self.reports_button.configure(state="disabled")
        self.demo_button.configure(state="disabled")

    def enable_buttons(self):
        """Enable all interactive buttons"""
        self.submit_button.configure(state="normal")
        self.edit_button.configure(state="normal")
        if self.vosk_model:
            self.voice_button.configure(state="normal")
        self.reports_button.configure(state="normal")
        self.demo_button.configure(state="normal")

    def on_edit_last(self):
        """Enhanced edit functionality"""
        if self.is_processing:
            return
            
        last_trans = database.get_last_transaction()
        if last_trans:
            self.is_edit_mode = True
            self.last_transaction_id = last_trans[0]
            
            trans_type, amount_rs, customer, details = (
                last_trans[1], 
                last_trans[2] / 100, 
                last_trans[3], 
                last_trans[4]
            )
            
            edit_text = f"{trans_type} of {amount_rs:.2f}"
            if customer:
                edit_text += f" from {customer}"
            if details:
                edit_text += f" for {details}"
            
            self.text_input.delete(0, "end")
            self.text_input.insert(0, edit_text)
            self.submit_button.configure(text="💾")
            self.update_status(f"Editing Transaction #{self.last_transaction_id}", "✏️")
            self.text_input.focus()
        else:
            self.add_chat_message("⚠️ No transactions to edit. Record a transaction first.", "assistant")

    def on_view_reports(self):
        """Enhanced reporting with better formatting"""
        with self.db_lock:
            try:
                transactions = database.get_all_transactions()
                if not transactions:
                    report_text = "📊 **Business Report**\n\n❌ No transactions recorded.\n\nStart with: 'Income 500 from Ram for motor repair'"
                else:
                    report_text = "📊 **COMPLETE BUSINESS REPORT**\n"
                    report_text += "=" * 50 + "\n\n"
                    
                    total_income = 0
                    total_expense = 0
                    customer_summary = {}
                    
                    report_text += "📋 **TRANSACTION HISTORY**\n"
                    report_text += "-" * 50 + "\n"
                    
                    for i, t in enumerate(transactions[-10:], 1):
                        amount_rupees = t[2] / 100
                        transaction_type = t[1].upper()
                        customer = t[3] or "N/A"
                        details = t[4] or "No details"
                        timestamp = t[5]
                        
                        if t[1] == 'income':
                            total_income += amount_rupees
                            emoji = "💰"
                            if customer != "N/A":
                                customer_summary[customer] = customer_summary.get(customer, 0) + amount_rupees
                        else:
                            total_expense += amount_rupees
                            emoji = "💸"
                        
                        report_text += f"{emoji} {transaction_type:<8} | ₹{amount_rupees:>8.2f} | {customer:<15} | {details[:30]}\n"
                    
                    report_text += "-" * 50 + "\n\n"
                    
                    report_text += "💼 **FINANCIAL SUMMARY**\n"
                    report_text += f"💰 Total Income:    ₹{total_income:>10.2f}\n"
                    report_text += f"💸 Total Expenses:  ₹{total_expense:>10.2f}\n"
                    report_text += f"📈 Net Profit:      ₹{total_income - total_expense:>10.2f}\n\n"
                    
                    if customer_summary:
                        report_text += "👥 **TOP CUSTOMERS**\n"
                        sorted_customers = sorted(customer_summary.items(), key=lambda x: x[1], reverse=True)
                        for customer, amount in sorted_customers[:5]:
                            report_text += f"   • {customer:<20} ₹{amount:.2f}\n"
                    
                    avg_transaction = total_income / max(len([t for t in transactions if t[1] == 'income']), 1)
                    report_text += f"\n📊 **BUSINESS INSIGHTS**\n"
                    report_text += f"   • Average job value: ₹{avg_transaction:.2f}\n"
                    report_text += f"   • Total transactions: {len(transactions)}\n"
                    report_text += f"   • Profit margin: {((total_income - total_expense) / max(total_income, 1) * 100):.1f}%\n"
                
                self.add_chat_message(report_text, "assistant")
            
            except Exception as e:
                logging.error(f"Error generating report: {e}", exc_info=True)
                self.add_chat_message(f"❌ Error generating report: {str(e)}", "assistant")

if __name__ == "__main__":
    try:
        app = EnhancedAssistantApp()
        app.mainloop()
    except Exception as e:
        logging.error(f"Application failed to start: {e}", exc_info=True)
        print(f"[Error] Application failed to start: {e}")
        messagebox.showerror("Error", f"Application failed to start: {e}")