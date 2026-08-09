from .iop.python.iop import IopRequest
from .get_client import client
from .dual_print import dual_print, IN_JUPYTER
import json

def get_trans(access_token,start_date, end_date, order_id=None, line_id=None, output=None):
    # global client
    # global access_token
    request = IopRequest('/finance/transaction/details/get', 'GET')
    request.add_api_param('start_time', start_date)
    request.add_api_param('end_time', end_date)
    if order_id:
        request.add_api_param('trade_order_id', order_id)
    if line_id:
        request.add_api_param('trade_order_line_id', line_id)
    response = client.execute(request, access_token)
    try:
        dicty = json.loads(response.body)
        if 'data' not in dicty:
            dual_print("data not in trans", dicty, output=output)
            return None
        return dicty["data"]
    except Exception as e:
        dual_print(e, output=output)
        return None