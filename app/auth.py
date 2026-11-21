import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from aiohttp import web

from . import config


def verify_init_data(init_data: str, max_age: int = 86400) -> dict:
    """Validate Telegram Mini App initData (HMAC-SHA256) and return the user dict."""
    try:
        data = dict(parse_qsl(init_data, keep_blank_values=True))
        got = data.pop("hash")
        check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
        secret = hmac.new(b"WebAppData", config.BOT_TOKEN.encode(), hashlib.sha256).digest()
        calc = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calc, got) or time.time() - int(data["auth_date"]) > max_age:
            raise ValueError("bad signature or expired")
        return json.loads(data["user"])
    except Exception:
        raise web.HTTPUnauthorized(text="invalid initData")
