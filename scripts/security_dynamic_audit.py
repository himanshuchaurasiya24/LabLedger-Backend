#!/usr/bin/env python3
"""Dynamic security audit script for LabLedger backend.

Runs runtime checks for:
- auth/login behavior
- cross-tenant authorization boundaries
- admin privilege-escalation protections
- malformed and fuzzed input handling (no 500s)

Exit code is non-zero if any check fails.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / ".env"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from all_urls import (
    API_AUTH_STAFFS,
    API_DIAGNOSIS_BILL,
    API_TOKEN,
    API_TOKEN_REFRESH,
    api_center_detail_by_id,
)


def load_env_file(path: Path) -> None:
    """Load .env without requiring shell `source`.

    Supports lines like:
    KEY=value
    KEY="value with spaces"
    KEY='value with spaces'
    """
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if value.startswith("'") and value.endswith("'") and len(value) >= 2:
            value = value[1:-1]
        elif value.startswith('"') and value.endswith('"') and len(value) >= 2:
            value = value[1:-1]

        os.environ.setdefault(key, value)


def bootstrap_django() -> None:
    load_env_file(ENV_PATH)

    # Ensure test host is accepted for Django test client requests.
    allowed_hosts = os.environ.get("ALLOWED_HOSTS", "")
    if "testserver" not in allowed_hosts:
        os.environ["ALLOWED_HOSTS"] = (
            f"{allowed_hosts},testserver" if allowed_hosts else "testserver"
        )

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "LabLedger.settings")

    import django

    django.setup()


@dataclass
class CheckResult:
    name: str
    passed: bool
    details: str


def run_checks() -> list[CheckResult]:
    from django.contrib.auth import get_user_model
    from rest_framework.test import APIClient

    from center_detail.models import CenterDetail

    User = get_user_model()
    client = APIClient()
    client.raise_request_exception = False

    run_id = str(int(time.time()))[-8:]
    results: list[CheckResult] = []
    created_users = []
    created_centers = []

    def record(name: str, passed: bool, details: str) -> None:
        results.append(CheckResult(name=name, passed=passed, details=details))

    def request(method: str, path: str, **kwargs):
        # secure=True avoids https redirect-only false negatives in prod-like config.
        fn = getattr(client, method.lower())
        return fn(path, secure=True, **kwargs)

    try:
        c1 = CenterDetail.objects.create(
            center_name=f"SecCenterA_{run_id}",
            address="Addr A",
            owner_name="Owner A",
            owner_phone=f"91{run_id}01",
        )
        c2 = CenterDetail.objects.create(
            center_name=f"SecCenterB_{run_id}",
            address="Addr B",
            owner_name="Owner B",
            owner_phone=f"91{run_id}02",
        )
        created_centers.extend([c1, c2])

        u1 = User.objects.create_user(
            username=f"admina{run_id}",
            email=f"admina_{run_id}@example.com",
            password="Passw0rd!23",
            first_name="Admin",
            last_name="A",
            phone_number=f"98{run_id}01",
            address="A",
            center_detail=c1,
            is_admin=True,
        )
        u1.is_staff = True
        u1.save()
        created_users.append(u1)

        u2 = User.objects.create_user(
            username=f"adminb{run_id}",
            email=f"adminb_{run_id}@example.com",
            password="Passw0rd!23",
            first_name="Admin",
            last_name="B",
            phone_number=f"98{run_id}02",
            address="B",
            center_detail=c2,
            is_admin=True,
        )
        u2.is_staff = True
        u2.save()
        created_users.append(u2)

        token_resp = request(
            "post",
            API_TOKEN,
            data={"username": u1.username, "password": "Passw0rd!23"},
            format="json",
        )
        token_data = getattr(token_resp, "data", None)
        if token_resp.status_code == 200 and isinstance(token_data, dict) and token_data.get("access"):
            record("auth_login", True, f"status={token_resp.status_code}")
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_data['access']}")
        else:
            record(
                "auth_login",
                False,
                f"status={token_resp.status_code}, body={token_data}",
            )
            return results

        r = request("get", api_center_detail_by_id(c2.id))
        record(
            "cross_tenant_center_access_blocked",
            r.status_code in (403, 404),
            f"status={r.status_code}",
        )

        new_username = f"staffx{run_id}"
        create_payload = {
            "username": new_username,
            "email": f"staffx_{run_id}@example.com",
            "first_name": "Staff",
            "last_name": "X",
            "phone_number": f"97{run_id}03",
            "address": "X",
            "password": "StrongPass!23",
            "is_admin": True,
        }
        r = request("post", API_AUTH_STAFFS, data=create_payload, format="json")
        if r.status_code == 201:
            created = User.objects.get(username=new_username)
            created_users.append(created)
            ok = created.is_admin is True and created.is_superuser is False
            record(
                "admin_cannot_create_superuser",
                ok,
                (
                    f"status={r.status_code}, is_admin={created.is_admin}, "
                    f"is_superuser={created.is_superuser}"
                ),
            )
        else:
            record(
                "admin_cannot_create_superuser",
                False,
                f"status={r.status_code}, body={getattr(r, 'data', None)}",
            )

        r = client.generic(
            "POST",
            API_TOKEN,
            data='{"username":',
            content_type="application/json",
            secure=True,
        )
        record("fuzz_malformed_json_no_500", r.status_code != 500, f"status={r.status_code}")

        huge_user = "A" * 20000
        r = request(
            "post",
            API_TOKEN,
            data={"username": huge_user, "password": "x"},
            format="json",
        )
        record("fuzz_oversized_input_no_500", r.status_code != 500, f"status={r.status_code}")

        r = request(
            "post",
            API_TOKEN,
            data={"username": "' OR 1=1 --", "password": "x"},
            format="json",
        )
        record(
            "fuzz_sqli_string_no_bypass",
            r.status_code in (400, 401, 403),
            f"status={r.status_code}",
        )

        r = request(
            "post",
            API_TOKEN_REFRESH,
            data={"refresh": "x" * 4096},
            format="json",
        )
        record("fuzz_invalid_refresh_no_500", r.status_code != 500, f"status={r.status_code}")

        # Authenticated endpoint fuzz smoke test (regression for search-field crash).
        r = request("get", f"{API_DIAGNOSIS_BILL}?search=" + ("X" * 12000))
        record("fuzz_endpoint_search_no_500", r.status_code != 500, f"status={r.status_code}")

    finally:
        for u in created_users:
            try:
                u.delete()
            except Exception:
                pass
        for c in created_centers:
            try:
                c.delete()
            except Exception:
                pass

    return results


def main() -> int:
    bootstrap_django()
    results = run_checks()

    print("DYNAMIC_SECURITY_RESULTS_START")
    for item in results:
        state = "PASS" if item.passed else "FAIL"
        print(f"{item.name}|{state}|{item.details}")
    print("DYNAMIC_SECURITY_RESULTS_END")

    failures = [r for r in results if not r.passed]
    summary = {
        "total": len(results),
        "passed": len(results) - len(failures),
        "failed": len(failures),
        "failures": [f.name for f in failures],
    }
    print("SUMMARY_JSON=" + json.dumps(summary))

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
