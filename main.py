from flask import Flask, request, jsonify, render_template
import os
import logging
import requests
from requests import RequestException
from cosette import *
from ant.core import *

HUB_URL = "https://hub-5n97k.ondigitalocean.app"
WALLETS_ENDPOINT = "/v0/wallets"

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

tools = []
history = []

def add_l402_tool(uri: str) -> str:
    """Add a new tool to the agent's toolset."""
    info = get_l402_uri_info(uri)
    r = generate_python_function(info)
    func_code = extract_function_code(contents(r))

    cf = create_func(func_code)
    tools.append(cf)
    return f"tool {cf.__name__} added"

@app.route("/")
def index():
    return render_template("index.html")

def get_wallet_balance():
    API_KEY = os.getenv('HUB_API_TOKEN')

    if not API_KEY:
        logging.error("HUB_API_TOKEN environment variable is not set")
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
    global history
    data = request.json
    question = data.get("question")

    if not question:
        return jsonify({"error": "Missing question"}), 400

    try:
        # Fetch initial balance
        initial_balance, currency = get_wallet_balance()
        # Initialize Cosette Chat
        sp = """You are a helpful assistant that can add new tools to help users accomplish actions and get information. 
        When a user provides an L402 URI, you should add it as a tool right away. If you do not have any tools, say so if the user asks.
        Do not invent data."""
        model = "gpt-4o"
        chat = Chat(model, sp=sp, tools=tools)
        chat.h = history

        logging.info(f"Received question: {question}")
        # Use Cosette's Chat with tool loop, including the conversation history
        response = chat.toolloop(question, trace_func=pchoice)

        # Update the conversation history
        history = chat.h

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
    tools.append(add_l402_tool)
    app.run(host="0.0.0.0", port=5000, threaded=False)
