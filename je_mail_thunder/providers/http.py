"""
The HTTPS client of the providers that talk to a web API, with the standard library.

Only ``https`` URLs are requested. A response with an error status is returned like any other, so the provider
decides what it means; only a request that got no response at all raises.
"""
import json
import urllib.error
import urllib.request
from typing import Any, Callable, Mapping, Optional, Tuple

from je_mail_thunder.utils.exception.exceptions import MailThunderConnectionException, MailThunderProviderException

REQUEST_TIMEOUT_SECONDS = 60.0
# A response larger than this is not a mail API answer worth reading into memory (attachments come one by one).
MAX_RESPONSE_BYTES = 64 * 1024 * 1024
Response = Tuple[int, bytes]
Transport = Callable[[str, str, Mapping[str, str], Optional[bytes]], Response]


def https_request(method: str, url: str, headers: Mapping[str, str], body: Optional[bytes] = None) -> Response:
    """
    Send one HTTPS request.

    :param method: ``GET``, ``POST``, ``PATCH``, ``PUT`` or ``DELETE``
    :param url: an ``https`` URL
    :param headers: the request headers
    :param body: the request body
    :return: the status and the response body, also for an error status
    :raises MailThunderProviderException: the URL is not ``https``
    :raises MailThunderConnectionException: the server could not be reached or did not answer
    """
    if not url.startswith("https://"):
        raise MailThunderProviderException("a mail API is only requested over https")
    request = urllib.request.Request(url, data=body, method=method, headers=dict(headers))
    try:
        # https only, checked above
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:  # nosec B310
            return response.status, response.read(MAX_RESPONSE_BYTES)
    except urllib.error.HTTPError as error:
        return error.code, error.read(MAX_RESPONSE_BYTES)
    except OSError as error:
        raise MailThunderConnectionException(
            f"the mail API could not be reached: {type(error).__name__}") from error


def decode_json(body: bytes) -> Any:
    """
    :param body: a response body
    :return: the JSON value it holds, or ``{}`` when it is empty or not JSON
    """
    if not body:
        return {}
    try:
        return json.loads(body.decode("utf-8"))
    except ValueError:
        return {}
