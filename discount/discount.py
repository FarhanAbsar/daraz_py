import os
import sys
import json
from pathlib import Path
import datetime
import numpy as np
import pandas as pd
from dotenv import load_dotenv

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)
pd.set_option('display.width', None)
pd.set_option('display.expand_frame_repr', False)

# ── BASE DIR ──
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.extend([
    str(BASE_DIR / "iop" / "python"),
    str(BASE_DIR / "sdk" / "python")
])

import iop
from lazop import LazopClient, LazopRequest

# ── JUPYTER WIDGETS ──
try:
    import ipywidgets as widgets
    from IPython.display import display, HTML
    IN_JUPYTER = True
except ImportError:
    IN_JUPYTER = False

output = widgets.Output()
container_widget = None

# ── ENV LOAD ──
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

url = os.getenv("DARAZ_BASE_URL", "https://api.daraz.com.bd/rest")
appkey = os.getenv("DARAZ_APP_KEY")
appSecret = os.getenv("DARAZ_APP_SECRET")
authUrl = os.getenv("DARAZ_AUTH_URL")

client = iop.IopClient(url, appkey, appSecret)
access_token = os.getenv("DARAZ_ACCESS_TOKEN")

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


def save_dates_to_env(start_date, end_date, env_path=ENV_PATH):
    """
    Overwrites ORDER_START_DATE and ORDER_END_DATE
    while preserving file formatting and blank lines.
    """

    # global output

    if not os.path.exists(env_path):
        return

    with open(env_path, "r") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        if line.startswith("ORDER_START_DATE="):
            continue
        if line.startswith("ORDER_END_DATE="):
            continue
        new_lines.append(line)

    if new_lines and not new_lines[-1].endswith("\n"):
        new_lines[-1] += "\n"

    new_lines.append(f"ORDER_START_DATE={start_date}\n")
    new_lines.append(f"ORDER_END_DATE={end_date}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)

    # Step 1: show running message
    # output.clear_output(wait=True)
    with output:
        print("➡ Date range advanced by 7 days.")
    # print(f"✅ Saved next date range: {start_date} → {end_date}")


# ── TOKEN CHECK ──
def token_works():
    global client
    global access_token
    request = iop.IopRequest('/seller/get', 'GET')
    response = client.execute(request, access_token)
    return "data" in response.body


# ── GET ACCESS TOKEN ──
def get_access_token(callback=None):
    """
    Get Daraz access token.
    In Jupyter, uses widget callback.
    In script, returns token directly.
    """

    global access_token

    if access_token and token_works():
        # print("✅ Access token retrieved:", access_token)
        if callback:
            callback(access_token)
        return access_token  # Important: stop here

    print("❌ Invalid or missing access token")

    def process_auth_code(auth_code):
        global access_token

        print("auth_code in process_auth_code:", auth_code)

        client_obj = LazopClient(url, appkey, appSecret)
        request = LazopRequest("/auth/token/create")
        request.add_api_param("code", auth_code)

        response = client_obj.execute(request)
        access_token = response.body["access_token"]

        # print("✅ Access token retrieved:", access_token)

        save_access_token_to_env(access_token)

        if callback:
            callback(access_token)

        return access_token

    if IN_JUPYTER:
        prompt_for_auth_code(callback=process_auth_code)
    else:
        code = prompt_for_auth_code()
        return process_auth_code(code)


# ── SHOW DATE WIDGET ──
def show_date_widget_and_run():
    # global output
    global container_widget

    current_start = os.getenv("ORDER_START_DATE", "2021-01-01")
    current_end = os.getenv("ORDER_END_DATE", datetime.datetime.now().strftime("%Y-%m-%d"))

    start_picker = widgets.DatePicker(
        description="Start Date",
        value=datetime.datetime.strptime(current_start, "%Y-%m-%d").date()
    )

    end_picker = widgets.DatePicker(
        description="End Date",
        value=datetime.datetime.strptime(current_end, "%Y-%m-%d").date()
    )

    run_button = widgets.Button(
        description="Fetch Data",
        button_style="primary"
    )

    container = widgets.VBox([start_picker, end_picker, run_button])
    display(container, output)

    container_widget = container

    def on_run(b):
        # global output
        global container_widget
        container_widget.close()

        start_date = start_picker.value.strftime("%Y-%m-%d")
        end_date = end_picker.value.strftime("%Y-%m-%d")

        # Step 2: run fetch
        display_df(
        # save_csv(
            access_token, start_date, end_date,
            # output
        )
        # fetch_and_process_data(access_token, start_date, end_date)

        # Step 3: advance dates
        next_start = start_picker.value + datetime.timedelta(days=7)
        next_end = end_picker.value + datetime.timedelta(days=7)

        save_dates_to_env(
            next_start.strftime("%Y-%m-%d"),
            next_end.strftime("%Y-%m-%d"),
            # output
        )

        start_picker.value = next_start
        end_picker.value = next_end


    run_button.on_click(on_run)

def get_order_items(order_id):
    request = iop.IopRequest('/order/items/get', 'GET')
    request.add_api_param('order_id', order_id)
    response = client.execute(request, access_token)
    return json.loads(response.body)["data"]

def get_order(order_id):
    request = iop.IopRequest('/order/get', 'GET')
    request.add_api_param('order_id', order_id)
    response = client.execute(request, access_token)
    return json.loads(response.body)["data"]

def get_trans(access_token,start_date, end_date, order_id=None, line_id=None):
    global client
    # global access_token
    request = iop.IopRequest('/finance/transaction/details/get', 'GET')
    request.add_api_param('start_time', start_date)
    request.add_api_param('end_time', end_date)
    if order_id:
        request.add_api_param('trade_order_id', order_id)
    if line_id:
        request.add_api_param('trade_order_line_id', line_id)
    response = client.execute(request, access_token)
    print(response.body)
    return json.loads(response.body)["data"]

# ── FETCH AND PROCESS DATA ──
def fetch_and_process_data(access_token=None, start_date=None, end_date=None):
    global client
    global output

    # Step 1: show running message
    output.clear_output(wait=True)
    with output:
        print("⏳ Running fetch for:", start_date, "→", end_date)

    if not access_token:
        print("No access token available!")
        return

    print("Access token in fetch_and_process_data:", access_token)


    if not start_date:
        start_date = os.getenv("ORDER_START_DATE", "2021-01-01")

    if not end_date:
        end_date = os.getenv("ORDER_END_DATE",
                             datetime.datetime.now().strftime("%Y-%m-%d"))

    print("Fetching data from", start_date, "to", end_date)

    data = get_trans(access_token, start_date, end_date)
    df = pd.DataFrame(data)

    ordNos = df['order_no'].unique()
    # Fetch order info
    order_item_info = {}
    for order_id in ordNos:
        order_items = get_order_items(order_id)
        for itemDoc in order_items:
            order_item = str(itemDoc.get("order_item_id", None))
            if order_item:
                order_item_info[order_item] = {
                    "created_at": itemDoc["created_at"],
                    "retail_price": itemDoc.get("item_price", 0.00),
                    "voucher": itemDoc.get("voucher_seller", 0.00),
                }

    # Clean amounts
    df['amount'] = pd.to_numeric(
        df['amount'].astype(str).str.replace(',', ''),
        errors='coerce'
    ).fillna(0)

    df['Bill Amt'] = np.where(df['fee_type'] == "13", df['amount'], 0)
    df['Discount Base'] = np.where(df['fee_type'] != "13", df['amount'], 0)

    # new_df = df.groupby('order_no', as_index=False).agg({
    new_df = df.groupby('reference', as_index=False).agg({
        'order_no': 'first',
        'Bill Amt': 'sum',
        'Discount Base': 'sum',
        # 'transaction_date': 'last',
    })

    new_df = new_df.rename(columns={
        'order_no': 'Daraz Bill No.',
        # 'transaction_date': 'Date'
    })

    new_df['Discount Amt'] = new_df['Discount Base'] * -1
    new_df['Payment Amt'] = ''
    new_df['Remarks'] = ''
    new_df['Bill No.'] = ''
    new_df['Date'] = new_df["reference"].apply(
        lambda x: order_item_info[x]["created_at"]
    )

    # Update Bill Amt and Discount Amt using order_item_info
    
    ordItemNos = df['reference'].unique()

    for ordItemNo in ordItemNos:
        if ordItemNo in order_item_info:
            retail_price = order_item_info[ordItemNo]["retail_price"]
            voucher = order_item_info[ordItemNo]["voucher"]
            idx = new_df[new_df['reference'] == ordItemNo].index[0]
            if new_df.loc[idx, 'Bill Amt'] != 0:
                new_df.loc[idx, 'Bill Amt'] = retail_price
                new_df.loc[idx, 'Discount Amt'] += voucher

    new_df['Received Amt'] = new_df['Bill Amt'] - new_df['Discount Amt']
    
    new_df['Bill Amt'] = new_df['Bill Amt'].round(2)
    new_df['Received Amt'] = new_df['Received Amt'].round(2)
    new_df['Discount Amt'] = new_df['Discount Amt'].round(2)

    new_df = new_df.drop(columns=['Discount Base'])

    new_df = new_df[['Date', 'Payment Amt',
                     'Bill No.', 'Daraz Bill No.', 'Bill Amt',
                     'Received Amt', 'Discount Amt', 'Remarks']]

    new_df = new_df.sort_values(
        by=['Date'], ascending=False
    ).reset_index(drop=True)

    # Step 4: replace running message with success
    output.clear_output(wait=True)
    with output:
        print("✅ Fetch successful.")

    return new_df


def display_df(token, start_date, end_date):
    global access_token
    global output
    access_token = token
    new_df = fetch_and_process_data(access_token, start_date, end_date)

    # Step 4: replace running message with success
    output.clear_output(wait=True)
    with output:
        print("for:", start_date, "→", end_date)
        display(new_df)
        # return new_df

def save_csv(token, start_date, end_date):
    global access_token
    global output
    access_token = token
    new_df = fetch_and_process_data(access_token, start_date, end_date)

    new_df.to_csv(f"./{start_date}_{end_date}.csv", index=False)

    # Step 4: replace running message with success
    output.clear_output(wait=True)
    with output:
        print("📁 CSV saved for:", start_date, "→", end_date)


# ── CALLBACK AFTER TOKEN ──
def after_token(token):
    global access_token
    access_token = token

    if IN_JUPYTER:
        show_date_widget_and_run()
    else:
        fetch_and_process_data(access_token)


# ── MAIN ──
def main():
    if IN_JUPYTER:
        get_access_token(callback=after_token)
    else:
        fetch_and_process_data(access_token)


# ── EXECUTE ──
if __name__ == "__main__":
    main()
