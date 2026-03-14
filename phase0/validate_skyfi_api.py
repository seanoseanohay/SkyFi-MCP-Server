"""
Phase 0 — SkyFi Platform Validation Script
==========================================
Tests SkyFi API connectivity and core endpoint behavior.
Uses openData=true exclusively to guarantee $0 spend.

Usage:
    source ../.venv/bin/activate
    python validate_skyfi_api.py

Saves sample JSON responses to ../samples/
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from shapely import wkt as shapely_wkt

# ── Configuration ────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent
SAMPLES_DIR = ROOT / "samples"
SAMPLES_DIR.mkdir(exist_ok=True)

load_dotenv(ROOT / ".env")

API_KEY = os.environ.get("X_SKYFI_API_KEY", "")
# SkyFi Platform API: docs at https://app.skyfi.com/platform-api/docs
BASE_URL = os.environ.get(
    "SKYFI_API_BASE_URL", "https://app.skyfi.com/platform-api"
).rstrip("/")
PAGE_SIZE = int(os.environ.get("ARCHIVES_PAGE_SIZE", "100"))

# Small WKT AOI — downtown San Francisco (~1.5 km²)
TEST_WKT = (
    "POLYGON(("
    "-122.4194 37.7749,"
    "-122.4094 37.7749,"
    "-122.4094 37.7849,"
    "-122.4194 37.7849,"
    "-122.4194 37.7749"
    "))"
)

# Date range: last 90 days (for archives search)
NOW = datetime.now(timezone.utc)
DATE_TO = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
DATE_FROM = (NOW - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
# Pass-prediction requires window starting ≥24h from now
PASS_FROM = (NOW + timedelta(hours=25)).strftime("%Y-%m-%dT%H:%M:%SZ")
PASS_TO = (NOW + timedelta(days=8)).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Helpers ──────────────────────────────────────────────────────────────────


def headers() -> dict:
    return {
        "X-Skyfi-Api-Key": API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def save_sample(name: str, data: dict | list) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = SAMPLES_DIR / f"{name}_{ts}.json"
    path.write_text(json.dumps(data, indent=2))
    print(f"  💾 Saved → {path.relative_to(ROOT)}")
    return path


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def ok(msg: str) -> None:
    print(f"  ✅ {msg}")


def fail(msg: str) -> None:
    print(f"  ❌ {msg}")


def info(msg: str) -> None:
    print(f"  ℹ  {msg}")


# ── Test 0: Prerequisites ────────────────────────────────────────────────────


def test_prerequisites() -> bool:
    section("Test 0 — Prerequisites")
    passed = True

    if not API_KEY:
        fail("X_SKYFI_API_KEY not set — copy .env.example to .env and fill in your key")
        passed = False
    else:
        ok(f"API key loaded (length={len(API_KEY)}, prefix={API_KEY[:8]}...)")

    info(f"Base URL: {BASE_URL}")
    info(f"Test AOI: {TEST_WKT[:80]}...")

    # Validate WKT with shapely
    try:
        geom = shapely_wkt.loads(TEST_WKT)
        area_deg2 = geom.area
        info(
            f"WKT valid — vertices={len(list(geom.exterior.coords))}, area≈{area_deg2:.6f}°²"
        )
        ok("WKT geometry valid (shapely)")
    except Exception as exc:
        fail(f"WKT invalid: {exc}")
        passed = False

    return passed


# ── Test 1: POST /archives ───────────────────────────────────────────────────


def test_archives() -> dict | None:
    section("Test 1 — POST /archives (imagery search)")
    url = f"{BASE_URL}/archives"
    payload = {
        "aoi": TEST_WKT,
        "openData": True,
        "pageSize": PAGE_SIZE,
        "fromDate": DATE_FROM,
        "toDate": DATE_TO,
    }
    info(f"URL: {url}")
    info(f"Payload keys: {list(payload.keys())}")
    info(f"Date range: {DATE_FROM} → {DATE_TO}")

    try:
        resp = requests.post(url, json=payload, headers=headers(), timeout=30)
    except requests.exceptions.ConnectionError as exc:
        err = str(exc)
        if "resolve" in err.lower() or "nodename" in err.lower():
            fail(
                "DNS failed — host not found. Set SKYFI_API_BASE_URL in .env (see https://app.skyfi.com/platform-api/docs)."
            )
            info(f"Detail: {err[:120]}...")
        else:
            fail(f"Connection failed: {exc}")
        return None
    except requests.exceptions.RequestException as exc:
        fail(f"Request failed: {exc}")
        return None

    info(f"HTTP status: {resp.status_code}")

    if resp.status_code == 401:
        fail("Authentication failed — check X_SKYFI_API_KEY")
        return None
    if resp.status_code == 400:
        fail(f"Bad request: {resp.text[:500]}")
        return None
    if resp.status_code >= 500:
        fail(f"Server error {resp.status_code}: {resp.text[:200]}")
        return None
    if resp.status_code != 200:
        fail(f"Unexpected status {resp.status_code}: {resp.text[:200]}")
        return None

    data = resp.json()
    save_sample("archives", data)

    # Inspect response shape
    results = data.get("results", data.get("archives", data.get("items", [])))
    next_page = data.get("nextPage") or data.get("next_page") or data.get("cursor")
    total = data.get("total") or data.get("totalCount") or len(results)

    ok(f"Response received — total={total}, results on page={len(results)}")

    if next_page:
        ok(f"nextPage token present: {str(next_page)[:40]}...")
    else:
        info("No nextPage token (all results fit on one page, or no results)")

    # Check thumbnailUrls
    thumb_count = 0
    for item in results:
        thumbs = (
            item.get("thumbnailUrls")
            or item.get("thumbnail_urls")
            or item.get("thumbnails", [])
        )
        if thumbs:
            thumb_count += 1
    if results:
        ok(f"thumbnailUrls present in {thumb_count}/{len(results)} results")
    else:
        info("No results returned for this AOI/date range (open data may be limited)")

    # Log first result summary (SkyFi uses captureTimestamp, cloudCoveragePercent)
    if results:
        first = results[0]
        info(f"First result keys: {list(first.keys())[:10]}")
        cloud = (
            first.get("cloudCoveragePercent")
            or first.get("cloudCoverage")
            or first.get("cloud_coverage")
        )
        date = (
            first.get("captureTimestamp")
            or first.get("date")
            or first.get("acquisitionDate")
        )
        info(f"First result — captureTimestamp={date}, cloudCoveragePercent={cloud}")

    return data


# ── Test 2: Pagination ───────────────────────────────────────────────────────


def test_pagination(archives_response: dict | None) -> None:
    section("Test 2 — Pagination (nextPage token)")
    if archives_response is None:
        info("Skipping — no archives response")
        return

    next_page = (
        archives_response.get("nextPage")
        or archives_response.get("next_page")
        or archives_response.get("cursor")
    )

    if not next_page:
        info(
            "No nextPage token in first response — pagination not needed or no more results"
        )
        ok("Pagination field check passed (no token = single page)")
        return

    url = f"{BASE_URL}/archives"
    payload = {
        "aoi": TEST_WKT,
        "openData": True,
        "pageSize": PAGE_SIZE,
        "fromDate": DATE_FROM,
        "toDate": DATE_TO,
        "nextPage": next_page,
    }
    info(f"Fetching page 2 with nextPage token: {str(next_page)[:40]}...")

    try:
        resp = requests.post(url, json=payload, headers=headers(), timeout=30)
    except requests.exceptions.ConnectionError as exc:
        fail(f"Connection failed (check SKYFI_API_BASE_URL): {exc}")
        return
    except requests.exceptions.RequestException as exc:
        fail(f"Pagination request failed: {exc}")
        return

    info(f"HTTP status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        save_sample("archives_page2", data)
        results = data.get("results", data.get("archives", data.get("items", [])))
        next2 = data.get("nextPage") or data.get("next_page") or data.get("cursor")
        ok(f"Page 2 received — results={len(results)}, has_next={bool(next2)}")
    else:
        fail(f"Pagination request returned {resp.status_code}: {resp.text[:200]}")


# ── Test 3: POST /pricing ────────────────────────────────────────────────────


def test_pricing() -> None:
    section("Test 3 — POST /pricing")
    url = f"{BASE_URL}/pricing"
    payload = {
        "aoi": TEST_WKT,
        "openData": True,
    }
    info(f"URL: {url}")

    try:
        resp = requests.post(url, json=payload, headers=headers(), timeout=30)
    except requests.exceptions.ConnectionError as exc:
        fail(f"Connection failed (check SKYFI_API_BASE_URL): {exc}")
        return
    except requests.exceptions.RequestException as exc:
        fail(f"Request failed: {exc}")
        return

    info(f"HTTP status: {resp.status_code}")

    if resp.status_code == 200:
        data = resp.json()
        save_sample("pricing", data)
        ok("Pricing response received")
        info(f"Response keys: {list(data.keys())[:10]}")
        price = (
            data.get("price")
            or data.get("totalPrice")
            or data.get("estimatedPrice")
            or data.get("cost")
        )
        currency = data.get("currency") or data.get("currencyCode", "USD")
        if price is not None:
            ok(f"Price: {price} {currency}")
        else:
            info("Price field not found in top-level keys — inspect sample file")
    elif resp.status_code == 404:
        info(
            "Pricing endpoint returned 404 — may require different payload or not available for open data"
        )
        info(f"Response: {resp.text[:300]}")
    elif resp.status_code == 422:
        info(f"Validation error: {resp.text[:300]}")
    else:
        fail(f"Unexpected status {resp.status_code}: {resp.text[:300]}")


# ── Test 4: POST /feasibility/pass-prediction ────────────────────────────────


def test_pass_prediction() -> None:
    section("Test 4 — POST /feasibility/pass-prediction")
    url = f"{BASE_URL}/feasibility/pass-prediction"
    # API requires time window starting ≥24h from now
    payload = {
        "aoi": TEST_WKT,
        "openData": True,
        "fromDate": PASS_FROM,
        "toDate": PASS_TO,
    }
    info(f"URL: {url}")
    info(f"Date window: {PASS_FROM} → {PASS_TO} (≥24h from now)")

    try:
        resp = requests.post(url, json=payload, headers=headers(), timeout=30)
    except requests.exceptions.ConnectionError as exc:
        fail(f"Connection failed (check SKYFI_API_BASE_URL): {exc}")
        return
    except requests.exceptions.RequestException as exc:
        fail(f"Request failed: {exc}")
        return

    info(f"HTTP status: {resp.status_code}")

    if resp.status_code == 200:
        data = resp.json()
        save_sample("pass_prediction", data)
        ok("Pass prediction response received")
        info(f"Response keys: {list(data.keys())[:10]}")
        passes = (
            data.get("passes") or data.get("predictions") or data.get("results") or []
        )
        if isinstance(passes, list):
            ok(f"Pass count: {len(passes)}")
            if passes:
                info(f"First pass keys: {list(passes[0].keys())[:8]}")
        else:
            info(f"Passes field type: {type(passes)}")
    elif resp.status_code == 404:
        info(
            "Pass prediction returned 404 — endpoint may differ or require satellite/sensor params"
        )
        info(f"Response: {resp.text[:300]}")
    elif resp.status_code == 422:
        info(f"Validation error: {resp.text[:300]}")
    else:
        fail(f"Unexpected status {resp.status_code}: {resp.text[:300]}")


# ── Test 5: POST /notifications (Phase 5 — AOI monitoring) ──────────────────


def test_notifications() -> None:
    """Validate POST /notifications (setup_aoi_monitoring). Requires a reachable webhook URL."""
    section("Test 5 — POST /notifications (Phase 5 AOI monitoring)")
    webhook_url = os.environ.get("SKYFI_WEBHOOK_BASE_URL", "").strip().rstrip("/")
    if not webhook_url:
        info("SKIPPED — set SKYFI_WEBHOOK_BASE_URL to validate.")
        info(
            "Use a public request catcher (e.g. https://webhook.site) to get a unique URL."
        )
        return

    url = f"{BASE_URL}/notifications"
    payload = {
        "aoi": TEST_WKT,
        "webhookUrl": webhook_url,
    }
    info(f"URL: {url}")
    info(f"webhookUrl: {webhook_url[:50]}...")

    try:
        resp = requests.post(url, json=payload, headers=headers(), timeout=30)
    except requests.exceptions.ConnectionError as exc:
        fail(f"Connection failed (check SKYFI_API_BASE_URL): {exc}")
        return
    except requests.exceptions.RequestException as exc:
        fail(f"Request failed: {exc}")
        return

    info(f"HTTP status: {resp.status_code}")

    if resp.status_code in (200, 201, 202):
        data = resp.json() if resp.text else {}
        save_sample("notifications", data)
        ok("Notifications (AOI monitoring) subscription accepted")
        sub_id = (
            data.get("subscriptionId") or data.get("notificationId") or data.get("id")
        )
        if sub_id is not None:
            ok(f"subscription id: {sub_id}")
        else:
            info(f"Response keys: {list(data.keys())[:12]}")
    elif resp.status_code == 400:
        info(f"Bad request — API may expect different body shape: {resp.text[:400]}")
        info("Check SkyFi docs: https://app.skyfi.com/platform-api/docs")
    elif resp.status_code == 404:
        info(
            "Endpoint returned 404 — notifications API may use a different path or method."
        )
        info(f"Response: {resp.text[:300]}")
    elif resp.status_code == 422:
        info(f"Validation error: {resp.text[:400]}")
    else:
        fail(f"Unexpected status {resp.status_code}: {resp.text[:300]}")


# ── Test 6: GET /notifications (list AOI monitors) ─────────────────────────────


def test_get_notifications() -> None:
    """Validate GET /notifications (list_aoi_monitors). Shows what SkyFi returns for this account."""
    section("Test 6 — GET /notifications (list AOI monitors)")
    url = f"{BASE_URL}/notifications"
    info(f"URL: {url}")

    try:
        resp = requests.get(url, headers=headers(), timeout=30)
    except requests.exceptions.ConnectionError as exc:
        fail(f"Connection failed (check SKYFI_API_BASE_URL): {exc}")
        return
    except requests.exceptions.RequestException as exc:
        fail(f"Request failed: {exc}")
        return

    info(f"HTTP status: {resp.status_code}")

    if resp.status_code == 200:
        try:
            data = resp.json() if resp.text else {}
        except Exception:
            data = {}
        save_sample("notifications_list", data)
        # Normalize: accept array or { notifications, subscriptions, data, items, results }
        raw_list = (
            data
            if isinstance(data, list)
            else data.get("notifications")
            or data.get("subscriptions")
            or data.get("data")
            or data.get("items")
            or data.get("results")
            or []
        )
        if not isinstance(raw_list, list):
            raw_list = []
        ok(f"GET /notifications returned {len(raw_list)} item(s)")
        if raw_list:
            first = raw_list[0] if isinstance(raw_list[0], dict) else {}
            info(f"First item keys: {list(first.keys())}")
            # Id field name SkyFi might use
            sub_id = (
                first.get("id")
                or first.get("subscriptionId")
                or first.get("notificationId")
            )
            if sub_id is not None:
                info(f"First subscription id: {sub_id}")
        else:
            info(
                "Empty list — no AOI monitors for this API key, or SkyFi returns only API-created subscriptions."
            )
    elif resp.status_code == 404:
        info(
            "GET /notifications returned 404 — endpoint may not be supported; list_aoi_monitors will use local cache."
        )
        info(f"Response: {resp.text[:200]}")
    elif resp.status_code == 501:
        info(
            "GET /notifications returned 501 — not implemented; list_aoi_monitors will use local cache."
        )
    else:
        info(f"Unexpected status: {resp.status_code} — {resp.text[:300]}")


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    print("\n🛰  SkyFi Platform Validation — Phase 0")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Base URL: {BASE_URL}")
    print("   open data only: True (guaranteed $0 spend)")

    if not test_prerequisites():
        print("\n⚠️  Prerequisites failed — aborting.")
        return 1

    archives_data = test_archives()
    test_pagination(archives_data)
    test_pricing()
    test_pass_prediction()
    test_notifications()
    test_get_notifications()

    section("Summary")
    info(f"Sample files saved to: {SAMPLES_DIR.relative_to(ROOT)}/")
    info("Review samples/*.json for full response structures")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
