import os
from pathlib import Path
from dotenv import load_dotenv
from .sdk.python.lazop import LazopClient, LazopRequest
from .iop.python.iop import IopRequest
from .get_env import url, appkey, appSecret, authUrl, ENV_PATH
from .get_client import client
import asyncio

from .dual_print import dual_print, IN_JUPYTER, _get_output

access_token = None

# ── PROMPT FOR AUTH CODE ──
async def prompt_for_auth_code(callback=None, output=None):
    """
    Shows instructions + widget in Jupyter or input() in script.
    Calls callback(code) when code entered.
    """

    event = asyncio.Event()
    # global output
    global IN_JUPYTER
    # global dual_print
    global authUrl

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
        # output = widgets.Output()

        if output is None:
            output = _get_output()
        with output:
            display(text, button)

        def on_submit(b):
            code = text.value.strip()
            text.disabled = True
            button.disabled = True

            dual_print("✅ Auth code captured:", code, output=output)

            event.set()

            if callback:
                callback(code)

        button.on_click(on_submit)

        await event.wait()

    else:
        dual_print(html_instructions, output=output)
        code = input("Paste the code here: ").strip()
        if callback:
            return callback(code)
    return code


# ── SAVE ACCESS TOKEN ──
def save_access_token_to_env(token, env_path=ENV_PATH, output=None):
    """
    Writes DARAZ_ACCESS_TOKEN=<token> to the .env file.
    Overwrites existing DARAZ_ACCESS_TOKEN if present.
    """
    global dual_print
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

    dual_print(f"✅ Access token saved to {env_path}", output=output)

# ── TOKEN CHECK ──
def token_works(access_token=None, output=None):
    if access_token is None:
        access_token = os.getenv("DARAZ_ACCESS_TOKEN")
    global client
    # global access_token
    request = IopRequest('/seller/get', 'GET')
    try:
        response = client.execute(request, access_token)
        # print("response in token_works:", response.body)
        return "data" in response.body
    except Exception as e:
        dual_print(e, output=output)
        return False


# ── GET ACCESS TOKEN ──
async def get_access_token(callback=None, output=None):
    """
    Get Daraz access token.
    In Jupyter, uses widget callback.
    In script, returns token directly.
    """

    global access_token

    access_token = os.getenv("DARAZ_ACCESS_TOKEN")

    if access_token and token_works(access_token, output=output):
        # print("✅ Access token retrieved:", access_token)
        if callback:
            callback(access_token)
        else:
            return access_token  # Important: stop here

    dual_print("❌ Invalid or missing access token", output=output)

    def process_auth_code(auth_code):
        global access_token

        dual_print(f"auth_code in process_auth_code: {auth_code}", output=output)

        client_obj = LazopClient(url, appkey, appSecret)
        request = LazopRequest("/auth/token/create")
        request.add_api_param("code", auth_code)

        response = client_obj.execute(request)
        # dual_print("response in process_auth_code:", response.body)
        access_token = response.body["access_token"]

        # dual_print("✅ Access token retrieved:", access_token)

        save_access_token_to_env(access_token, output=output)

        if callback:
            callback(access_token)

        return access_token
    if True:
    # if IN_JUPYTER:
    #     prompt_for_auth_code(process_auth_code)
    # else:
        code = await prompt_for_auth_code(output=output)
        dual_print(f"code after prompt_for_auth_code: {code}", output=output)
        access_token = process_auth_code(code)
        dual_print(f"access_token from prompt_for_auth_code: {access_token}", output=output)
        return access_token


# access_token = get_access_token()
