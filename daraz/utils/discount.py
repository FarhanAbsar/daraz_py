import os
import sys
import json
from pathlib import Path
import datetime
import numpy as np
import pandas as pd
import asyncio
from .get_env import ENV_PATH, refresh_env
from .get_access_token import access_token, get_access_token
from .get_client import client
from .get_trans import get_trans
from .get_order_items import get_order_items
from .dual_print import dual_print, IN_JUPYTER, _get_output
import logging
import sys
import traceback
import asyncio

def global_exception_handler(exc_type, exc_value, exc_tb):
    """Catches standard uncaught exceptions at any depth."""
    err = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    dual_print(f"\n🔥 CRITICAL ERROR AT TOP LEVEL:\n{err}", output=output)

# Override Python's default error hook
sys.excepthook = global_exception_handler


def async_exception_handler(loop, context):
    """Catches unhandled errors inside asyncio background tasks."""
    exc = context.get("exception")
    if exc:
        err = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    else:
        err = context.get("message", "Unknown async error")
    dual_print(f"\n🔥 CRITICAL ASYNC ERROR:\n{err}", output=output)


def catch_errors(func):
    """Decorator to stop ipywidgets from swallowing callback exceptions."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            err = traceback.format_exc()
            dual_print(f"\n🔥 ERROR INSIDE {func.__name__}:\n{err}", output=output)
            raise
    return wrapper
logging.basicConfig(level=logging.ERROR)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)
pd.set_option('display.width', None)
pd.set_option('display.expand_frame_repr', False)

# ── JUPYTER WIDGETS ──
try:
    import ipywidgets as widgets
    from IPython.display import display, HTML, clear_output
    IN_JUPYTER = True
except ImportError:
    IN_JUPYTER = False

output = None
# out_area = widgets.Output()
# output = None

# def log_to_jupyter(message):
#     """Helper to ensure prints are visible inside Jupyter out_area."""
#     if IN_JUPYTER:
#         with out_area:
#             print(message)
#     else:
#         dual_print(message)


# # output = widgets.Output()
# output = None
# container_widget = None

# _output_displayed = False

# def _get_output():
#     global output
#     if output is None:
#         output = widgets.Output()
#     global _output_displayed
#     if not _output_displayed:
#         try:
#             display(output)
#         except Exception:
#             pass
#         _output_displayed = True
#     return output

def save_dates_to_env(start_date, end_date, env_path=ENV_PATH, output=None):
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
    # output = _get_output()
    # with output:
    dual_print("➡ Date range advanced by 7 days.", output=output)
    # print(f"✅ Saved next date range: {start_date} → {end_date}")

def get_next_date_range(current_start,current_end):
    next_start = current_start + datetime.timedelta(days=7)
    next_end = current_end + datetime.timedelta(days=7)

    return next_start.strftime("%Y-%m-%d"), next_end.strftime("%Y-%m-%d")

def after_current_date_range_set(current_start, current_end, output=None):
    next_start, next_end = get_next_date_range(current_start, current_end)
    save_dates_to_env(next_start, next_end, output=output)  # ✅ Already strings
    return next_start, next_end

def is_valid_date(date_text):
    try:
        datetime.datetime.strptime(date_text, "%Y-%m-%d")  # ✅
        return True
    except (ValueError, TypeError):
        return False

def get_date_range():
    current_start_from_env = os.getenv("ORDER_START_DATE", "2021-01-01")
    current_start = input(f"Enter start date (YYYY-MM-DD):\nDefault: {current_start_from_env}: ")
    current_start_set = is_valid_date(current_start)
    if not current_start_set:
        dual_print(f"Invalid date format. Using default start date: {current_start_from_env}")
        current_start = current_start_from_env
    current_end_from_env = os.getenv("ORDER_END_DATE", datetime.datetime.now().strftime("%Y-%m-%d"))
    current_end = input(f"Enter end date (YYYY-MM-DD):\nDefault: {current_end_from_env}:")
    current_end_set = is_valid_date(current_end)
    if not current_end_set:
        dual_print(f"Invalid date format. Using default end date: {current_end}")
        current_end = current_end_from_env

    after_current_date_range_set(start_picker.value, end_picker.value, output=output)

    return current_start, current_end

start_picker = widgets.DatePicker(
    description="Start Date",
    # value=datetime.datetime.strptime(current_start, "%Y-%m-%d").date()
)

end_picker = widgets.DatePicker(
    description="End Date",
    # value=datetime.datetime.strptime(current_end, "%Y-%m-%d").date()
)

def set_next_value_in_picker(picker, current_value, output=None):
    try:
        if isinstance(current_value, str):
            current_value = datetime.datetime.strptime(current_value, "%Y-%m-%d").date()
        next_value = current_value + datetime.timedelta(days=6)
        picker.value = next_value
    except Exception as e:
        dual_print(f"Error in set_next_value_in_picker: {e}", output=output)


async def get_date_range_from_widget(output=None):
    # Bind future directly to active loop (fixes nest_asyncio deadlock)
    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    # event = asyncio.Event()
    # global output
    # output = _get_output()
    global container_widget

    current_start = os.getenv("ORDER_START_DATE", "2021-01-01")
    current_end = os.getenv("ORDER_END_DATE", datetime.datetime.now().strftime("%Y-%m-%d"))

    global start_picker
    global end_picker
    # with output:
    #     clear_output(wait=True)

    start_picker.value = datetime.datetime.strptime(current_start, "%Y-%m-%d").date()

    end_picker.value = datetime.datetime.strptime(current_end, "%Y-%m-%d").date()

    run_button = widgets.Button(
        description="Fetch Data",
        button_style="primary"
    )

    container = widgets.VBox([start_picker, end_picker, run_button])
    with output:
    # if True:
        display(container)

    container_widget = container
    
    selected_dates = {}
    @catch_errors  # 👈 THIS PREVENTS IPYWIDGETS FROM SWALLOWING THE TRACEBACK
    def on_run(b):
        try:
        #     selected_dates["start"] = start_picker.value.strftime("%Y-%m-%d")
        #     selected_dates["end"] = end_picker.value.strftime("%Y-%m-%d")
        #     after_current_date_range_set(start_picker.value, end_picker.value, output=output)
        #     container.close()
        # except Exception as e:
        #     dual_print(f"Error handling date selection: {e}")
        #     selected_dates["start"] = current_start
        #     selected_dates["end"] = current_end
        # finally:
        #     dual_print("before event.set()", output=output)
        #     event.set()  # ✅ Always unblocks await event.wait()
        #     dual_print("after event.set()", output=output)
            start_val = start_picker.value.strftime("%Y-%m-%d")
            end_val = end_picker.value.strftime("%Y-%m-%d")
            after_current_date_range_set(start_picker.value, end_picker.value, output=output)
            run_button.disabled = True
            run_button.description = "Fetching..."
            
            if not fut.done():
                # dual_print("before fut.set_result()", output=output)
                fut.set_result((start_val, end_val))
                # loop.call_soon(lambda: None)
                # dual_print("after fut.set_result()", output=output)
        except Exception as e:
            dual_print(f"Error handling date selection: {e}", output=output)
            if not fut.done():
                fut.set_result((current_start, current_end))
                # loop.call_soon(lambda: None)
        # return start_date, end_date

    run_button.on_click(on_run)

    # await event.wait()

    # dual_print("after event.wait()", output=output)

    # return selected_dates['start'], selected_dates['end']
    # Await the future directly
    # start_date, end_date = await fut.result()
    # Poll with asyncio.sleep to keep the loop selector awake
    while not fut.done():
        await asyncio.sleep(0.05)

    start_date, end_date = fut.result()
    # dual_print(f"after await fut", output=output)
    # Close container AFTER future completes (prevents destroying context during callback execution)
    container.close()
    
    return start_date, end_date

# ── SHOW DATE WIDGET ──

# ── FETCH AND PROCESS DATA ──
def fetch_and_process_data(access_token=None, start_date=None, end_date=None, output=None):
    global client
    # global output
    # output = _get_output()

    # with output:
    dual_print(f"⏳ Running fetch for: {start_date} → {end_date}", output=output)

    if not access_token:
        # with output:
        dual_print("No access token available!", output=output)
        return None

    try:
        # dual_print("Access token in fetch_and_process_data:", access_token)


        if not start_date:
            start_date = os.getenv("ORDER_START_DATE", "2021-01-01")

        if not end_date:
            end_date = os.getenv("ORDER_END_DATE",
                                datetime.datetime.now().strftime("%Y-%m-%d"))

        # dual_print("Fetching data from", start_date, "to", end_date)

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
                    current.strftime("%Y-%m-%d"),
                    output=output
                )
            )

            current = next_day
    except Exception as e:
        # with output:
        dual_print(f"Failed to fetch transactions: {e}", output=output)
        return None


    try:
        df = pd.DataFrame(data)

        if df.empty:
            # with output:
            dual_print("No data fetched.", output=output)
            return None

        # df['reference'] = df['reference'].astype(str).str.replace(r'\.0$', '', regex=True)
        # df['order_no'] = df['order_no'].astype(str).str.replace(r'\.0$', '', regex=True)
        ordNos = df['order_no'].unique()
        # bad api change , previously it was string and it was better
        ordNos = [int(ordNo) for ordNo in ordNos]
        # Fetch order info
        order_item_info = {}
        # for order_id in ordNos:
        #     order_items = get_order_items(order_id)
        orders_items = []

        # with output:
        for j in range(0, len(ordNos), 10):
            batch = ordNos[j:j+10]
            # dual_print(batch)
            orders_items += get_order_items(
                batch, 
                access_token,
                output=output
            )

        # with output:
        dual_print(f"Fetched {len(orders_items)} orders", output=output)  
        order_items = [
            item 
            for ordr in orders_items 
            for item in ordr["order_items"]
        ]
        # with output:
        # dual_print(f"with {len(order_items)} order items", output=output)  
        # dual_print("first order item: ", order_items[0])
        if True:
            for itemDoc in order_items:
                order_item = str(itemDoc.get("order_item_id", None))
                if order_item:
                    order_item_info[order_item] = {
                        "created_at": itemDoc["created_at"],
                        "retail_price": itemDoc.get("item_price", 0.00),
                        "voucher": itemDoc.get("voucher_seller", 0.00),
                    }
                # # with output:
                # dual_print("order item:", order_item, order_item_info[order_item])


    # with output:
        dual_print(f"{len(order_item_info)} order item info", output=output)
        # dual_print("first order item info: ", list(order_item_info.keys())[0], list(order_item_info.values())[0] )

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
            lambda x: order_item_info.get(x, {}).get("created_at", "")
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
        # with output:
        dual_print("✅ Fetch successful.", output=output)
    except Exception as e:
        # with output:
        dual_print(f"Failed to fetch order items: {e}", output=output)
        return None

    return new_df

def display_df(token, start_date, end_date, new_df=None, output=None):
    global access_token
    # global output
    # output = _get_output()

    access_token = token if token is not None else access_token
    if new_df is None:
        if start_date is None or end_date is None:
            if IN_JUPYTER:
                # start_date, end_date = await get_date_range_from_widget()
                dual_print("Please select a date range.", output=output)
                return None
            else:
                start_date, end_date = get_date_range()
        new_df = fetch_and_process_data(access_token, start_date, end_date, output=output)

    # Step 4: replace running message with success
    # output.clear_output(wait=True)
    dual_print(f"for: {start_date} → {end_date}", output=output)
    # with output:
# Direct output to output widget if in Jupyter
    if IN_JUPYTER:
        with output:
            # output.clear_output()
            if new_df is not None:
                display(new_df)
            else:
                dual_print("No data to display.", output=output)
    else:
        # print(new_df)
        # with output:
        dual_print(new_df, output=output)

def save_csv(token, start_date, end_date, output=None):
    global access_token
    # global output
    # out = _get_output()

    access_token = token
    new_df = fetch_and_process_data(access_token, start_date, end_date)

    new_df.to_csv(f"./{start_date}_{end_date}.csv", index=False)

    # Step 4: replace running message with success
    # output.clear_output(wait=True)
    # with output:
    dual_print(f"📁 CSV saved for: {start_date}, → {end_date}", output=output)


# ── MAIN ──
async def main():
# Attach handler to current event loop
    global output
    output = _get_output()
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(async_exception_handler)
    global access_token
    refresh_env()
    if IN_JUPYTER:
        display(output)
        access_token = await get_access_token(output=output)
        # get_access_token(callback=after_token)
        # if output is None:
        #     output = _get_output()
        # with output:
        # # with _get_output():
        #     clear_output(wait=True)
        #     display(output)
        # after_token(access_token)
        # dual_print("Please select a date range.", output=output)
        start_date, end_date = await get_date_range_from_widget(output)
        try:
            # dual_print(f"Before setting next date", output=output)
            set_next_value_in_picker(start_picker, start_date, output=output)
            set_next_value_in_picker(end_picker, end_date, output=output)
        except Exception as e:
            dual_print(e, output=output)
    else:
        access_token = await get_access_token(output=output)
        # fetch_and_process_data(access_token)
        start_date, end_date = get_date_range(output=output)
    try:
        # dual_print(f"For getting data", output=output)
        new_df = fetch_and_process_data(access_token, start_date, end_date, output=output)
        # dual_print(f"For displaying data", output=output)
        display_df(access_token, start_date, end_date, new_df, output=output)
    except Exception as e:
        dual_print(e, output=output)


# ── EXECUTE ──
if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    
    # Use asyncio.run() inside .py files instead of top-level await
    asyncio.run(main())