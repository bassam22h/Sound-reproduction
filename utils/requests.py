import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# إعداد اتصالات requests محسنة
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504]
)
adapter = HTTPAdapter(
    max_retries=retry_strategy,
    pool_connections=10,
    pool_maxsize=10
)
session.mount("https://", adapter)
session.mount("http://", adapter)

# إضافة headers افتراضية إذا لزم الأمر
session.headers.update({
    'User-Agent': 'VoiceCloneBot/1.0',
    'Accept-Encoding': 'gzip, deflate'
})
