#!/usr/bin/env python3
"""Print Codex usage windows and reset credits."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"
CREDITS_URL = "https://chatgpt.com/backend-api/wham/rate-limit-reset-credits"
AUTH_CLAIM = "https://api.openai.com/auth"
TIMEOUT_SECONDS = 20


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--auth", help="Path to auth.json or a Codex home directory")
    args = parser.parse_args()

    try:
        auth = load_auth(args.auth)
        headers = {
            "Authorization": f"Bearer {auth['access_token']}",
            "originator": "Codex Desktop",
            "OAI-Product-Sku": "CODEX",
            "Accept": "application/json",
        }
        if auth.get("account_id"):
            headers["ChatGPT-Account-Id"] = auth["account_id"]

        usage = fetch_json(USAGE_URL, headers)
        credits = fetch_json(CREDITS_URL, headers)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print_report(auth, usage, credits)
    return 0


def load_auth(path_arg: str | None) -> dict[str, str | None]:
    path = auth_path(path_arg)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"could not find Codex auth at {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"could not read Codex auth at {path}") from exc

    tokens = data.get("tokens")
    if not isinstance(tokens, dict):
        raise RuntimeError(f"{path} does not contain tokens")

    access_token = first(tokens, "access_token", "accessToken")
    if not access_token:
        raise RuntimeError(f"{path} does not contain an access token")

    id_payload = jwt_payload(first(tokens, "id_token", "idToken"))
    access_payload = jwt_payload(access_token)

    return {
        "access_token": access_token,
        "account_id": (
            account_id_from(id_payload)
            or account_id_from(access_payload)
            or first(tokens, "account_id", "accountId")
        ),
        "email": clean(id_payload.get("email")),
        "name": clean(id_payload.get("name")),
    }


def auth_path(path_arg: str | None) -> Path:
    if path_arg:
        path = Path(path_arg).expanduser()
        return path if path.name == "auth.json" else path / "auth.json"
    return Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser() / "auth.json"


def fetch_json(url: str, headers: dict[str, str]) -> dict[str, Any]:
    try:
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read()
            content_type = response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise RuntimeError("saved Codex login was rejected") from exc
        if exc.code == 429:
            retry_after = exc.headers.get("Retry-After")
            detail = f"; retry after {retry_after}s" if retry_after else ""
            raise RuntimeError(f"rate limited{detail}") from exc
        raise RuntimeError(f"{url} returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"request failed for {url}: {exc.reason}") from exc

    if not body:
        raise RuntimeError(f"{url} returned an empty response")
    if content_type and "json" not in content_type.lower():
        raise RuntimeError(f"{url} returned {content_type}, not JSON")

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{url} returned invalid JSON") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"{url} returned non-object JSON")
    return data


def print_report(auth: dict[str, str | None], usage: dict[str, Any], credits: dict[str, Any]) -> None:
    now = datetime.now().astimezone()
    rate_limit = usage.get("rate_limit") if isinstance(usage.get("rate_limit"), dict) else {}

    print("Codex usage")
    print(f"Checked: {fmt_time(now)}")

    print("\nAccount")
    print(f"Email: {clean(usage.get('email')) or auth.get('email') or '-'}")
    if auth.get("name"):
        print(f"Name: {auth['name']}")
    print(f"Account ID: {auth.get('account_id') or clean(usage.get('account_id')) or '-'}")
    print(f"Plan: {fmt_plan(usage.get('plan_type'))}")

    print("\nLimit status")
    print(f"Allowed: {fmt_bool(rate_limit.get('allowed'))}")
    print(f"Limit reached: {fmt_bool(rate_limit.get('limit_reached'))}")

    print("\nUsage windows")
    windows = [
        (label, rate_limit.get(key))
        for label, key in (("5h limit", "primary_window"), ("Weekly limit", "secondary_window"))
        if isinstance(rate_limit.get(key), dict)
    ]
    if not windows:
        print("- none returned")
    for index, (label, window) in enumerate(windows):
        if index:
            print()
        print_window(label, window, now)

    rows = sorted(
        [row for row in credits.get("credits", []) if isinstance(row, dict)],
        key=lambda row: parse_time(row.get("expires_at")) or datetime.max.replace(tzinfo=timezone.utc),
    )
    available = as_int(credits.get("available_count"))
    if available is None:
        available = sum(1 for row in rows if (clean(row.get("status")) or "").lower() == "available")

    print("\nReset credits")
    print(f"Available count: {available}")
    if not rows:
        print("- none returned")
    for index, row in enumerate(rows, 1):
        print()
        print_credit(index, row)


def print_window(label: str, window: dict[str, Any], now: datetime) -> None:
    used = as_int(window.get("used_percent"))
    remaining = None if used is None else max(0, min(100, 100 - used))
    reset_at = reset_time(window, now)
    print(label)
    print(f"  Used: {fmt_percent(used)}")
    print(f"  Remaining: {fmt_percent(remaining)}")
    print(f"  Window seconds: {show(window.get('limit_window_seconds'))}")
    print(f"  Resets in: {duration(window.get('reset_after_seconds'))}")
    print(f"  Resets at: {fmt_time(reset_at)}")


def print_credit(index: int, row: dict[str, Any]) -> None:
    print(f"Credit {index}")
    print(f"  ID: {show(row.get('id'))}")
    print(f"  Title: {show(row.get('title'))}")
    print(f"  Type: {show(row.get('reset_type'))}")
    print(f"  Status: {show(row.get('status'))}")
    print(f"  Granted at: {fmt_time(parse_time(row.get('granted_at')))}")
    print(f"  Expires at: {fmt_time(parse_time(row.get('expires_at')))}")
    if row.get("redeem_started_at"):
        print(f"  Redeem started at: {fmt_time(parse_time(row.get('redeem_started_at')))}")
    if row.get("redeemed_at"):
        print(f"  Redeemed at: {fmt_time(parse_time(row.get('redeemed_at')))}")


def jwt_payload(token: str | None) -> dict[str, Any]:
    if not token:
        return {}
    parts = token.split(".")
    if len(parts) < 2:
        return {}
    try:
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
    except (ValueError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def account_id_from(payload: dict[str, Any]) -> str | None:
    claim = payload.get(AUTH_CLAIM)
    return clean(claim.get("chatgpt_account_id")) if isinstance(claim, dict) else None


def reset_time(window: dict[str, Any], now: datetime) -> datetime | None:
    reset_at = as_float(window.get("reset_at"))
    if reset_at is not None:
        seconds = reset_at / 1000 if reset_at > 10_000_000_000 else reset_at
        return datetime.fromtimestamp(seconds, tz=timezone.utc).astimezone()

    reset_after = as_int(window.get("reset_after_seconds"))
    return now + timedelta(seconds=max(0, reset_after)) if reset_after is not None else None


def parse_time(value: Any) -> datetime | None:
    value = clean(value)
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone()


def first(values: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = clean(values.get(key))
        if value:
            return value
    return None


def clean(value: Any) -> str | None:
    if isinstance(value, (str, int)):
        value = str(value).strip()
        return value or None
    return None


def as_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def show(value: Any) -> str:
    return clean(value) or "-"


def fmt_bool(value: Any) -> str:
    return "true" if value is True else "false" if value is False else "-"


def fmt_percent(value: Any) -> str:
    value = as_int(value)
    return f"{value}%" if value is not None else "-"


def fmt_plan(value: Any) -> str:
    value = clean(value)
    return " ".join(part.capitalize() for part in value.split("_")) if value else "-"


def fmt_time(value: datetime | None) -> str:
    if value is None:
        return "-"
    hour = value.hour % 12 or 12
    ampm = "AM" if value.hour < 12 else "PM"
    return f"{value:%Y-%m-%d} {hour}:{value:%M:%S} {ampm} {value.tzname() or ''}".rstrip()


def duration(value: Any) -> str:
    seconds = as_int(value)
    if seconds is None:
        return "-"
    days, remainder = divmod(max(0, seconds), 86_400)
    hours, remainder = divmod(remainder, 3_600)
    minutes = remainder // 60
    if days:
        return f"{days}d {hours}h" if hours else f"{days}d"
    if hours:
        return f"{hours}h {minutes}m" if minutes else f"{hours}h"
    return f"{max(1, minutes)}m"


if __name__ == "__main__":
    raise SystemExit(main())
