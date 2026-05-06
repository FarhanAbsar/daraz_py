from .iop.python.iop import IopRequest
from .get_client import client
import json

# def get_order_items(order_id):
#     request = iop.IopRequest('/order/items/get', 'GET')
#     request.add_api_param('order_id', order_id)
def get_order_items(
    order_ids, 
    access_token,
    # output=None
):
    request = IopRequest('/orders/items/get', 'GET')
    request.add_api_param('order_ids', order_ids)
    response = client.execute(request, access_token)
    dicty = json.loads(response.body)
    # if output:
    #     with output:
    #         print(order_ids, dicty)
    return dicty["data"]