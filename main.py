from flask import Flask, request, jsonify, render_template
from l402.client import requests
from l402.client.preimage_provider import AlbyAPI
from l402.client.credentials import SqliteCredentialsService
import os
import logging
from requests import RequestException
from cosette import Chat, models

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# Initialize the Client with necessary services
requests.configure(
    preimage_provider=AlbyAPI(api_key=os.getenv("ALBY_TOKEN")),
    credentials_service=SqliteCredentialsService()
)



def scrape_webpage(url: str) -> dict:
    """
    Scrapes a webpage and returns its content in markdown format.

    url: The URL of the webpage to scrape.
    return: A dictionary containing the scraped content and metadata.
    """
    print(f"Scraping webpage: {url}")
    headers = {"Content-Type": "application/json"}
    data = {"url": url, "formats": ["markdown"]}
    endpoint_url = "https://api.fewsats.com/v0/gateway/access/6cfbcb2a-2cb7-4ee4-978b-6ea9202b71a3"
    response = requests.post(url=endpoint_url, json=data, headers=headers)
    response.raise_for_status()
    return response.json()

@app.route("/")
def index():
    return render_template("index.html")

def get_wallet_balance():
    headers = {"Authorization": f"Bearer {os.getenv('ALBY_TOKEN')}"}
    response = requests.get("https://api.getalby.com/balance", headers=headers)
    response.raise_for_status()
    balance_data = response.json()
    return balance_data.get('balance', 0)

@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    question = data.get("question")

    if not question:
        return jsonify({"error": "Missing question"}), 400

    try:
        # Fetch initial balance
        initial_balance = get_wallet_balance()
        # Initialize Cosette Chat
        sp = """You are a helpful assistant that can scrape URLs provided by the user to answer questions.
                Do not try to guess URLs to scrape. Only scrape URLs that are literally included in the conversation."""
        model = "gpt-4o"
        chat = Chat(model, sp=sp, tools=[scrape_webpage])

        # Use Cosette's Chat with tool loop
        response = chat.toolloop(question)

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
    app.run(host="0.0.0.0", port=5000, threaded=False)