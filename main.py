import os
import sys
from pathlib import Path

# Add relative path to daraz_iop
sys.path.insert(0, str(Path(__file__).parent / "daraz_iop"))

import iop
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("DARAZ_BASE_URL", "https://api.daraz.com.bd")
appkey = os.getenv("DARAZ_APP_KEY")
appSecret = os.getenv("DARAZ_APP_SECRET")
access_token = os.getenv("DARAZ_ACCESS_TOKEN")

# Example usage
client = iop.IopClient(url, appkey, appSecret)
request = iop.IopRequest('/finance/transaction/details/get', 'GET')

request.add_api_param('offset', '0')
request.add_api_param('trans_type', '-1')
request.add_api_param('trade_order_id', '123123213213')
request.add_api_param('limit', '100')
request.add_api_param('start_time', '2021-01-01')
request.add_api_param('end_time', '2021-01-05')
request.add_api_param('trade_order_line_id', '45645674566')

response = client.execute(request, access_token)

print(response.type)
print(response.body)