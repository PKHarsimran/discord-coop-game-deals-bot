from __future__ import annotations

from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def build_session(retries: int = 3, backoff_factor: float = 0.5) -> requests.Session:
    retry = Retry(
        total=retries,
        connect=retries,
        read=retries,
        status=retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "POST"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def get_json(
    url: str,
    *,
    params: Optional[Dict[str, str]] = None,
    timeout: int = 20,
    session: Optional[requests.Session] = None,
) -> Any:
    s = session or build_session()
    r = s.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()
