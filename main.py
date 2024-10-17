from flask import Flask, request, jsonify, render_template
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
sats_per_cent = None


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


def get_wallet_balance_sats():
    headers = {"Authorization": f"Bearer {os.getenv('ALBY_TOKEN')}"}
    response = requests.get("https://api.getalby.com/balance", headers=headers)
    response.raise_for_status()
    balance_data = response.json()
    return balance_data.get('balance', 0)


def get_sats_per_cent():
    global sats_per_cent
    if sats_per_cent is None:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        btc_price = data['bitcoin']['usd']
        sats_per_cent = 100_000_000 / (btc_price * 100)  # sats per cent
    return sats_per_cent


def sats_to_usd(sats):
    return sats / (get_sats_per_cent() * 100)


def pchoice(r):
    print(
        r.choices[0])  # this function will print the choices made by the agent


@app.route("/ask", methods=["POST"])
def ask():
    global history
    data = request.json
    question = data.get("question")

    if not question:
        return jsonify({"error": "Missing question"}), 400

    try:
        initial_balance_sats = get_wallet_balance_sats()

        sp = """You are a helpful assistant that can add new tools to help users accomplish actions and get information. 
        When a user provides an L402 URI, you should add it as a tool right away. If you do not have any tools, say so if the user asks.
        Do not invent data."""
        model = "gpt-4o"
        chat = Chat(model, sp=sp, tools=tools)
        chat.h = history

        print("Received question:", question)
        response = chat.toolloop(question, trace_func=pchoice)

        history = chat.h

        final_balance_sats = get_wallet_balance_sats()

        balance_difference_sats = initial_balance_sats - final_balance_sats

        initial_balance_usd = sats_to_usd(initial_balance_sats)
        final_balance_usd = sats_to_usd(final_balance_sats)
        balance_difference_usd = sats_to_usd(balance_difference_sats)

        print({
            "initial_balance": f"${initial_balance_usd:.2f}",
            "initial_balance_sats": initial_balance_sats,
            "final_balance": f"${final_balance_usd:.2f}",
            "final_balance_sats": final_balance_sats,
            "balance_difference": f"{balance_difference_usd:.2f}",
            "balance_difference_sats": balance_difference_sats
        })

        return jsonify({
            "answer": response.choices[0].message.content,
            "initial_balance": f"${initial_balance_usd:.2f}",
            "final_balance": f"${final_balance_usd:.2f}",
            "balance_difference_usd": balance_difference_usd,
            "balance_difference_sats": balance_difference_sats
        })

    except Exception as e:
        logging.error(f"Error in ask: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/get_balance", methods=["GET"])
def get_balance():
    try:
        balance_sats = get_wallet_balance_sats()
        balance_usd = sats_to_usd(balance_sats)
        app.logger.info(f"Successfully fetched balance: ${balance_usd:.2f}")
        return jsonify({"balance": f"${balance_usd:.2f}"})
    except RequestException as e:
        app.logger.error(f"Error fetching balance: {str(e)}")
        return jsonify(
            {"error": "An error occurred while fetching the balance"}), 500


if __name__ == "__main__":
    tools.append(add_l402_tool)
    get_sats_per_cent()  # Initialize the sats per cent when the program starts
    app.run(host="0.0.0.0", port=5000, threaded=False)
