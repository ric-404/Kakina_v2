"""Client that sends real HTTP/JSON requests to FastAPI.

The CLI does not edit the JSON data file directly.
"""
import httpx

BASE_URL = "http://127.0.0.1:8765"

class ApiError(Exception):
    pass


class ApiClient:
    def __init__(self):
        self.http = httpx.Client(base_url=BASE_URL, timeout=12)

    def call(self, method, path, payload=None, params=None):
        try:
            response = self.http.request(method, path, json=payload, params=params)
        except httpx.RequestError as exc:
            raise ApiError("Cannot connect to the local FastAPI server.") from exc
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            if isinstance(detail, list):
                detail = "; ".join(
                    "/".join(map(str, item.get("loc", []))) + ": " + item.get("msg", "Invalid value")
                    for item in detail
                )
            raise ApiError(f"{detail} (HTTP {response.status_code})")
        return response.json() if response.content else None

