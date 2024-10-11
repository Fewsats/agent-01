"""Meta Tools for AI agents"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_core.ipynb.

# %% auto 0
__all__ = ['func_generation_sp', 'get_l402_uri_info', 'generate_python_function', 'get_text', 'extract_function_code',
           'create_func', 'add_l402_tool']

# %% ../nbs/00_core.ipynb 2
import requests

# %% ../nbs/00_core.ipynb 4
def get_l402_uri_info(uri: str) -> dict:
    """
   Returns the information of the L402 URI resource.

    Args:
    uri (str): The L402 URI to describe.

    Returns:
    dict: A dictionary containing the description of the L402 URI.
    """
    if not uri.startswith("l402://"):
        raise ValueError("Invalid L402 URI format")
    
    scheme = "http://" if "localhost" in uri else "https://"
    http_url = uri.replace("l402://", scheme, 1)
    
    response = requests.get(http_url)
    response.raise_for_status()
    
    return response.json()

    

# %% ../nbs/00_core.ipynb 7
from cosette import Chat
import json 

func_generation_sp = """You are an AI assistant specialized in creating Python functions based on L402 info inputs. 
When given an L402 info dictionary, your task is to generate a Python function that can access the specified endpoint. 
Follow these guidelines:

1. Create a function name that relates to the resource or action described in the 'name' field making it specific enough to avoid conflicts.
2. Use the 'endpoint' field to determine the URL for the request.
3. Use the 'method' field to determine the HTTP method for the request.
4. Handle any required parameters for the endpoint request by passing them as function params.
5. Write a docstring that includes:
   - A brief description of the function's purpose
   - Parameters with their types and descriptions
   - Return value with its type and description
6. Do not import the requests library. Assume it is available in the global scope.
7. Handle potential errors and exceptions appropriately.
8. Do not handle any authentication or authorization in the function.
9. Return the response from the endpoint.
10. Use L402 request client to send the request and configure exactly like this:

L402 Request configuration:
```
l402_requests.configure(
   preimage_provider=AlbyAPI(api_key=os.getenv("ALBY_TOKEN")),
   credentials_service=SqliteCredentialsService()
)
```

Example input:
```
{'access': {'authentication': {'format': 'L402 {credentials}:{proof_of_payment}',
   'header': 'Authorization',
   'protocol': 'L402'},
  'endpoint': 'https://blockbuster.fewsats.com/video/stream/79c816f77fdc4e66b8cd18ad67537936',
  'method': 'POST'},
 'content_type': 'video',
 'cover_url': 'https://pub-3c55410f5c574362bbaa52948499969e.r2.dev/cover-images/79c816f77fdc4e66b8cd18ad67537936',
 'description': 'Lex Fridman Podcast full episode:    • Andrew Huberman: Focus, Controversy, ',
 'name': 'How to focus and think deeply | Andrew Huberman and Lex Fridman',
 'pricing': [{'amount': 1, 'currency': 'USD'}],
 'version': '1.0'}
```

Example output:
```
from l402.client import requests as l402_requests
from l402.client.preimage_provider import AlbyAPI
from l402.client.credentials import SqliteCredentialsService
import requests
import os

l402_requests.configure(
   preimage_provider=AlbyAPI(api_key=os.getenv("ALBY_TOKEN")),
   credentials_service=SqliteCredentialsService()
)
 def stream_video_huberman() -> dict:
    \"\"\"
    Stream the video of the podcast episode featuring Andrew Huberman and Lex Fridman.

    This function sends a POST request to the specified endpoint.
    Returns:
    - requests.Response: The response object containing the server's response to the request.
    \"\"\"
    endpoint = "https://blockbuster.fewsats.com/video/stream/79c816f77fdc4e66b8cd18ad67537936"
    try:
        response = l402_requests.post(endpoint, headers=headers)
        response.raise_for_status()  # Raise an error for bad responses
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None
```
Your response should be a complete Python function definition, including imports, type hints, docstring, and function body. Only output the function definition, no other text."""


# %% ../nbs/00_core.ipynb 8
def generate_python_function(info: dict) -> str:
   """
   Generates a Python function based on the provided L402 info dictionary.

   Args:
   info (dict): The L402 info dictionary containing the details of the resource.

   Returns:
   str: A Python function definition as a string.
   """
   # we remove authentication because it's handled by the L402 client
   # and it only confuses the LLM
   info['access'].pop('authentication', None)

   chat = Chat('gpt-4o-mini', sp=func_generation_sp)
   return chat(json.dumps(info))


# %% ../nbs/00_core.ipynb 11
def get_text(response):
    return response.choices[0].message.content


# %% ../nbs/00_core.ipynb 13
import re
def extract_function_code(func_code):
    code_pattern = re.compile(r'```python\n(.*?)```', re.DOTALL)
    match = code_pattern.search(func_code)
    return match.group(1).strip() if match else func_code


# %% ../nbs/00_core.ipynb 16
import importlib.util
import re
import os

def create_func(code_string):
    # Ensure the funcs directory exists
    os.makedirs('.funcs', exist_ok=True)

    # Extract Python code from Markdown code blocks if present
    code_pattern = re.compile(r'```python\n(.*?)```', re.DOTALL)
    match = code_pattern.search(code_string)
    extracted_code = match.group(1).strip() if match else code_string

    # Create a temporary file name

    function_name = extracted_code.split('def ')[1].split('(')[0].strip()

    temp_file = f'.funcs/{function_name}.py'

    # Write the code to a temporary file
    with open(temp_file, 'w') as f:
        f.write(extracted_code)

    # Import the function
    spec = importlib.util.spec_from_file_location("temp_module", temp_file)
    temp_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(temp_module)

    # Get the function
    function_name = extracted_code.split('def ')[1].split('(')[0].strip()
    return getattr(temp_module, function_name)



# %% ../nbs/00_core.ipynb 31
def add_l402_tool(uri: str) -> str:
    """Add a new tool to the agent's toolset."""
    info = get_l402_uri_info(uri)
    r = generate_python_function(info)
    func_code = extract_function_code(get_text(r))

    cf = create_func(func_code)
    tools.append(cf)
    return f"tool {cf.__name__} added"