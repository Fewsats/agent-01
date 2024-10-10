from flask import Flask, request, jsonify, render_template
from l402.client import requests
from l402.client.preimage_provider import AlbyAPI
from l402.client.credentials import SqliteCredentialsService
import os
import logging
from requests import RequestException
from cosette import Chat

# from tools import get_l402_uri_info, scrape_webpage

# Initialize the Client with necessary services
requests.configure(
    preimage_provider=AlbyAPI(api_key=os.getenv("ALBY_TOKEN")),
    credentials_service=SqliteCredentialsService()
)

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

def get_l402_uri_info(uri: str, return_format: str = "JSON") -> dict:
    """
    Interprets an L402 URI and returns information about the content.

    Args:
    uri (str): The L402 URI to describe.
    return_format (str): The desired return format, either "JSON" or "HTML". Defaults to "JSON".

    Returns:
    str: A dictionary containing the description of the L402 URI either in JSON or HTML format.
    """
    if not uri.startswith("l402://"):
        raise ValueError("Invalid L402 URI format")
    
    http_url = uri.replace("l402://", "https://", 1)
    response = requests.get(http_url)
    response.raise_for_status()
    data = response.json()
    
    data["price"] = int(data["pricing"][0]["amount"]) / 100
    endpoint = data['access']['endpoint']
    method = data['access']['method'].lower()
    name = data.get('name', 'unnamed_l402_function')
    description = data.get('description', 'No description provided')
    # Create a function with a proper name and docstring
    def l402_function():
        """
        {description}

        This function interacts with an L402 endpoint.
        Endpoint: {endpoint}
        Method: {method}

        Returns:
        dict: The JSON response from the endpoint.
        """
        request_func = getattr(requests, method)
        response = request_func(endpoint)
        response.raise_for_status()
        return response.json()

    # Set the function name and docstring
    l402_function.__name__ = name.replace(" ", "_").lower()
    l402_function.__doc__ = l402_function.__doc__.format(
        description=description,
        endpoint=endpoint,
        method=method.upper()
    )

    # # Add the new function to the tools list
    tools.append(l402_function)

    return data

def add_l402_tool(uri: str) -> None:
    """
    Creates a new function based on the L402 URI information and adds it to the tools list.

    Args:
    uri (str): The L402 URI to interpret and create a function from.

    Returns:
    dict: The information of the L402 tool added.
    """
    if not uri.startswith("l402://"):
        raise ValueError("Invalid L402 URI format")
    
    http_url = uri.replace("l402://", "https://", 1)
    response = requests.get(http_url)
    response.raise_for_status()
    data = response.json()

    endpoint = data['access']['endpoint']
    method = data['access']['method'].lower()
    name = data.get('name', 'unnamed_l402_function')
    description = data.get('description', 'No description provided')

    # # Create a function with a proper name and docstring
    # def l402_function(*args, **kwargs):
    #     """
    #     {description}

    #     This function interacts with an L402 endpoint.
    #     Endpoint: {endpoint}
    #     Method: {method}

    #     Args:
    #     *args: Positional arguments to pass to the endpoint.
    #     **kwargs: Keyword arguments to pass to the endpoint.

    #     Returns:
    #     dict: The JSON response from the endpoint.
    #     """
    #     request_func = getattr(requests, method)
    #     response = request_func(endpoint, *args, **kwargs)
    #     response.raise_for_status()
    #     return response.json()

    # # Set the function name and docstring
    # l402_function.__name__ = name.replace(" ", "_").lower()
    # l402_function.__doc__ = l402_function.__doc__.format(
    #     description=description,
    #     endpoint=endpoint,
    #     method=method.upper()
    # )

    # # Add the new function to the tools list
    # tools.append(l402_function)

    return data



tools = [get_l402_uri_info]
# tools = [scrape_webpage, get_l402_uri_info]



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
                Do not try to guess URLs to scrape. Only scrape URLs that are literally included in the conversation.
                When a user provides an L402 URI, return the description of the URI in HTML format without any additional text."""
        model = "gpt-4o"
        chat = Chat(model, sp=sp, tools=tools)
        logging.info(f"Chat initialized with tools: {tools}")

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