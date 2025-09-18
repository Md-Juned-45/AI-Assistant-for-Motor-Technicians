# llm_worker.py - Simplified with business-first detection

import sys
import json
import re
from typing import Dict, List, Optional
from datetime import datetime

# --- Configuration ---
try:
    import ollama
    OLLAMA_AVAILABLE = True
    MODEL_NAME = 'phi3'  # Or your preferred model
    client = ollama.Client(host='http://localhost:11434', timeout=60)
except ImportError:
    OLLAMA_AVAILABLE = False
    print("[Alert] Ollama library not found. The AI worker cannot function.")

# --- Business Pattern Detection ---

BUSINESS_KEYWORDS = [
    # Transaction keywords
    r'\b(income|earning|earn|earned|kamaya|paisa|rupee|rs\.?|₹)\b',
    r'\b(expense|spent|spend|kharcha|kharch)\b',
    r'\b(customer|client|sahib|ji)\b',
    
    # Service keywords  
    r'\b(motor|motar|rewinding|repair|fix|service)\b',
    r'\b(winding|coil|bearing|pump)\b',
    
    # Query keywords
    r'\b(report|total|sum|today|yesterday|month|week)\b',
    r'\b(show|display|list|kitna|kya|how much)\b',
    r'\b(delete|remove|cancel|galat)\b',
    
    # Amount patterns
    r'\b\d+\s*(rupee|rs|₹|paisa)\b',
    r'\b(from|to|for|se|ko)\s+[A-Za-z]+\b'  # "from Ram", "to Shyam"
]

def looks_like_business_query(message: str) -> bool:
    """
    Quick pattern-based detection for business-related content.
    Returns True if message contains business keywords/patterns.
    """
    message_lower = message.lower()
    
    for pattern in BUSINESS_KEYWORDS:
        if re.search(pattern, message_lower, re.IGNORECASE):
            return True
    
    return False

# --- System Prompts ---

# Main LLM prompt for general interactions
def get_general_llm_prompt(user_message: str) -> str:
    current_date = datetime.now().strftime('%Y-%m-%d')
    return f"""
You are a helpful AI assistant for a motor repair technician in India. You can:
1. Have general conversations and answer questions
2. Help with business tasks when needed

IMPORTANT INSTRUCTIONS:
- For general questions, greetings, casual chat: Answer naturally and helpfully
- If the user asks about BUSINESS matters (income, expenses, customers, reports): 
  Respond with ONLY this JSON: {{"business_intent": "needs_business_processing", "original_query": "user's exact message"}}
- For personal advice unrelated to business: Politely decline and redirect to business help

Examples:
User: "Hi, how are you?" → "Hello! I'm doing well, thank you. I'm here to help with your motor repair business or answer any questions you have. How can I assist you today?"

User: "What is photosynthesis?" → "Photosynthesis is the process by which plants convert sunlight, carbon dioxide, and water into glucose and oxygen..."

User: "Income 1500 from Ram" → {{"business_intent": "needs_business_processing", "original_query": "Income 1500 from Ram"}}

User: "How much did I earn today?" → {{"business_intent": "needs_business_processing", "original_query": "How much did I earn today?"}}

Current Date: {current_date}

User message: {user_message}

Your response:
"""

# Business command parser (when business intent is detected)
BUSINESS_COMMAND_PARSER_PROMPT = """
You are an AI assistant for an Indian motor repair technician. Convert business requests into structured JSON commands.
You must understand Indian English, mixed Hindi-English (Hinglish), and common technician terms.

CRITICAL INSTRUCTIONS:
1. Your output MUST be a valid JSON object with "intent" and "payload" keys.
2. Intents: 'transaction', 'update_transaction', 'database_query', 'delete_transactions', 'generate_report'
3. For amounts, convert rupees to paise (multiply by 100).
4. Standardize details (e.g., "motar winding" → "Motor rewinding").
5. Use conversation history for context.

Example Payloads:
- Transaction: {{"type": "income"|"expense", "amount_paise": int, "customer": str|null, "details": str}}
- Query: {{"customer_name": str, "type": "income"|"expense", "date_from": "YYYY-MM-DD", "details_keyword": str}}
- Delete: {{"delete_scope": "today"}}
- Report: {{"period": "today"|"monthly"|"all_time"}}

Conversation History:
{history}

Latest user message: {user_message}

Your JSON response:
"""

# Data summarizer for business queries
DATA_SUMMARIZER_PROMPT = """
You are a business assistant summarizing data for a technician.
Convert JSON data into clear, natural language. Use Rupees (amount_paise / 100).

User's Question: {user_question}
Database Results: {db_results_json}

Your natural language summary:
"""

# Intelligence layer for insights
INTELLIGENCE_LAYER_PROMPT = """
You are a proactive business advisor. Review the answer and add helpful insights if possible.
Look for patterns, repeat customers, trends, or actionable suggestions.

Original Question: {user_question}
Base Answer: {base_answer}
Conversation History: {history}

Your enhanced response (or return base answer if no insights to add):
"""

# --- Core LLM Functions ---

def call_llm(system_prompt: str, user_message: str, expect_json: bool = False) -> Dict | str:
    """Call Ollama LLM with error handling."""
    if not OLLAMA_AVAILABLE:
        return {"error": "Ollama is not available. Please install and run the Ollama service."}

    try:
        response = client.chat(
            model=MODEL_NAME,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_message}
            ],
            options={'temperature': 0.1 if expect_json else 0.3}
        )
        content = response['message']['content'].strip()
        
        # Try to parse as JSON if we expect it or if it looks like JSON
        if expect_json or (content.startswith('{') and content.endswith('}')):
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                if expect_json:
                    return {"error": f"Expected JSON but got: {content}"}
        
        return content
        
    except Exception as e:
        print(f"[Ollama Error]: {e}")
        return {"error": f"Failed to communicate with AI model: {str(e)}"}


def process_user_message(history: List[Dict]) -> Dict:
    """
    Main processing function: Let LLM handle everything, intercept business intents.
    """
    user_message = history[-1]['content']
    
    # Quick pre-check: if it clearly looks like business, go straight to business processing
    if looks_like_business_query(user_message):
        return parse_business_command(history)
    
    # Let the main LLM handle it
    prompt = get_general_llm_prompt(user_message)
    
    llm_response = call_llm(prompt, user_message)
    
    if isinstance(llm_response, dict):
        # Check for errors
        if llm_response.get("error"):
            return {"intent": "error", "payload": llm_response["error"]}
        
        # Check if LLM detected business intent
        if llm_response.get("business_intent") == "needs_business_processing":
            # Process as business command
            return parse_business_command(history)
        
        # If it's a dict but not business intent, something unexpected happened
        return {"intent": "error", "payload": "Unexpected response format from AI"}
    
    # Normal text response from LLM - map to the right intent for app.py
    # Check what type of response this is
    response_lower = llm_response.lower()
    
    if any(greeting in response_lower for greeting in ['hello', 'hi', 'namaste', 'good morning']):
        return {"intent": "greeting", "payload": llm_response}
    elif '?' in user_message or any(word in user_message.lower() for word in ['help', 'what', 'how']):
        return {"intent": "question", "payload": llm_response}
    else:
        return {"intent": "general_response", "payload": llm_response}


def parse_business_command(history: List[Dict]) -> Dict:
    """Parse business commands using dedicated business prompt."""
    user_message = history[-1]['content']
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
    
    prompt = BUSINESS_COMMAND_PARSER_PROMPT.format(
        history=history_str,
        user_message=user_message
    )
    
    result = call_llm(prompt, user_message, expect_json=True)
    
    if isinstance(result, dict) and result.get("error"):
        return {"intent": "error", "payload": result["error"]}
    
    if isinstance(result, dict) and "intent" in result:
        return result
    
    return {"intent": "error", "payload": f"Could not parse business command: {result}"}


def formulate_and_enhance_answer(user_question: str, db_results_json: str, history: List[Dict]) -> Dict:
    """Generate and enhance answers for business queries."""
    
    # Step 1: Summarize the data
    summarizer_prompt = DATA_SUMMARIZER_PROMPT.format(
        user_question=user_question,
        db_results_json=db_results_json
    )
    
    base_answer = call_llm(summarizer_prompt, user_question)
    
    if isinstance(base_answer, dict) and base_answer.get("error"):
        return {"intent": "error", "payload": base_answer["error"]}
    
    # Step 2: Add intelligence layer
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
    intelligence_prompt = INTELLIGENCE_LAYER_PROMPT.format(
        user_question=user_question,
        base_answer=base_answer,
        history=history_str
    )
    
    final_answer = call_llm(intelligence_prompt, user_question)
    
    if isinstance(final_answer, dict) and final_answer.get("error"):
        # Fallback to base answer if intelligence layer fails
        return {"intent": "answer", "payload": base_answer}
    
    return {"intent": "answer", "payload": final_answer}


# --- Main Orchestrator ---

def main():
    """Main function to handle input and route tasks."""
    try:
        input_data = json.loads(sys.stdin.read().strip())
        task = input_data.get('task', 'parse_command')
        history = input_data.get('history', [])
        context = input_data.get('context', {})
        
        if task == 'parse_command':
            if not history or history[-1].get('role') != 'user':
                result = {'intent': 'error', 'payload': 'No user message found in history.'}
            else:
                result = process_user_message(history)
        
        elif task == 'formulate_answer_from_data':
            user_question = context.get('user_question', '')
            db_results_json = context.get('db_results', '[]')
            result = formulate_and_enhance_answer(user_question, db_results_json, history)
        
        else:
            result = {'intent': 'error', 'payload': f'Unknown task: {task}'}
        
        print(json.dumps(result, ensure_ascii=False))
    
    except json.JSONDecodeError:
        print(json.dumps({'intent': 'error', 'payload': 'Invalid JSON input.'}))
    except Exception as e:
        print(json.dumps({'intent': 'error', 'payload': f'Unexpected error: {str(e)}'}))


if __name__ == '__main__':
    main()