import os
import sys
import json
from pathlib import Path
import datetime
import numpy as np
import pandas as pd
from .get_env import ENV_PATH
from .get_access_token import access_token
from .get_client import client
from .get_trans import get_trans
from .get_order_items import get_order_items

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)
pd.set_option('display.width', None)
pd.set_option('display.expand_frame_repr', False)

# ── JUPYTER WIDGETS ──
try:
    import ipywidgets as widgets
    from IPython.display import display, HTML
    IN_JUPYTER = True
except ImportError:
    IN_JUPYTER = False

# output = widgets.Output()
output = None
container_widget = None

_output_displayed = False

def _get_output():
    global output
    if output is None:
        output = widgets.Output()
    global _output_displayed
    if not _output_displayed:
        try:
            display(output)
        except Exception:
            pass
        _output_displayed = True
    return output

def save_dates_to_env(start_date, end_date, env_path=ENV_PATH):
    """
    Overwrites ORDER_START_DATE and ORDER_END_DATE
    while preserving file formatting and blank lines.
    """

    global output

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
    output = _get_output()
    with output:
        print("➡ Date range advanced by 7 days.")
    # print(f"✅ Saved next date range: {start_date} → {end_date}")

# ── SHOW DATE WIDGET ──
def show_date_widget_and_run():
    global output
    output = _get_output()
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
    display(container)

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


# ── FETCH AND PROCESS DATA ──
def fetch_and_process_data(access_token=None, start_date=None, end_date=None):
    global client
    global output
    output = _get_output()

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

    data = []
    start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    current = start

    while current <= end:
        next_day = current + datetime.timedelta(days=1)

        data.extend(
            get_trans(
                access_token,
                current.strftime("%Y-%m-%d"),
                current.strftime("%Y-%m-%d")
            )
        )

        current = next_day
    df = pd.DataFrame(data)

    ordNos = df['order_no'].unique()
    # bad api change , previously it was string and it was better
    ordNos = [int(ordNo) for ordNo in ordNos]
    # Fetch order info
    order_item_info = {}
    # for order_id in ordNos:
    #     order_items = get_order_items(order_id)
    orders_items = []
    with output:
        for j in range(0, len(ordNos), 10):
            batch = ordNos[j:j+10]
            # print(batch)
            orders_items += get_order_items(
                batch, 
                access_token,
                # output
            )

    with output:
        print("Fetched", len(orders_items), "orders")  
    order_items = [
        item 
        for ordr in orders_items 
        for item in ordr["order_items"]
    ]
    # with output:
    #     print("Fetched", len(order_items), "order items")  
        # print("first order item: ", order_items[0])
    if True:
        for itemDoc in order_items:
            order_item = str(itemDoc.get("order_item_id", None))
            if order_item:
                order_item_info[order_item] = {
                    "created_at": itemDoc["created_at"],
                    "retail_price": itemDoc.get("item_price", 0.00),
                    "voucher": itemDoc.get("voucher_seller", 0.00),
                }
            # with output:
            #     print("order item:", order_item, order_item_info[order_item])

    with output:
        print(len(order_item_info), "order item info")
        # print("first order item info: ", list(order_item_info.keys())[0], list(order_item_info.values())[0] )

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
    # output.clear_output(wait=True)
    with output:
        print("✅ Fetch successful.")

    return new_df


def display_df(token, start_date, end_date):
    global access_token
    global output
    output = _get_output()

    access_token = token
    new_df = fetch_and_process_data(access_token, start_date, end_date)

    # Step 4: replace running message with success
    # output.clear_output(wait=True)
    with output:
        print("for:", start_date, "→", end_date)
        display(new_df)
        # return new_df

def save_csv(token, start_date, end_date):
    global access_token
    global output
    out = _get_output()

    access_token = token
    new_df = fetch_and_process_data(access_token, start_date, end_date)

    new_df.to_csv(f"./{start_date}_{end_date}.csv", index=False)

    # Step 4: replace running message with success
    # output.clear_output(wait=True)
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
        # get_access_token(callback=after_token)
        after_token(access_token)
    else:
        fetch_and_process_data(access_token)


# ── EXECUTE ──
if __name__ == "__main__":
    main()
