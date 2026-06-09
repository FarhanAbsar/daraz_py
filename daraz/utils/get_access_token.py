import os
from pathlib import Path
from dotenv import load_dotenv
from .sdk.python.lazop import LazopClient, LazopRequest
from .iop.python.iop import IopRequest
from .get_env import url, appkey, appSecret, authUrl, ENV_PATH
from .get_client import client

try:
    import ipywidgets as widgets
    from IPython.display import display, HTML
    IN_JUPYTER = True
except ImportError:
    IN_JUPYTER = False

# ── PROMPT FOR AUTH CODE ──
def prompt_for_auth_code(callback=None):
    """
    Shows instructions + widget in Jupyter or input() in script.
    Calls callback(code) when code entered.
    """

    html_instructions = f"""
    <div style="font-size:14px">
        1️⃣ Click this link and open in your browser:<br>
        <a href="{authUrl}" target="_blank">{authUrl}</a><br><br>
        2️⃣ Login if required and click 'Authorize'<br>
        3️⃣ Copy the value after 'code=' in the redirect URL and paste below.
    </div>
    """

    if IN_JUPYTER:
        display(HTML(html_instructions))

        text = widgets.Text(
            description="Auth code:",
            layout=widgets.Layout(width="65%"),
            placeholder="paste the code from redirect URL",
        )
        button = widgets.Button(description="Submit", button_style="success")
        output = widgets.Output()

        display(text, button, output)

        def on_submit(b):
            code = text.value.strip()
            text.disabled = True
            button.disabled = True

            with output:
                print("✅ Auth code captured:", code)

            if callback:
                callback(code)

        button.on_click(on_submit)

    else:
        print(html_instructions)
        code = input("Paste the code here: ").strip()
        if callback:
            return callback(code)
        return code


# ── SAVE ACCESS TOKEN ──
def save_access_token_to_env(token, env_path=ENV_PATH):
    """
    Writes DARAZ_ACCESS_TOKEN=<token> to the .env file.
    Overwrites existing DARAZ_ACCESS_TOKEN if present.
    """

    lines = []

    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()

    # Remove old token line
    lines = [line for line in lines if not line.startswith("DARAZ_ACCESS_TOKEN=")]

    # Ensure newline before appending
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"

    lines.append(f"DARAZ_ACCESS_TOKEN={token}\n")

    with open(env_path, "w") as f:
        f.writelines(lines)

    print(f"✅ Access token saved to {env_path}")

# ── TOKEN CHECK ──
def token_works(access_token=os.getenv("DARAZ_ACCESS_TOKEN")):
    global client
    # global access_token
    request = IopRequest('/seller/get', 'GET')
    response = client.execute(request, access_token)
    # print("response in token_works:", response.body)
    return "data" in response.body


# ── GET ACCESS TOKEN ──
def get_access_token(callback=None):
    """
    Get Daraz access token.
    In Jupyter, uses widget callback.
    In script, returns token directly.
    """

    # global access_token

    access_token = os.getenv("DARAZ_ACCESS_TOKEN")

    if access_token and token_works(access_token):
        # print("✅ Access token retrieved:", access_token)
        if callback:
            callback(access_token)
        else:
            return access_token  # Important: stop here

    print("❌ Invalid or missing access token")

    def process_auth_code(auth_code):
        global access_token

        print("auth_code in process_auth_code:", auth_code)

        client_obj = LazopClient(url, appkey, appSecret)
        request = LazopRequest("/auth/token/create")
        request.add_api_param("code", auth_code)

        response = client_obj.execute(request)
        # print("response in process_auth_code:", response.body)
        access_token = response.body["access_token"]

        # print("✅ Access token retrieved:", access_token)

        save_access_token_to_env(access_token)

        if callback:
            callback(access_token)

        return access_token
    if IN_JUPYTER:
        prompt_for_auth_code(process_auth_code)
    else:
        code = prompt_for_auth_code()
        print("code after prompt_for_auth_code:", code)
        return process_auth_code(code)


access_token = get_access_token()