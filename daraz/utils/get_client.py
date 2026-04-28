from .iop.python.iop import IopClient
from .get_env import url, appkey, appSecret

client = IopClient(url, appkey, appSecret)