import io
import logging
import mimetypes
import os
import time
import urllib.parse
from datetime import datetime
from typing import Any, Dict, Mapping, Optional, Tuple, Union

import hashlib
import hmac
import requests

DEFAULT_CHARSET = "UTF-8"
_DEFAULT_CONNECT_TIMEOUT_MS = 15000
_DEFAULT_READ_TIMEOUT_MS = 30000
_DEFAULT_SDK_VERSION = "iop-sdk-java-20181207"
_USER_AGENT = "iop-sdk-python/1.0"
_LOGGER = logging.getLogger("daraz.iop")


class ApiException(Exception):
    def __init__(
        self,
        message: str,
        *,
        original_exception: Optional[Exception] = None,
        response: Optional["IopResponse"] = None,
    ):
        super().__init__(message)
        self.original_exception = original_exception
        self.response = response


class FileItem:
    def __init__(
        self,
        file_name: str,
        *,
        data: Optional[bytes] = None,
        path: Optional[str] = None,
        content_type: Optional[str] = None,
    ):
        if not file_name:
            raise ValueError("File name is required")
        if data is None and path is None:
            raise ValueError("Provide either data or path")
        self.file_name = os.path.basename(file_name)
        self._data = data
        self._path = path
        self._content_type = content_type

    @classmethod
    def from_path(cls, path: str, content_type: Optional[str] = None) -> "FileItem":
        if not path:
            raise ValueError("Path is required")
        return cls(os.path.basename(path), path=path, content_type=content_type)

    @classmethod
    def from_bytes(
        cls, name: str, data: bytes, content_type: Optional[str] = None
    ) -> "FileItem":
        if data is None:
            raise ValueError("Data must not be None")
        return cls(name, data=data, content_type=content_type)

    def open(self):
        if self._data is not None:
            return io.BytesIO(self._data)
        if self._path:
            return open(self._path, "rb")
        raise ValueError("No data available for %s" % self.file_name)

    @property
    def content_type(self) -> str:
        if self._content_type:
            return self._content_type
        guess = mimetypes.guess_type(self.file_name)[0]
        return guess or "application/octet-stream"


def _format_timestamp(value: Optional[Union[int, float, datetime, str]] = None) -> str:
    now_ms = int(time.time() * 1000)

    def enforce_window(candidate: int) -> int:
        if abs(candidate - now_ms) / 1000.0 > 7200:
            return now_ms
        return candidate

    if isinstance(value, datetime):
        millis = int(value.timestamp() * 1000)
    elif isinstance(value, (int, float)):
        numeric = float(value)
        millis = int(numeric if numeric >= 1e12 else numeric * 1000)
    elif isinstance(value, str) and value.isdigit():
        millis = int(value)
    else:
        millis = now_ms

    millis = enforce_window(millis)
    return str(millis)


def _normalize_params(params: Mapping[str, Any]) -> Dict[str, str]:
    normalized: Dict[str, str] = {}
    if not params:
        return normalized
    for key, value in params.items():
        if key is None or value is None:
            continue
        normalized[key] = str(value)
    return normalized


def _build_rest_url(server_url: str, api_name: Optional[str]) -> str:
    if not api_name:
        return server_url
    if server_url.endswith("/") and api_name.startswith("/"):
        return server_url + api_name[1:]
    if not server_url.endswith("/") and not api_name.startswith("/"):
        return server_url + "/" + api_name
    return server_url + api_name


def _build_request_url(base_url: str, *parts: str) -> str:
    if not parts:
        return base_url
    builder = [base_url]
    has_question = "?" in base_url
    append_directly = base_url.endswith("?") or base_url.endswith("&")
    for part in parts:
        if not part:
            continue
        if append_directly:
            builder.append(part)
        else:
            if has_question:
                builder.append("&")
            else:
                builder.append("?")
                has_question = True
            builder.append(part)
        append_directly = False
    return "".join(builder)


class IopRequest:
    def __init__(self, api_name: Optional[str] = None, method: str = "POST"):
        self.api_name = api_name
        self.http_method = method.upper() if method else "POST"
        self.api_params: Dict[str, str] = {}
        self.header_params: Dict[str, str] = {}
        self.file_params: Dict[str, FileItem] = {}
        self.timestamp: Optional[Union[int, float, datetime]] = None

    def add_api_param(self, key: str, value: Any):
        if key and value is not None:
            self.api_params[key] = str(value)

    def add_header_parameter(self, key: str, value: Any):
        
        if key and value is not None:
            self.header_params[key] = str(value)

    def add_api_parameters(self, params: Mapping[str, Any]):
        for key, value in (params or {}).items():
            self.add_api_param(key, value)

    def add_file_parameter(self, name: str, payload: Any):
        if not name:
            raise ValueError("file parameter name is required")
        if isinstance(payload, FileItem):
            item = payload
        elif isinstance(payload, (bytes, bytearray)):
            raise ValueError(
                "Wrap raw bytes in FileItem or pass a tuple (filename, bytes[, mime])"
            )
        elif isinstance(payload, tuple):
            if len(payload) == 2:
                filename, data = payload
                item = FileItem.from_bytes(filename, data)
            elif len(payload) == 3:
                filename, data, mime = payload
                item = FileItem.from_bytes(filename, data, content_type=mime)
            else:
                raise ValueError("file tuple must be (name, data[, mime])")
        elif isinstance(payload, (str, os.PathLike)):
            item = FileItem.from_path(str(payload))
        else:
            raise TypeError("Unsupported file parameter type %s" % type(payload))
        self.file_params[name] = item

    def set_http_method(self, method: str):
        if method:
            self.http_method = method.upper()

    def set_timestamp(self, value: Union[int, float, datetime]):
        self.timestamp = value


class IopResponse:
    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.body = body
        self.type: Optional[str] = None
        self.code: Optional[str] = None
        self.message: Optional[str] = None
        self.request_id: Optional[str] = None

    def is_success(self) -> bool:
        return self.code in (None, "", "0")


class IopClient:
    def __init__(
        self,
        base_url: str,
        app_key: str,
        app_secret: str,
        connect_timeout_ms: int = _DEFAULT_CONNECT_TIMEOUT_MS,
        read_timeout_ms: int = _DEFAULT_READ_TIMEOUT_MS,
    ):
        self.base_url = base_url
        self.app_key = app_key
        self.app_secret = app_secret
        self.connect_timeout_ms = connect_timeout_ms
        self.read_timeout_ms = read_timeout_ms
        self.use_gzip_encoding = True
        self.proxies: Optional[Mapping[str, str]] = None
        self.sdk_version = _DEFAULT_SDK_VERSION
        self.sign_method = "sha256"
        self.log_level = "ERROR"
        self.should_log = False
        self.verify = True
        self._session = requests.Session()

    def set_need_enable_logger(self, value: bool):
        self.should_log = bool(value)

    def set_ignore_ssl_check(self, value: bool):
        self.verify = not bool(value)

    def set_use_gzip_encoding(self, value: bool):
        self.use_gzip_encoding = bool(value)

    def set_connect_timeout(self, timeout_ms: int):
        self.connect_timeout_ms = max(0, int(timeout_ms))

    def set_read_timeout(self, timeout_ms: int):
        self.read_timeout_ms = max(0, int(timeout_ms))

    def set_sign_method(self, method: str):
        if not method or method.lower() != "sha256":
            raise ValueError("Only sha256 sign method is supported in this client")
        self.sign_method = "sha256"

    def set_proxy(self, proxies: Optional[Mapping[str, str]]):
        self.proxies = dict(proxies) if proxies else None

    def set_log_level(self, level: str):
        normalized = (level or "").upper()
        if normalized not in {"DEBUG", "INFO", "ERROR"}:
            raise ValueError("log level must be DEBUG, INFO or ERROR")
        self.log_level = normalized

    def is_debug_enabled(self) -> bool:
        return self.log_level == "DEBUG"

    def is_info_enabled(self) -> bool:
        return self.log_level == "INFO"

    def is_error_enabled(self) -> bool:
        return self.log_level == "ERROR"

    def execute(
        self, request: IopRequest, access_token: Optional[str] = None
    ) -> IopResponse:
        api_name = request.api_name
        if not api_name:
            raise ApiException("api_name must be provided on IopRequest")
        start = time.time()
        api_params = _normalize_params(request.api_params)
        common_params = self._build_common_params(request, access_token)
        sign_value = self._generate_sign(api_name, {**common_params, **api_params})
        common_params["sign"] = sign_value
        common_query = urllib.parse.urlencode(common_params)
        request_url = _build_request_url(
            _build_rest_url(self.base_url, api_name), common_query
        )
        headers = dict(request.header_params)
        headers.setdefault("Accept", "text/xml,text/javascript")
        headers.setdefault("User-Agent", _USER_AGENT)
        if self.use_gzip_encoding:
            headers.setdefault("Accept-Encoding", "gzip")
        timeout = self._timeout_tuple()
        try:
            response = self._dispatch_request(
                request, request_url, api_params, headers, timeout
            )
        except requests.RequestException as exc:
            elapsed = int((time.time() - start) * 1000)
            self._log(api_name, api_params, common_params, elapsed, str(exc), False)
            raise ApiException("IOP request failed", original_exception=exc)
        elapsed = int((time.time() - start) * 1000)
        iop_response = self._parse_response(response)
        if response.status_code >= 400 and response.status_code != 400:
            self._log(
                api_name,
                api_params,
                common_params,
                elapsed,
                iop_response.body or "",
                False,
            )
            raise ApiException(
                f"Received HTTP {response.status_code}", response=iop_response
            )
        success = iop_response.is_success()
        self._log(
            api_name,
            api_params,
            common_params,
            elapsed,
            iop_response.body or "",
            success,
        )
        return iop_response

    def _dispatch_request(
        self,
        request: IopRequest,
        url: str,
        api_params: Mapping[str, str],
        headers: Dict[str, str],
        timeout: Tuple[float, float],
    ) -> requests.Response:
        if request.file_params:
            files, handles = self._prepare_files(request.file_params)
            try:
                return self._session.post(
                    url,
                    headers=headers,
                    data=api_params,
                    files=files,
                    timeout=timeout,
                    proxies=self.proxies,
                    verify=self.verify,
                )
            finally:
                for stream in handles:
                    stream.close()
        if request.http_method == "POST":
            headers.setdefault(
                "Content-Type", "application/x-www-form-urlencoded;charset=UTF-8"
            )
            return self._session.post(
                url,
                headers=headers,
                data=api_params,
                timeout=timeout,
                proxies=self.proxies,
                verify=self.verify,
            )
        return self._session.get(
            url,
            headers=headers,
            params=api_params,
            timeout=timeout,
            proxies=self.proxies,
            verify=self.verify,
        )

    def _prepare_files(
        self, file_params: Mapping[str, FileItem]
    ) -> Tuple[Dict[str, Tuple[str, Any, str]], Tuple[io.IOBase, ...]]:
        handles = []
        files: Dict[str, Tuple[str, Any, str]] = {}
        for name, item in file_params.items():
            stream = item.open()
            handles.append(stream)
            files[name] = (item.file_name, stream, item.content_type)
        return files, tuple(handles)

    def _parse_response(self, response: requests.Response) -> IopResponse:
        payload = IopResponse(response.status_code, response.text or "")
        try:
            data = response.json()
        except ValueError:
            data = None
        if isinstance(data, Mapping):
            payload.type = data.get("type")
            payload.code = data.get("code")
            payload.message = data.get("message")
            payload.request_id = data.get("request_id")
        return payload

    def _generate_sign(
        self, api_name: str, parameters: Mapping[str, str]
    ) -> str:
        builder = [api_name]
        for key in sorted(parameters.keys()):
            if not key:
                continue
            value = parameters[key]
            if value is None:
                continue
            trimmed = value.strip()
            if not trimmed:
                continue
            builder.append(key)
            builder.append(value)
        payload = "".join(builder)
        if self.sign_method.lower() != "sha256":
            raise ApiException("Unsupported sign method %s" % self.sign_method)
        digest = hmac.new(
            self.app_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return digest.upper()

    def _build_common_params(
        self, request: IopRequest, access_token: Optional[str]
    ) -> Dict[str, str]:
        params: Dict[str, str] = {
            "app_key": self.app_key,
            "timestamp": _format_timestamp(request.timestamp),
            "sign_method": self.sign_method,
            "partner_id": self.sdk_version,
        }
        if access_token:
            params["access_token"] = str(access_token)
        if self.is_debug_enabled():
            params["debug"] = "true"
        return params

    def _log(
        self,
        api_name: str,
        api_params: Mapping[str, str],
        common_params: Mapping[str, str],
        elapsed_ms: int,
        message: str,
        success: bool,
    ) -> None:
        if not self.should_log:
            return
        payload = {**common_params, **api_params}
        if not success:
            level = logging.ERROR
        elif self.is_debug_enabled():
            level = logging.DEBUG
        elif self.is_info_enabled():
            level = logging.INFO
        else:
            return
        _LOGGER.log(
            level,
            "%s/%s %s %sms params=%s message=%s",
            self.app_key,
            self.sdk_version,
            api_name,
            elapsed_ms,
            payload,
            message,
        )

    def _timeout_tuple(self) -> Tuple[float, float]:
        return (
            max(0.0, self.connect_timeout_ms / 1000.0),
            max(0.0, self.read_timeout_ms / 1000.0),
        )
