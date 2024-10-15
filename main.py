from flask import Flask, request, jsonify, render_template
# from l402.client import requests
# from l402.client.preimage_provider import AlbyAPI
# from l402.client.credentials import SqliteCredentialsService
import os
import logging
import requests
from requests import RequestException
from cosette import *
from ant.core import *


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
    headers = {"Authorization": f"Bearer {os.getenv('ALBY_TOKEN')}"}
    response = requests.get("https://api.getalby.com/balance", headers=headers)
    response.raise_for_status()
    balance_data = response.json()
    return balance_data.get('balance', 0)

def pchoice(r): print(r.choices[0]) # this function will print the choices made by the agent

@app.route("/ask", methods=["POST"])
def ask():
    global history  # Add this line
    data = request.json
    question = data.get("question")

    if not question:
        return jsonify({"error": "Missing question"}), 400

    try:
        # Fetch initial balance
        initial_balance = get_wallet_balance()
        # Initialize Cosette Chat
        sp = """You are a helpful assistant that can add new tools to help users accomplish actions and get information. 
        When a user provides an L402 URI, you should add it as a tool right away. If you do not have any tools, say so if the user asks."""
        model = "gpt-4o"
        chat = Chat(model, sp=sp, tools=tools)
        chat.h = history

        print("Received question:", question)
        # Use Cosette's Chat with tool loop, including the conversation history
        response = chat.toolloop(question, trace_func=pchoice)

        # Update the conversation history
        history = chat.h

        # Fetch final balance
        final_balance = get_wallet_balance()

        # Calculate the difference
        balance_difference = initial_balance - final_balance

        return jsonify({
            "answer": response.choices[0].message.content,
            "initial_balance": initial_balance,
            "final_balance": final_balance,
            "balance_difference": balance_difference
        })
    except Exception as e:
        logging.error(f"Error in ask: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/get_balance", methods=["GET"])
def get_balance():
    try:
        balance_sats = get_wallet_balance()
        app.logger.info(f"Successfully fetched balance: {balance_sats} sats")
        return jsonify({"balance": balance_sats})
    except RequestException as e:
        app.logger.error(f"Error fetching balance: {str(e)}")
        return jsonify({"error": "An error occurred while fetching the balance"}), 500

if __name__ == "__main__":
    tools.append(add_l402_tool)
    app.run(host="0.0.0.0", port=5000, threaded=False)
