import sys
import json
import requests
from typing import Dict, List
from datetime import datetime

# --- Configuration ---
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
SIMPLE_GREETINGS = ["hi", "hello", "namaste", "namaskar", "hey"]

# --- Prompts for Gemini API ---

QUERY_CLASSIFIER_PROMPT = f"""
You are a master query router for a technician's business assistant. Your only job is to classify the user's request into one of three categories based on their latest message.
Your response MUST be a single JSON object with a key "category" and one of the following three values: 'business_related', 'general_knowledge', 'personal'.

- 'business_related': Anything about income, expenses, reports, customers, job details, business analytics.
- 'general_knowledge': Questions about facts, people, places, or anything not related to the user's business. Examples: "Who is the PM of India?".
- 'personal': Casual chat, personal advice, or conversations not related to business or general knowledge. Example: "How was your day?".

Current Date: {datetime.now().strftime('%Y-%m-%d')}
"""

BUSINESS_COMMAND_PARSER_PROMPT = """
You are an AI assistant for an Indian motor repair technician. Your task is to convert the user's business-related request into a structured JSON command.
You must understand Indian English, mixed Hindi-English (Hinglish), and common technician terms.

CRITICAL INSTRUCTIONS:
1.  Your output MUST be a valid JSON object with "intent" and "payload" keys.
2.  Intents can be: 'transaction', 'update_transaction', 'database_query', 'delete_transactions'.
3.  For amounts, always convert rupees to paise (multiply by 100).
4.  Standardize details (e.g., "motar winding" becomes "Motor rewinding").
5.  Use conversation history for context, especially for updates like "no, it was 500".
6. For "delete todays data", the intent is 'delete_transactions' and payload is {"delete_scope": "today"}.
"""

DATA_SUMMARIZER_PROMPT = """
You are an AI assistant summarizing business data for a technician.
Convert the provided JSON data from the database into a clear, concise, and friendly natural language response.
Always use Rupees (amount_paise / 100). Start the summary directly without conversational filler.
"""

# --- Core Gemini API Interaction ---

def call_gemini_api(api_key: str, system_prompt: str, history: List[Dict]) -> Dict:
    """Calls the Gemini API with a system prompt and conversation history."""
    headers = {'Content-Type': 'application/json'}
    url = f"{GEMINI_API_URL}?key={api_key}"

    # Convert history to Gemini's format
    gemini_history = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [{"text": msg["content"]}]})

    payload = {
        "contents": gemini_history,
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        },
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.0
        }
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        response_json = response.json()
        
        content = response_json['candidates'][0]['content']['parts'][0]['text']
        return json.loads(content)
        
    except requests.exceptions.RequestException as e:
        return {'intent': 'error', 'payload': f"Network error: {e}"}
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        # Fallback for non-JSON or malformed responses
        try:
            # Attempt to extract raw text if JSON parsing fails
            raw_text = response_json.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'No content found.')
            return {'intent': 'error', 'payload': f"AI response was not valid JSON. Raw text: '{raw_text}'"}
        except:
             return {'intent': 'error', 'payload': f"Could not parse AI response: {e}"}


# --- Main Logic Functions ---

def classify_and_parse_command(api_key: str, history: List[Dict]) -> Dict:
    """Classify the query, then parse it if it's business-related."""
    
    # Step 1: Classify the user's intent
    classification_result = call_gemini_api(api_key, QUERY_CLASSIFIER_PROMPT, history)
    category = classification_result.get("category")

    # Step 2: Act based on classification
    if category == 'personal':
        return {
            "intent": "personal_response",
            "payload": "Namaste! I am your business assistant. I can help with transactions and reports."
        }
    elif category == 'general_knowledge':
        # For this version, we will politely decline web search
        return {
            "intent": "general_response",
            "payload": "That's an interesting question, but my function is to assist with your business records."
        }
    elif category == 'business_related':
        # Parse the business command into structured JSON
        return call_gemini_api(api_key, BUSINESS_COMMAND_PARSER_PROMPT, history)
    else:
        return {
            "intent": "error",
            "payload": f"Could not classify request. Model returned: {classification_result.get('error') or category}"
        }

def formulate_answer_from_data(api_key: str, user_question: str, db_results_json: str, history: List[Dict]) -> Dict:
    """Summarize DB data into a natural language answer."""
    # Combine the database results with the user's question for context
    prompt_with_data = f"User Question: {user_question}\n\nDatabase Results:\n{db_results_json}"
    
    # We create a new history for this specific task to not confuse the model
    summarization_history = history + [{'role': 'user', 'content': prompt_with_data}]
    
    # Call Gemini API to summarize
    api_response = call_gemini_api(api_key, DATA_SUMMARIZER_PROMPT, summarization_history)
    
    # The API is expected to return a JSON with a 'summary' key
    summary_text = api_response.get('summary', 'Could not generate a summary.')

    return {"intent": "answer", "payload": summary_text}


# --- Main Orchestrator ---

def main():
    """Main function to read input, route tasks, and print JSON output."""
    try:
        input_data = json.loads(sys.stdin.read().strip())
        task = input_data.get('task', 'parse_command')
        history = input_data.get('history', [])
        context = input_data.get('context', {})
        api_key = input_data.get('api_key')

        if not api_key:
            result = {'intent': 'error', 'payload': 'Gemini API key is missing.'}
            print(json.dumps(result, ensure_ascii=False))
            return

        # --- Rule-Based Greeting Layer ---
        user_message = history[-1]['content'].lower().strip()
        if task == 'parse_command' and user_message in SIMPLE_GREETINGS:
            result = {'intent': 'greeting', 'payload': 'Namaste! How can I help with your business today?'}
            print(json.dumps(result, ensure_ascii=False))
            return
            
        # --- Task Routing ---
        if task == 'parse_command':
            result = classify_and_parse_command(api_key, history)
        elif task == 'formulate_answer_from_data':
            user_question = context.get('user_question', '')
            db_results_json = context.get('db_results', '[]')
            result = formulate_answer_from_data(api_key, user_question, db_results_json, history)
        else:
            result = {'intent': 'error', 'payload': f'Unknown task: {task}'}
        
        print(json.dumps(result, ensure_ascii=False))
    
    except Exception as e:
        error_result = {'intent': 'error', 'payload': f'Critical error in AI worker: {str(e)}'}
        print(json.dumps(error_result, ensure_ascii=False))

if __name__ == '__main__':
    main()
