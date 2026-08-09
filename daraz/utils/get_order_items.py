from .iop.python.iop import IopRequest
from .get_client import client
import json
from .dual_print import dual_print, IN_JUPYTER

# def get_order_items(order_id):
#     request = iop.IopRequest('/order/items/get', 'GET')
#     request.add_api_param('order_id', order_id)
def get_order_items(
    order_ids, 
    access_token,
    output=None
):
    request = IopRequest('/orders/items/get', 'GET')
    request.add_api_param('order_ids', order_ids)
    response = client.execute(request, access_token)
    try:
        dicty = json.loads(response.body)
        # if output:
        #     with output:
        #         print(order_ids, dicty)
        if 'data' not in dicty:
            dual_print("data not in order_items", dicty, output=output)
            return None
        return dicty["data"]
    except Exception as e:
        dual_print(e, output=output)
        return None