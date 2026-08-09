from .iop.python.iop import IopRequest
from .get_client import client
from .dual_print import dual_print, IN_JUPYTER
import json

def get_order(
    order_id,
    access_token,
    output=None
):
    request = IopRequest('/order/get', 'GET')
    request.add_api_param('order_id', order_id)
    response = client.execute(request, access_token)
    try:
        dicty = json.loads(response.body)
        if 'data' not in dicty:
            dual_print("data not in order", dicty, output=output)
            return None
        return dicty["data"]
    except Exception as e:
        dual_print(e, output=output)
        return None