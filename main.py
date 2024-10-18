from flask import Flask, request, jsonify, render_template
import os
import logging
import requests
from requests import RequestException
from cosette import *
from ant.core import *
from cachetools import LRUCache
from functools import wraps

HUB_URL = "https://hub-5n97k.ondigitalocean.app"
WALLETS_ENDPOINT = "/v0/wallets"

MAX_ITEMS = 1000
user_history = LRUCache(maxsize=MAX_ITEMS)
user_tools = LRUCache(maxsize=MAX_ITEMS)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'random-static-key')
logging.basicConfig(level=logging.INFO)


def create_session_add_l402_tool(session_id):
    @wraps(add_l402_tool)
    def session_add_l402_tool(uri: str) -> str:
        """Add a new tool to the user's toolset."""
        info = get_l402_uri_info(uri)
        r = generate_python_function(info)
        func_code = extract_function_code(contents(r))

        cf = create_func(func_code)
        # we know the key is there
        user_tools[session_id].append(cf)
        return f"tool {cf.__name__} added"

    return session_add_l402_tool

@app.route("/")
def index():
    return render_template("index.html")

def get_wallet_balance():
    API_KEY = os.getenv('HUB_API_KEY')

    if not API_KEY:
        logging.error("HUB_API_KEY environment variable is not set")
        raise ValueError("API key not found in environment variables")

    headers = {
        "Authorization": f"Token {API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.get(f"{HUB_URL}{WALLETS_ENDPOINT}", headers=headers)
    response.raise_for_status()
    wallets = response.json()
    
    if wallets:
        wallet = wallets[0]
        balance = wallet['balance']
        currency = wallet['currency']
        return balance, currency
    else:
        raise ValueError("No wallets found")


def pchoice(r): 
    logging.info(f"Agent choice: {r.choices[0]}")

@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    question = data.get("question")
    session_id = request.headers.get("Session-ID")

    if not question or not session_id:
        return jsonify({"error": "Missing question or Session-ID"}), 400

    try:
        # Fetch initial balance
        initial_balance, currency = get_wallet_balance()
        
        # Initialize or get user history and tools
        user_history.setdefault(session_id, [])
        user_tools.setdefault(session_id, [])

        
        # Initialize Cosette Chat
        sp = """You are a helpful assistant that can add new tools to help users accomplish actions and get information. 
        When a user provides an L402 URI, you should add it as a tool right away. If you do not have any tools, say so if the user asks.
        Do not invent data."""
        model = "gpt-4o"
        
        if len(user_tools[session_id]) < 1:
            # Create a session-specific add_l402_tool function
            session_add_l402_tool = create_session_add_l402_tool(session_id)
            user_tools[session_id].append(session_add_l402_tool)
     
        
        chat = Chat(model, sp=sp, tools=user_tools[session_id])
        chat.h = user_history[session_id]

        logging.info(f"Received question: {question}")
        # Use Cosette's Chat with tool loop, including the conversation history
        response = chat.toolloop(question, trace_func=pchoice)

        # Update the user history
        user_history[session_id] = chat.h

        # Fetch final balance
        final_balance, _ = get_wallet_balance()

        # Calculate the difference
        balance_difference = initial_balance - final_balance

        return jsonify({
            "answer": response.choices[0].message.content,
            "initial_balance": initial_balance / 100,
            "final_balance": final_balance / 100,
            "balance_difference": balance_difference / 100,
            "currency": currency
        })
    except Exception as e:
        logging.error(f"Error in ask: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/get_balance", methods=["GET"])
def get_balance():
    try:
        balance, currency = get_wallet_balance()
        app.logger.info(f"Successfully fetched balance: {balance/100} {currency}")
        return jsonify({"balance": balance/100, "currency": currency})
    except RequestException as e:
        app.logger.error(f"Error fetching balance: {str(e)}", exc_info=True)
        return jsonify({"error": "An error occurred while fetching the balance"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=False)
