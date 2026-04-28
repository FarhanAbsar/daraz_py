from .iop.python.iop import IopRequest
from .get_client import client
import json

def get_order(
    order_id,
    access_token
):
    request = IopRequest('/order/get', 'GET')
    request.add_api_param('order_id', order_id)
    response = client.execute(request, access_token)
    return json.loads(response.body)["data"]