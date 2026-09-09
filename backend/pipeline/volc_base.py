"""火山引擎 visual 服务的共享底座:签名、调用、错误解析。

即梦(jimeng_ti2v_v30_pro)和小云雀(pippit_*)都走 visual.volcengineapi.com,
同一套 OpenAPI v4 签名、同样的 CVSync2AsyncSubmitTask/GetResult 动作,
区别只在 req_key 和 body 参数。这里抽出公共部分。
"""
from __future__ import annotations

import json
from typing import Optional

from volcengine.ApiInfo import ApiInfo
from volcengine.Credentials import Credentials
from volcengine.ServiceInfo import ServiceInfo
from volcengine.base.Service import Service


def make_service(ak: str, sk: str) -> Service:
    """构造一个已设好 AK/SK 的火山 visual 服务客户端。"""
    service_info = ServiceInfo(
        "visual.volcengineapi.com",
        {"Accept": "application/json"},
        Credentials("", "", "cv", "cn-north-1"),
        10,
        60,
        scheme="https",
    )
    api_info = {
        "CVSync2AsyncSubmitTask": ApiInfo(
            "POST", "/",
            {"Action": "CVSync2AsyncSubmitTask", "Version": "2022-08-31"},
            {}, {},
        ),
        "CVSync2AsyncGetResult": ApiInfo(
            "POST", "/",
            {"Action": "CVSync2AsyncGetResult", "Version": "2022-08-31"},
            {}, {},
        ),
    }
    svc = Service(service_info, api_info)
    svc.set_ak(ak)
    svc.set_sk(sk)
    return svc


def call(service: Service, action: str, body: dict, label: str = "火山visual") -> dict:
    """发请求并把响应/异常都解析成 dict。

    火山 SDK 的 Service.json 在 HTTP!=200 时会
    `raise Exception(resp.text.encode("utf-8"))`,把错误体藏在 bytes 里。
    审核失败、权限不足都走这条路径,这里统一捕获并解析成可读报错。
    """
    try:
        raw = service.json(action, {}, json.dumps(body))
        return json.loads(raw)
    except Exception as e:  # noqa: BLE001
        parsed = parse_sdk_error(e)
        if parsed is not None:
            return parsed
        raise RuntimeError(f"{label} {action} 调用异常: {e}") from e


def parse_sdk_error(e: Exception) -> Optional[dict]:
    """把 SDK 抛出的 bytes/str 异常体解析成 dict,失败返回 None。"""
    args = getattr(e, "args", None)
    if not args:
        return None
    payload = args[0]
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8", errors="replace")
    if not isinstance(payload, str):
        return None
    try:
        return json.loads(payload)
    except (ValueError, TypeError):
        return None


def format_error(prefix: str, resp: dict, access_denied_hint: str = "") -> str:
    """把响应体格式化成可读报错。兼容业务错误和火山平台错误两种结构。"""
    # 业务错误结构:{code, message, request_id}
    code = resp.get("code")
    if code is not None:
        msg = resp.get("message", "未知错误")
        rid = resp.get("request_id", "")
        return f"{prefix}(code={code}): {msg}\nrequest_id={rid}"
    # 火山平台错误结构:{ResponseMetadata: {Error: {Code, Message}, RequestId}}
    meta = resp.get("ResponseMetadata", {})
    err = meta.get("Error", {})
    if err:
        ecode = err.get("Code", "")
        emsg = err.get("Message", "")
        rid = meta.get("RequestId", "")
        hint = access_denied_hint if ecode == "AccessDenied" else ""
        return f"{prefix}: [{ecode}] {emsg}\nRequestId={rid}{hint}"
    return f"{prefix}: {resp}"
