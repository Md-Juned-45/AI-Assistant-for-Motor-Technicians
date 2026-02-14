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

# --- New Imports for Google STT ---
import speech_recognition as sr

# Configure logging for debugging
logging.basicConfig(filename='app.log', level=logging.DEBUG,
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Voice functionality (graceful fallback if not available)
try:
    # We still need pyaudio for microphone access
    import pyaudio
    import pyttsx3
    VOICE_ENABLED = True
except ImportError:
    VOICE_ENABLED = False
    print("[Info] Voice libraries (pyaudio, pyttsx3, SpeechRecognition) not found. Voice features will be disabled.")

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

        # --- App State & Configuration ---
        self.gemini_api_key = "AIzaSyD8LSzLKuT3BaPDOnVcvlrpI1UVUEMAGcU" # Your Gemini API Key
        self.conversation_history = []
        self.last_transaction_id = None
        self.is_processing = False
        self.is_edit_mode = False
        self.daily_stats = {"income": 0, "expense": 0, "jobs": 0}
        self.db_lock = threading.Lock()

        # Initialize voice components
        self.setup_voice_components()
        self.setup_modern_ui()
        self.update_daily_stats()
        self.add_welcome_message()

    def setup_voice_components(self):
        """Initialize TTS components. Vosk is replaced by Google STT."""
        self.tts_engine = None
        if VOICE_ENABLED:
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
        print("[Info] Voice recognition is now powered by Google Speech-to-Text.")


    def setup_modern_ui(self):
        """Create a modern user interface"""
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)
        self.create_stats_dashboard()
        self.create_modern_chat_interface()
        self.create_input_controls()
        self.create_status_bar()

    def create_stats_dashboard(self):
        self.stats_frame = ctk.CTkFrame(self.main_container, fg_color="#2b2b2b", corner_radius=10)
        self.stats_frame.pack(fill="x", pady=(0, 10), padx=10)
        stats_title = ctk.CTkLabel(self.stats_frame, text="📊 Today's Summary", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"))
        stats_title.pack(pady=(10, 5))
        self.stats_container = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        self.stats_container.pack(fill="x", padx=15, pady=5)
        self.income_frame = ctk.CTkFrame(self.stats_container, fg_color="#3a3a3a", corner_radius=8)
        self.income_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.income_label = ctk.CTkLabel(self.income_frame, text="💰 Income", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        self.income_label.pack(pady=(8, 2))
        self.income_value = ctk.CTkLabel(self.income_frame, text="₹0.00", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), text_color="#00ff00")
        self.income_value.pack(pady=(0, 8))
        self.expense_frame = ctk.CTkFrame(self.stats_container, fg_color="#3a3a3a", corner_radius=8)
        self.expense_frame.pack(side="left", fill="both", expand=True, padx=5)
        self.expense_label = ctk.CTkLabel(self.expense_frame, text="💸 Expenses", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        self.expense_label.pack(pady=(8, 2))
        self.expense_value = ctk.CTkLabel(self.expense_frame, text="₹0.00", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), text_color="#ff6b6b")
        self.expense_value.pack(pady=(0, 8))
        self.profit_frame = ctk.CTkFrame(self.stats_container, fg_color="#3a3a3a", corner_radius=8)
        self.profit_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))
        self.profit_label = ctk.CTkLabel(self.profit_frame, text="📈 Net Profit", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        self.profit_label.pack(pady=(8, 2))
        self.profit_value = ctk.CTkLabel(self.profit_frame, text="₹0.00", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), text_color="#4ecdc4")
        self.profit_value.pack(pady=(0, 8))

    def create_modern_chat_interface(self):
        self.chat_frame = ctk.CTkFrame(self.main_container, fg_color="#1e1e1e", corner_radius=10)
        self.chat_frame.pack(fill="both", expand=True, pady=(0, 10), padx=10)
        chat_title = ctk.CTkLabel(self.chat_frame, text="💬 Assistant Chat", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"))
        chat_title.pack(pady=(10, 5))
        self.chat_scrollable = ctk.CTkScrollableFrame(self.chat_frame, fg_color="transparent")
        self.chat_scrollable.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.chat_scrollable.grid_columnconfigure(0, weight=1)

    def create_input_controls(self):
        self.input_main_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.input_main_frame.pack(fill="x", pady=(0, 10), padx=10)
        self.input_frame = ctk.CTkFrame(self.input_main_frame, fg_color="#2b2b2b", corner_radius=10)
        self.input_frame.pack(fill="x", padx=10, pady=5)
        self.text_input = ctk.CTkEntry(self.input_frame, placeholder_text="Type here (e.g., 'Income 500 from Ram for motor repair')", font=ctk.CTkFont(family="Segoe UI", size=12), height=36, corner_radius=8)
        self.text_input.pack(side="left", fill="x", expand=True, padx=(10, 5), pady=5)
        self.text_input.bind("<Return>", self.on_submit)
        self.submit_button = ctk.CTkButton(self.input_frame, text="➤", width=36, height=36, command=self.on_submit, font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), fg_color="#3498db", hover_color="#2980b9")
        self.submit_button.pack(side="right", padx=(0, 10), pady=5)
        self.action_frame = ctk.CTkFrame(self.input_main_frame, fg_color="transparent")
        self.action_frame.pack(fill="x", padx=10, pady=5)
        voice_text = "🎤 Voice (Google)" if VOICE_ENABLED else "🎤 Voice (Off)"
        self.voice_button = ctk.CTkButton(self.action_frame, text=voice_text, width=120, height=32, command=self.on_voice_input, fg_color="#e74c3c" if VOICE_ENABLED else "gray", hover_color="#c0392b" if VOICE_ENABLED else "gray", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        self.voice_button.pack(side="left", padx=(0, 5))
        if not VOICE_ENABLED: self.voice_button.configure(state="disabled")
        self.reports_button = ctk.CTkButton(self.action_frame, text="📊 Reports", width=100, height=32, command=self.on_view_reports, fg_color="#3498db", hover_color="#2980b9", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        self.reports_button.pack(side="left", padx=5)
        self.edit_button = ctk.CTkButton(self.action_frame, text="✏️ Edit", width=100, height=32, command=self.on_edit_last, fg_color="#f39c12", hover_color="#e67e22", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        self.edit_button.pack(side="left", padx=5)
        self.demo_button = ctk.CTkButton(self.action_frame, text="🚀 Demo", width=100, height=32, command=self.add_demo_data, fg_color="#9b59b6", hover_color="#8e44ad", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        self.demo_button.pack(side="right")

    def create_status_bar(self):
        self.status_frame = ctk.CTkFrame(self.main_container, height=24, fg_color="#2b2b2b", corner_radius=8)
        self.status_frame.pack(fill="x", side="bottom", padx=10, pady=(0, 10))
        self.status_frame.pack_propagate(False)
        self.status_label = ctk.CTkLabel(self.status_frame, text="🟢 Ready - Powered by Gemini API", font=ctk.CTkFont(family="Segoe UI", size=11))
        self.status_label.pack(side="left", padx=10, pady=5)
        self.time_label = ctk.CTkLabel(self.status_frame, text=datetime.now().strftime("%I:%M %p"), font=ctk.CTkFont(family="Segoe UI", size=11))
        self.time_label.pack(side="right", padx=10, pady=5)
        self.update_time()
    
    # --- FIX: Added the missing update_status method ---
    def update_status(self, text, emoji="🟢"):
        """Update status with emoji indicators"""
        self.status_label.configure(text=f"{emoji} {text}")

    def add_welcome_message(self):
        welcome_msg = """🎉 Welcome to your AI Assistant!

I can help you:
• Track income: "Income 500 from Ram for motor repair"
• Record expenses: "Spent 50 on copper wire"
• Answer questions: "How much did I earn today?"
• Generate reports: Click 'Reports'

Try typing or speaking naturally!"""
        self.add_chat_message(welcome_msg, "assistant", show_prefix=False)

    def update_time(self):
        current_time = datetime.now().strftime("%I:%M %p")
        self.time_label.configure(text=current_time)
        self.after(60000, self.update_time)

    def add_chat_message(self, message, sender="user", show_prefix=True):
        message_frame = ctk.CTkFrame(self.chat_scrollable, fg_color="transparent")
        message_frame.grid(sticky="ew", pady=5, padx=100)
        if sender == "assistant":
            bg_color, fg_color, prefix = ("#34495e", "#ecf0f1", "🤖 Assistant: ") if show_prefix else ("#2b2b2b", "#ecf0f1", "")
        else:
            bg_color, fg_color, prefix = "#3498db", "#ffffff", "👤 You: "
        message_label = ctk.CTkLabel(message_frame, text=f"{prefix}{message}", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=fg_color, fg_color=bg_color, corner_radius=10, wraplength=700, anchor="w", justify="left", width=700)
        message_label.grid(sticky="ew", padx=10)
        self.chat_scrollable._parent_canvas.yview_moveto(1.0)
        if sender == "assistant" and self.tts_engine and len(message) < 200:
            threading.Thread(target=self.speak_text, args=(message,), daemon=True).start()

    def update_daily_stats(self):
        with self.db_lock:
            try:
                today_transactions = database.get_today_transactions()
                income_total = sum(t[2] / 100 for t in today_transactions if t[1] == 'income')
                expense_total = sum(t[2] / 100 for t in today_transactions if t[1] == 'expense')
                net_profit = income_total - expense_total
                self.income_value.configure(text=f"₹{income_total:.2f}")
                self.expense_value.configure(text=f"₹{expense_total:.2f}")
                self.profit_value.configure(text=f"₹{net_profit:.2f}")
                self.profit_value.configure(text_color="#00ff00" if net_profit >= 0 else "#ff6b6b")
            except Exception as e:
                logging.error(f"Error updating stats: {e}", exc_info=True)

    def on_submit(self, event=None):
        text = self.text_input.get().strip()
        if text and not self.is_processing:
            self.text_input.delete(0, "end")
            self.add_chat_message(text, "user")
            self.process_command(text)

    def on_voice_input(self):
        if not self.is_processing and VOICE_ENABLED:
            threading.Thread(target=self.listen_and_process_voice, daemon=True).start()

    def listen_and_process_voice(self):
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
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.pause_threshold = 0.8
            r.adjust_for_ambient_noise(source, duration=0.5)
            self.after(0, self.update_status, "🎤 Listening via Google...", "🎤")
            try:
                audio = r.listen(source, timeout=5, phrase_time_limit=15)
                self.after(0, self.update_status, "✅ Got it! Processing...", "⚙️")
                text = r.recognize_google_cloud(audio, language="en-IN")
                return text
            except sr.WaitTimeoutError:
                self.after(0, self.update_status, "⚠️ Listening timed out.", "⚠️")
                return None
            except sr.UnknownValueError:
                self.after(0, self.update_status, "🤔 Couldn't understand audio.", "🤔")
                return None
            except sr.RequestError as e:
                self.after(0, messagebox.showerror, "API Error", f"API error: {e}. Check credentials.")
                return None
            except Exception as e:
                self.after(0, messagebox.showerror, "Voice Error", f"An unexpected error occurred: {e}")
                return None

    def speak_text(self, text):
        if not self.tts_engine: return
        try:
            clean_text = text.replace("₹", "rupees ").replace("✅", "").replace("📊", "")
            self.tts_engine.say(clean_text)
            self.tts_engine.runAndWait()
        except Exception as e:
            logging.error(f"TTS Error: {e}", exc_info=True)

    def process_command(self, command_text, task='parse_command', context=None):
        if self.is_processing: return
        self.is_processing = True
        self.update_status("Thinking... 🤔", "🤔")
        self.disable_buttons()
        worker_input = {
            'task': task,
            'history': self.conversation_history + [{'role': 'user', 'content': command_text}],
            'context': context or {},
            'api_key': self.gemini_api_key
        }
        threading.Thread(target=self._run_llm_parser, args=(command_text, worker_input), daemon=True).start()

    def _run_llm_parser(self, user_message, worker_input):
        try:
            python_executable = sys.executable
            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            process = subprocess.Popen(
                [python_executable, 'llm_worker.py'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding='utf-8', creationflags=creation_flags
            )
            stdout, stderr = process.communicate(input=json.dumps(worker_input, ensure_ascii=False), timeout=60)
            if stderr: raise Exception(f"LLM Worker Error: {stderr}")
            response_data = json.loads(stdout.strip())
        except Exception as e:
            logging.error(f"LLM worker error: {e}", exc_info=True)
            response_data = {'intent': 'error', 'payload': f'System error: {str(e)}'}
        self.after(0, self.handle_llm_response, user_message, response_data)

    def handle_llm_response(self, user_message, response_data):
        intent = response_data.get('intent', 'error')
        payload = response_data.get('payload')
        assistant_response_text = ""
        try:
            if intent == 'database_query':
                if payload:
                    with self.db_lock:
                        db_results = database.query_transactions(payload)
                    if not db_results:
                        self.add_chat_message("🔍 No matching records found.", "assistant")
                        self.reset_ui_state()
                    else:
                        context = {'user_question': user_message, 'db_results': json.dumps(db_results, default=str)}
                        self.process_command(user_message, task='formulate_answer_from_data', context=context)
                        return
                else:
                    assistant_response_text = "🤔 I need more specific details to search for."
            elif intent == 'delete_transactions':
                with self.db_lock:
                    deleted_count = database.delete_todays_transactions()
                assistant_response_text = f"✅ Successfully deleted {deleted_count} transactions from today." if deleted_count > 0 else "🔔 No transactions found for today to delete."
                self.update_daily_stats()
            elif intent == 'answer':
                assistant_response_text = f"📊 {payload}"
            elif intent == 'transaction':
                if payload:
                    with self.db_lock:
                        is_valid, msg = database.validate_transaction_data(payload)
                        if is_valid:
                            tid = database.add_transaction(payload)
                            self.last_transaction_id = tid
                            trans_type = payload.get('type', 'Tx').title()
                            amt = payload.get('amount_paise', 0) / 100
                            assistant_response_text = f"✅ {trans_type} of ₹{amt:.2f} recorded (ID: #{tid})."
                            self.update_daily_stats()
                        else:
                             assistant_response_text = f"⚠️ Invalid transaction: {msg}"
                else:
                    assistant_response_text = "⚠️ Please include an amount."
            elif intent == 'update_transaction':
                if payload and self.last_transaction_id:
                    with self.db_lock:
                        database.update_transaction(self.last_transaction_id, payload)
                        assistant_response_text = f"✅ Transaction #{self.last_transaction_id} updated!"
                        self.update_daily_stats()
                else:
                    assistant_response_text = "⚠️ No recent transaction to update."
            elif intent in ['greeting', 'question', 'personal_response', 'general_response']:
                 assistant_response_text = payload
            elif intent == 'error':
                assistant_response_text = f"❌ Error: {payload}"
            else:
                assistant_response_text = "🤔 I'm not sure how to handle that."
            self.add_chat_message(assistant_response_text, "assistant")
            self.conversation_history.extend([{'role': 'user', 'content': user_message}, {'role': 'assistant', 'content': json.dumps(response_data)}])
            self.conversation_history = self.conversation_history[-6:]
        except Exception as e:
            logging.error(f"Error handling LLM response: {e}", exc_info=True)
            self.add_chat_message(f"❌ Unexpected error: {str(e)}", "assistant")
        finally:
            self.reset_ui_state()

    def reset_ui_state(self):
        self.is_processing = False
        self.update_status("Ready - Powered by Gemini API", "🟢")
        self.enable_buttons()

    def disable_buttons(self):
        for button in [self.submit_button, self.edit_button, self.voice_button, self.reports_button, self.demo_button]:
            button.configure(state="disabled")

    def enable_buttons(self):
        for button in [self.submit_button, self.edit_button, self.reports_button, self.demo_button]:
             button.configure(state="normal")
        if VOICE_ENABLED: self.voice_button.configure(state="normal")

    def on_edit_last(self):
        if self.is_processing: return
        last_trans = database.get_last_transaction()
        if last_trans:
            self.is_edit_mode = True
            self.last_transaction_id = last_trans[0]
            edit_text = f"{last_trans[1]} {last_trans[2]/100} from {last_trans[3]} for {last_trans[4]}"
            self.text_input.delete(0, "end")
            self.text_input.insert(0, edit_text.replace("None","").strip())
            self.submit_button.configure(text="💾")
            self.update_status(f"Editing Transaction #{self.last_transaction_id}", "✏️")
            self.text_input.focus()
        else:
            self.add_chat_message("⚠️ No transactions to edit.", "assistant")

    def on_view_reports(self):
        report_popup = ctk.CTkToplevel(self)
        report_popup.title("📊 Business Report")
        report_popup.geometry("650x700")
        report_popup.transient(self)
        report_popup.grab_set()
        textbox = ctk.CTkTextbox(report_popup, font=ctk.CTkFont(family="Consolas", size=12), wrap="word")
        textbox.pack(expand=True, fill="both", padx=10, pady=10)
        textbox.insert("0.0", "Generating report, please wait...")
        textbox.configure(state="disabled")
        threading.Thread(target=self._generate_and_display_report, args=(textbox,), daemon=True).start()

    def _generate_and_display_report(self, textbox_widget):
        with self.db_lock:
            transactions = database.get_all_transactions()
        if not transactions:
            report_text = "📊 Business Report\n\nNo transactions recorded yet."
        else:
            total_income = sum(t[2] / 100 for t in transactions if t[1] == 'income')
            total_expense = sum(t[2] / 100 for t in transactions if t[1] == 'expense')
            customer_summary = {t[3]: customer_summary.get(t[3], 0) + (t[2] / 100) for t in transactions if t[1] == 'income' and t[3] is not None}
            report_text = "📊 COMPLETE BUSINESS REPORT\n" + "=" * 50 + "\n\n"
            report_text += f"💼 FINANCIAL SUMMARY\n{'Total Income:':<18} ₹{total_income:>10.2f}\n{'Total Expenses:':<18} ₹{total_expense:>10.2f}\n{'Net Profit:':<18} ₹{total_income - total_expense:>10.2f}\n\n"
            if customer_summary:
                report_text += "👥 TOP CUSTOMERS BY REVENUE\n"
                for customer, amount in sorted(customer_summary.items(), key=lambda item: item[1], reverse=True)[:5]:
                    report_text += f"  - {customer:<20} ₹{amount:.2f}\n"
                report_text += "\n"
            report_text += "📋 RECENT TRANSACTION HISTORY (Last 20)\n" + "-" * 50 + "\n"
            for t in transactions[:20]:
                timestamp_obj = datetime.strptime(t[5].split('.')[0], '%Y-%m-%d %H:%M:%S')
                report_text += f"[{timestamp_obj.strftime('%d-%b-%Y')}] {t[1].title():<7} | ₹{t[2]/100:>8.2f} | {t[3] or 'N/A':<15} | {t[4] or 'No Details'}\n"
        def update_textbox():
            textbox_widget.configure(state="normal")
            textbox_widget.delete("1.0", "end")
            textbox_widget.insert("1.0", report_text)
            textbox_widget.configure(state="disabled")
        self.after(0, update_textbox)
        
    def add_demo_data(self):
        if self.is_processing: return
        self.update_status("Adding demo data...", "🟡")
        demo_data = [{"type": "income", "amount_paise": 150000, "customer": "Sharma Ji", "details": "Motor rewinding"}, {"type": "expense", "amount_paise": 25000, "customer": None, "details": "Copper wire"}, {"type": "income", "amount_paise": 80000, "customer": "Gupta Store", "details": "Fan repair"}]
        with self.db_lock:
            for item in demo_data:
                database.add_transaction(item)
        self.add_chat_message("✅ Demo data added successfully!", "assistant")
        self.update_daily_stats()
        self.reset_ui_state()

if __name__ == "__main__":
    try:
        app = EnhancedAssistantApp()
        app.mainloop()
    except Exception as e:
        logging.critical(f"Application failed to start: {e}", exc_info=True)
        messagebox.showerror("Critical Error", f"Application failed to start: {e}")
