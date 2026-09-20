"""Percorre o assistente de hiring.amazon.com e coleta as vagas filtradas."""

from __future__ import annotations

import os
import random
import re
import time
from typing import Any

import run_progress as progress
from trawl_browser import (
    attach_trawl_init_script,
    kill_extractor_browsers,
    open_camoufox,
)

JOB_SEARCH_URL = "https://hiring.amazon.com/app#/jobSearch"
JOB_ID_RE = re.compile(r"(?:jobId|job-id|jobID)=([^&/#]+)", re.I)
JOB_ID_TOKEN_RE = re.compile(r"JOB-[A-Z]{2}-\d+", re.I)
SKIP_TITLES = {
    "job search",
    "amazon jobs overview",
    "job opportunities",
    "amazon perks",
    "unique opportunities",
    "getting started",
    "skip to content",
    "type: part time",
    "type: full time",
    "duration: regular",
    "duration: seasonal",
    "warning",
    "fraud warning",
    "recommended jobs",
}

_JUNK_TITLE_RE = re.compile(
    r"(skip to content|total\s+\d+\s+jobs?\s+found|jobs that support|type:\s|duration:\s|pay rate:\s|fraud|warning|recommended jobs|want to get alerts|shift available)",
    re.I,
)

_CARD_TEXT_CLICK = (
    r"\d+\s+shifts?\s+available",
    r"fulfillment center warehouse associate",
    r"warehouse associate",
    r"pay rate:",
)


def _pause(low=0.35, high=1.1) -> None:
    time.sleep(random.uniform(low, high))


def _human_type(page, locator, text: str) -> None:
    try:
        locator.click(force=True, timeout=2_500)
    except Exception:
        locator.evaluate("el => { el.focus(); el.click(); }")
    _pause(0.2, 0.5)
    try:
        locator.fill("")
    except Exception:
        locator.evaluate("el => { el.value = ''; el.dispatchEvent(new Event('input', { bubbles: true })); }")
    page.keyboard.type(text, delay=random.randint(45, 130))
    _pause(0.2, 0.45)


def _click_first(page, selectors: list[str]) -> bool:
    for selector in selectors:
        try:
            target = page.locator(selector).first
            if target.count() and target.is_visible():
                target.click(force=True)
                _pause()
                return True
        except Exception:
            continue
    return False


def _is_wizard_close(button) -> bool:
    try:
        blob = " ".join(
            filter(
                None,
                [
                    button.get_attribute("aria-label"),
                    button.get_attribute("title"),
                    button.get_attribute("data-test-id"),
                    button.inner_text(),
                ],
            )
        ).lower()
    except Exception:
        return False
    return "guided" in blob


def _click_overlay_x(page, *, generic: bool = True) -> bool:
    selectors = [
        "button[aria-label='Close site redirect banner']",
        "button[aria-label='Dismiss announcement']",
        "button[aria-label='Close announcement']",
        "[aria-label='Close site redirect banner']",
        "[aria-label='Dismiss announcement']",
    ]
    if generic:
        selectors.extend(
            [
                "[data-test-id*='close' i]",
                "[data-test-component*='Close']",
                "button[aria-label='Close']",
                "[aria-label='Close']",
                "button:has-text('×')",
                "button:has-text('✕')",
            ]
        )
    clicked = False
    for selector in selectors:
        buttons = page.locator(selector)
        try:
            count = min(buttons.count(), 8)
        except Exception:
            continue
        for index in range(count):
            button = buttons.nth(index)
            try:
                if not button.is_visible() or _is_wizard_close(button):
                    continue
                button.click(timeout=2_000)
                clicked = True
                print(f"[warehouse] fechei overlay no X ({selector})", flush=True)
                _pause(0.2, 0.45)
            except Exception:
                try:
                    if _is_wizard_close(button):
                        continue
                    button.evaluate("el => el.click()")
                    clicked = True
                    print(f"[warehouse] fechei overlay no X via JS ({selector})", flush=True)
                    _pause(0.2, 0.45)
                except Exception:
                    continue
    if clicked:
        return True
    try:
        clicked = page.evaluate(
            """() => {
              const isWizard = (el) => {
                const blob = [
                  el.getAttribute('aria-label') || '',
                  el.getAttribute('title') || '',
                  el.getAttribute('data-test-id') || '',
                  el.innerText || '',
                ].join(' ').toLowerCase();
                return blob.includes('guided');
              };
              const isClose = (el) => {
                if (isWizard(el)) return false;
                const label = (el.getAttribute('aria-label') || '').toLowerCase();
                const testId = (el.getAttribute('data-test-id') || '').toLowerCase();
                const text = (el.innerText || '').trim();
                return (
                  label === 'close' ||
                  label.includes('dismiss') ||
                  label.includes('close site') ||
                  label.includes('close announcement') ||
                  testId.includes('close') ||
                  text === '×' ||
                  text === '✕' ||
                  text === 'X'
                );
              };
              const walk = (root) => {
                for (const el of root.querySelectorAll('button, [role="button"], [aria-label], [data-test-id]')) {
                  if (isClose(el)) {
                    el.click();
                    return true;
                  }
                }
                for (const el of root.querySelectorAll('*')) {
                  if ((el.shadowRoot || el.shadowRootUnl) && walk(el.shadowRoot || el.shadowRootUnl)) return true;
                }
                return false;
              };
              return walk(document);
            }"""
        )
    except Exception:
        clicked = False
    if clicked:
        print("[warehouse] fechei overlay no X via shadow DOM", flush=True)
        _pause(0.2, 0.45)
    return bool(clicked)


def _dismiss_overlays(page, *, generic_x: bool = True) -> None:
    _click_first(
        page,
        [
            "button:has-text('I consent')",
            "button:has-text('Accept')",
            "button:has-text('Got it')",
            "button:has-text('Not now')",
            "button:has-text('No thanks')",
            "button:has-text('Continue to United States')",
            "button:has-text('Stay on this page')",
        ],
    )
    _pause(0.35, 0.7)
    for _ in range(6):
        if not _click_overlay_x(page, generic=generic_x):
            break
        _pause(0.25, 0.5)


def _click_label_in_shadow(page, label: str, *, exact: bool = False) -> bool:
    wanted = _normalize_label(label)
    try:
        return bool(
            page.evaluate(
                """({ wanted, exact }) => {
                  const norm = (value) => (value || '').replace(/[^a-z0-9]+/gi, '').toLowerCase();
                  const visible = (el) => {
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return (
                      style.visibility !== 'hidden' &&
                      style.display !== 'none' &&
                      rect.width > 0 &&
                      rect.height > 0
                    );
                  };
                  const matches = [];
                  const walk = (root) => {
                    const nodes = root.querySelectorAll(
                      'button, [role="button"], [role="option"], [role="combobox"], a, [class*="chip"], [class*="Chip"]'
                    );
                    for (const el of nodes) {
                      if (!visible(el)) continue;
                      const raw = el.innerText || el.textContent || el.getAttribute('aria-label') || '';
                      const text = norm(raw);
                      if (text === wanted || (!exact && text.includes(wanted))) {
                        matches.push({ el, len: text.length });
                      }
                    }
                    for (const el of root.querySelectorAll('*')) {
                      if (el.shadowRoot || el.shadowRootUnl) walk(el.shadowRoot || el.shadowRootUnl);
                    }
                  };
                  walk(document);
                  matches.sort((a, b) => a.len - b.len);
                  if (!matches.length) return false;
                  matches[0].el.click();
                  return true;
                }""",
                {"wanted": wanted, "exact": exact},
            )
        )
    except Exception:
        return False


def _wait_wizard(page, pattern: str) -> None:
    try:
        page.locator(f"text=/{pattern}/i").first.wait_for(timeout=10_000)
    except Exception:
        pass
    _pause(0.35, 0.7)


def _wait_after_filter() -> None:
    print("[warehouse] aguardando 3s a lista filtrar", flush=True)
    time.sleep(3)


def _press_next(page) -> bool:
    _wait_after_filter()
    if _click_first(
        page,
        [
            "button:has-text('Next')",
            "button:has-text('Continue')",
            "[data-test-id*='next']",
        ],
    ):
        print("[warehouse] cliquei em Next", flush=True)
        return True
    if _click_label_in_shadow(page, "Next", exact=True):
        print("[warehouse] cliquei em Next via shadow DOM", flush=True)
        _pause()
        return True
    return False


def _press_done(page) -> bool:
    _wait_after_filter()
    clicked = False
    if _click_first(page, ["button:has-text('Done')", "[data-test-id*='done']"]):
        print("[warehouse] cliquei em Done", flush=True)
        clicked = True
    elif _click_label_in_shadow(page, "Done", exact=True):
        print("[warehouse] cliquei em Done via shadow DOM", flush=True)
        clicked = True
    if clicked:
        _wait_after_filter()
    return clicked


def _press_skip(page) -> bool:
    if _click_first(page, ["button:has-text('Skip')", "[data-test-id*='skip']"]):
        print("[warehouse] cliquei em Skip", flush=True)
        return True
    if _click_label_in_shadow(page, "Skip", exact=True):
        print("[warehouse] cliquei em Skip via shadow DOM", flush=True)
        _pause()
        return True
    print("[warehouse] não achei o botão Skip", flush=True)
    return False


def _advance_wizard(page, *, selected: bool, finish: bool = False) -> None:
    _pause(0.4, 0.7)
    if selected:
        if finish and _press_done(page):
            return
        if _press_next(page):
            return
        if finish:
            _press_done(page)
        return
    _press_skip(page)


def _normalize_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _click_chip(page, label: str) -> bool:
    compact = re.sub(r"\s+", "", label)
    if _click_first(
        page,
        [
            f"button.filterScheduleShift:has-text('{label}')",
            f"button:has-text('{label}')",
            f"button:has-text('{compact}')",
            f"[role='button']:has-text('{label}')",
        ],
    ):
        print(f"[warehouse] selecionei chip '{label}'", flush=True)
        return True
    if _click_label_in_shadow(page, label):
        print(f"[warehouse] selecionei chip '{label}' via shadow DOM", flush=True)
        _pause(0.2, 0.5)
        return True
    return False


def _confirm_location_suggestion(page) -> None:
    _pause(0.6, 1.1)
    page.keyboard.press("ArrowDown")
    _pause(0.15, 0.3)
    page.keyboard.press("Enter")
    _pause(0.4, 0.8)


def _fill_guide_zip(page, zip_code: str) -> bool:
    field = page.locator("#zipcode-nav-guide")
    try:
        field.first.wait_for(state="visible", timeout=12_000)
    except Exception:
        try:
            page.locator("text=/home address|step 1\\s*\\/\\s*5|zipcode or city/i").first.wait_for(timeout=4_000)
        except Exception:
            pass
        if field.count() == 0:
            field = page.get_by_placeholder("Enter zipcode or city").last
        if field.count() == 0:
            return False

    _dismiss_overlays(page, generic_x=False)
    _human_type(page, field.first if hasattr(field, "first") else field, zip_code)
    _confirm_location_suggestion(page)
    if not _press_next(page):
        try:
            page.keyboard.press("Enter")
        except Exception:
            pass
    _pause(0.8, 1.6)
    return True


def _fill_search_zip(page, zip_code: str) -> None:
    _dismiss_overlays(page)
    field = page.locator("#zipcode-nav-search")
    try:
        field.first.wait_for(state="visible", timeout=15_000)
    except Exception:
        field = page.get_by_placeholder("Enter zipcode or city").first
        field.wait_for(state="visible", timeout=10_000)

    _dismiss_overlays(page)
    _human_type(page, field, zip_code)
    _confirm_location_suggestion(page)
    page.keyboard.press("Enter")
    _pause(1.5, 2.5)


def _slider_now(locator) -> int | None:
    try:
        raw = locator.get_attribute("aria-valuenow")
        if raw is not None and str(raw).strip() != "":
            return int(float(raw))
    except Exception:
        return None
    return None


def _set_hours_js(page, target: int) -> bool:
    try:
        return bool(
            page.evaluate(
                """(target) => {
                  const sliders = [];
                  const walk = (root) => {
                    for (const el of root.querySelectorAll('[role="slider"], input[type="range"]')) {
                      sliders.push(el);
                    }
                    for (const el of root.querySelectorAll('*')) {
                      if (el.shadowRoot || el.shadowRootUnl) walk(el.shadowRoot || el.shadowRootUnl);
                    }
                  };
                  walk(document);
                  if (!sliders.length) return false;
                  const minEl = sliders[0];
                  const maxEl = sliders[sliders.length - 1];
                  const assign = (el, value) => {
                    el.focus();
                    if ('value' in el) el.value = String(value);
                    el.setAttribute('aria-valuenow', String(value));
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                  };
                  assign(minEl, 0);
                  assign(maxEl, target);
                  return true;
                }""",
                target,
            )
        )
    except Exception:
        return False


def _drag_hours_max(page, target: int) -> bool:
    sliders = page.get_by_role("slider")
    try:
        if sliders.count() < 1:
            return False
        first = sliders.first.bounding_box()
        last = sliders.last.bounding_box()
    except Exception:
        return False
    if not first or not last:
        return False
    left = first["x"] + first["width"] / 2
    right = last["x"] + last["width"] / 2
    y = last["y"] + last["height"] / 2
    if right <= left:
        return False
    dest_x = left + (right - left) * (max(0, min(40, target)) / 40.0)
    try:
        page.mouse.move(right, y)
        page.mouse.down()
        page.mouse.move(dest_x, y, steps=14)
        page.mouse.up()
        _pause(0.2, 0.4)
        return True
    except Exception:
        return False


def _set_hours_max(page, target: int) -> int | None:
    sliders = page.get_by_role("slider")
    try:
        count = sliders.count()
    except Exception:
        count = 0

    if count:
        try:
            sliders.first.focus()
            page.keyboard.press("Home")
            _pause(0.1, 0.2)
            max_slider = sliders.last
            max_slider.focus()
            _pause(0.15, 0.3)
            page.keyboard.press("End")
            _pause(0.1, 0.2)
            for _ in range(40):
                now = _slider_now(max_slider)
                if now is not None and now <= target:
                    return now
                page.keyboard.press("ArrowLeft")
                time.sleep(0.05)
            now = _slider_now(max_slider)
            if now is not None and now <= target:
                return now
        except Exception:
            pass

    _drag_hours_max(page, target)
    _set_hours_js(page, target)
    try:
        if sliders.count():
            return _slider_now(sliders.last)
    except Exception:
        return None
    return None


def _set_hours(page, hours: int | None) -> None:
    _wait_wizard(page, "hours a week|how many hours")
    if hours is None or hours == "":
        if not _press_next(page):
            _press_skip(page)
        return
    target = max(0, min(40, int(hours)))
    now = _set_hours_max(page, target)
    print(f"[warehouse] hours 0-{now if now is not None else '?'} (alvo 0-{target})", flush=True)
    if not _press_next(page):
        print("[warehouse] Next do passo de hours não encontrado", flush=True)


def _select_chips(page, labels: list[str]) -> bool:
    selected = False
    for index, label in enumerate(labels):
        if index:
            _wait_after_filter()
        if _click_chip(page, label):
            selected = True
        else:
            print(f"[warehouse] não achei o chip '{label}'", flush=True)
    return selected


def _select_option(page, label: str) -> bool:
    if _click_first(page, [f"button:has-text('{label}')", f"[role='option']:has-text('{label}')"]):
        print(f"[warehouse] selecionei opção '{label}'", flush=True)
        return True
    if _click_label_in_shadow(page, label):
        print(f"[warehouse] selecionei opção '{label}' via shadow DOM", flush=True)
        return True
    try:
        combo = page.get_by_role("combobox")
        if combo.count() and combo.first.is_visible():
            combo.first.click()
            _pause(0.25, 0.45)
            if _click_first(page, [f"[role='option']:has-text('{label}')", f"text={label}"]):
                print(f"[warehouse] selecionei opção '{label}' no combobox", flush=True)
                return True
            if _click_label_in_shadow(page, label):
                print(f"[warehouse] selecionei opção '{label}' no combobox via shadow", flush=True)
                return True
    except Exception:
        return False
    return False


def _click_when_start_js(page, label: str, *, open_list: bool) -> bool:
    wanted = _normalize_label(label)
    try:
        return bool(
            page.evaluate(
                """({ wanted, openList }) => {
                  const norm = (value) => (value || '').replace(/[^a-z0-9]+/gi, '').toLowerCase();
                  const visible = (el) => {
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return (
                      style.visibility !== 'hidden' &&
                      style.display !== 'none' &&
                      rect.width > 0 &&
                      rect.height > 0
                    );
                  };
                  const blobOf = (el) => [
                    el.getAttribute('placeholder') || '',
                    el.getAttribute('aria-label') || '',
                    el.getAttribute('id') || '',
                    el.className || '',
                    el.innerText || '',
                  ].join(' ').toLowerCase();
                  const isSearch = (el) => /search jobs|job search|zipcode|enter zip/.test(blobOf(el));
                  const isStartValue = (text) =>
                    /assoonaspossible|within\\d+weeks|after\\d+weeks/.test(text);
                  const matches = [];
                  const walk = (root) => {
                    const selector = openList
                      ? '[role="option"], [role="listbox"] li, [role="listbox"] [role="button"]'
                      : '[role="combobox"], button, [aria-haspopup="listbox"]';
                    for (const el of root.querySelectorAll(selector)) {
                      if (!visible(el) || isSearch(el)) continue;
                      const text = norm(el.innerText || el.textContent || el.getAttribute('aria-label'));
                      if (openList) {
                        if (text === wanted || text.includes(wanted)) {
                          matches.push({ el, top: el.getBoundingClientRect().top });
                        }
                      } else if (isStartValue(text)) {
                        matches.push({ el, top: el.getBoundingClientRect().top });
                      }
                    }
                    for (const el of root.querySelectorAll('*')) {
                      if (el.shadowRoot || el.shadowRootUnl) walk(el.shadowRoot || el.shadowRootUnl);
                    }
                  };
                  walk(document);
                  if (!matches.length) return false;
                  matches.sort((a, b) => (openList ? b.top - a.top : a.top - b.top));
                  matches[0].el.click();
                  return true;
                }""",
                {"wanted": wanted, "openList": open_list},
            )
        )
    except Exception:
        return False


def _select_when_start(page, label: str) -> bool:
    opened = _click_first(
        page,
        [
            f"[role='combobox']:has-text('{label}')",
            "[role='combobox']:has-text('As soon as possible')",
            "[role='combobox']:has-text('Within')",
            f"button:has-text('{label}')",
        ],
    )
    if not opened:
        opened = _click_when_start_js(page, label, open_list=False)
    if not opened:
        print("[warehouse] não abri o select de When Start", flush=True)
        return False
    print("[warehouse] cliquei no select de When Start (1/2)", flush=True)
    try:
        page.get_by_role("option").first.wait_for(state="visible", timeout=5_000)
    except Exception:
        _pause(0.7, 1.0)

    selected = _click_first(
        page,
        [
            f"[role='listbox'] [role='option']:has-text('{label}')",
            f"[role='option']:has-text('{label}')",
        ],
    )
    if not selected:
        selected = _click_when_start_js(page, label, open_list=True)
    if not selected:
        print(f"[warehouse] não cliquei a opção '{label}' na lista (2/2)", flush=True)
        return False
    print(f"[warehouse] cliquei '{label}' na lista (2/2)", flush=True)
    _wait_after_filter()
    return True


_STREET_ADDRESS_RE = re.compile(
    r"(?P<line>\d{1,6}\s+[A-Za-z0-9 .#'-]+,\s*(?P<city>[A-Za-z][A-Za-z .'-]+),\s*(?P<state>[A-Z]{2})(?:\s+(?P<zip>\d{5}(?:-\d{4})?))?)"
)
_DOLLAR_RE = re.compile(r"(?:US\s*)?(?:\$|＄)\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)", re.I)
_PAY_RATE_AMOUNT_RE = re.compile(
    r"pay\s*rate\b.{0,80}?(?:US\s*)?(?:\$|＄)\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)",
    re.I | re.S,
)
_PAY_RATE_NUMBER_RE = re.compile(
    r"pay\s*rate\b.{0,80}?(?:up\s*to\s*)?(\d{1,2}\.\d{2})\b",
    re.I | re.S,
)
_DURATION_RE = re.compile(r"duration:?\s*(regular|seasonal)", re.I)
_TYPE_RE = re.compile(
    r"type:?\s*((?:full\s*time|part\s*time|flex(?:\s*time)?)(?:\s*,\s*(?:full\s*time|part\s*time|flex(?:\s*time)?))*)",
    re.I,
)


def _parse_location(raw: str) -> tuple[str, str]:
    street = _STREET_ADDRESS_RE.search(raw or "")
    if street:
        return street.group("city").strip(), street.group("state")
    match = re.search(r"([A-Za-z][A-Za-z .'-]*),\s*([A-Z]{2})\b", raw or "")
    if match:
        return match.group(1).strip(), match.group(2)
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    if len(parts) >= 2:
        return parts[0], parts[-1][:2].upper()
    return raw.strip(), ""


def _looks_like_street(value: str) -> bool:
    return bool(_STREET_ADDRESS_RE.search(value or ""))


def _normalize_salary(raw: str) -> str:
    blob = (raw or "").replace("\xa0", " ").replace("&nbsp;", " ")
    amounts: list[str] = []
    ctx = _PAY_RATE_AMOUNT_RE.search(blob)
    if ctx:
        amounts.append(ctx.group(1))
        rest = blob[ctx.end() :]
        rng = re.match(r"\s*[-–]\s*(?:US\s*)?(?:\$|＄)?\s*([\d,.]+)", rest, re.I)
        if rng:
            amounts.append(rng.group(1))
    if not amounts:
        found = _DOLLAR_RE.findall(blob)
        hourly: list[str] = []
        for item in found:
            try:
                value = float(item.replace(",", ""))
            except ValueError:
                continue
            if 7 <= value <= 80:
                hourly.append(item)
        amounts = hourly[:2] or found[:1]
    if not amounts:
        num = _PAY_RATE_NUMBER_RE.search(blob)
        if num:
            amounts.append(num.group(1))
    cleaned = [f"${item.replace(',', '')}" for item in amounts if item]
    if len(cleaned) >= 2:
        return f"{cleaned[0]} - {cleaned[1]}"
    return cleaned[0] if cleaned else ""


def _normalize_duration(raw: str) -> str:
    match = re.search(r"(regular|seasonal)", raw or "", re.I)
    return match.group(1).title() if match else ""


def _pick_location_line(text: str) -> str:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    for line in lines:
        street = _STREET_ADDRESS_RE.search(line)
        if street:
            return street.group("line").strip()
    for line in lines:
        if re.search(r"type:|duration:|pay\s*rate", line, re.I):
            continue
        if re.search(r",\s*[A-Z]{2}(?:\s+\d{5})?$", line):
            return line
    return next((line for line in lines if "mi" in line.lower() or "," in line), "")


def _stringify_job_value(value: Any) -> str:
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, (int, float)):
        if value <= 0 or value > 500:
            return ""
        return f"${value:.2f}"
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in (
            "formatted",
            "text",
            "display",
            "payRate",
            "payRateMax",
            "salary",
            "amount",
            "max",
            "min",
            "value",
            "name",
            "address",
            "street",
            "streetAddress",
            "fullAddress",
            "duration",
            "schedule",
        ):
            found = _stringify_job_value(value.get(key))
            if found:
                return found
        return ""
    if isinstance(value, list):
        for item in value:
            found = _stringify_job_value(item)
            if found:
                return found
    return ""


def _first_job_text(*values: Any) -> str:
    for value in values:
        found = _stringify_job_value(value)
        if found:
            return found
    return ""


def _fill_missing(target: dict[str, str], source: dict[str, str]) -> None:
    for field in ("title", "url", "externalId", "jobType", "salary", "schedule", "city", "state"):
        incoming = str(source.get(field) or "").strip()
        current = str(target.get(field) or "").strip()
        if field == "salary":
            incoming = _normalize_salary(incoming) or incoming
            if incoming and not _normalize_salary(current):
                target[field] = incoming
            continue
        if not incoming or current:
            continue
        if field == "schedule":
            incoming = _normalize_duration(incoming) or incoming
        target[field] = incoming
    incoming_loc = str(source.get("location") or "").strip()
    current_loc = str(target.get("location") or "").strip()
    if incoming_loc and (not current_loc or (_looks_like_street(incoming_loc) and not _looks_like_street(current_loc))):
        target["location"] = incoming_loc
        city, state = _parse_location(incoming_loc)
        if city:
            target["city"] = city
        if state:
            target["state"] = state


def _store_job(bucket: dict[str, dict[str, str]], job: dict[str, str]) -> None:
    key = job.get("externalId") or job.get("title") or ""
    if not key:
        return
    current = bucket.get(key)
    if not current:
        bucket[key] = dict(job)
        return
    _fill_missing(current, job)


def _extract_job_id(*parts: str) -> str:
    blob = " ".join(part for part in parts if part)
    match = JOB_ID_RE.search(blob)
    if match:
        return match.group(1)
    token = JOB_ID_TOKEN_RE.search(blob)
    return token.group(0) if token else ""


def _job_detail_url(job_id: str) -> str:
    return f"https://hiring.amazon.com/app#/jobDetail?jobId={job_id}&locale=en-US"


def _is_junk_title(title: str) -> bool:
    cleaned = (title or "").strip().lower()
    if not cleaned or cleaned in SKIP_TITLES:
        return True
    return bool(_JUNK_TITLE_RE.search(cleaned)) and "associate" not in cleaned


def _is_real_job(job: dict[str, str]) -> bool:
    title = (job.get("title") or "").strip()
    if _is_junk_title(title):
        return False
    job_id = _extract_job_id(job.get("externalId", ""), job.get("url", ""), job.get("title", ""))
    return bool(job_id)


def _normalize_job(job: dict[str, str]) -> dict[str, str] | None:
    job_id = _extract_job_id(job.get("externalId", ""), job.get("url", ""), job.get("title", ""))
    title = (job.get("title") or "").strip()
    if _is_junk_title(title):
        return None
    normalized = dict(job)
    if not job_id:
        return None
    normalized["externalId"] = job_id
    normalized["url"] = _job_detail_url(job_id)
    return normalized


def _matches_job_title(job: dict[str, str], job_title: str) -> bool:
    needle = job_title.strip().lower()
    if not needle:
        return True
    return needle in (job.get("title") or "").lower()


def _pay_values(salary: str) -> list[float]:
    return [float(match) for match in re.findall(r"(\d+(?:\.\d+)?)", salary or "")]


def _parse_card_text(text: str) -> dict[str, str]:
    blob = text or ""
    type_match = _TYPE_RE.search(blob)
    duration_match = _DURATION_RE.search(blob)
    job_type = (type_match.group(1).strip() if type_match else "")
    job_type = re.split(r"\s+(?:duration:|pay\s*rate:)", job_type, maxsplit=1, flags=re.I)[0].strip()
    return {
        "jobType": job_type,
        "schedule": _normalize_duration(duration_match.group(1) if duration_match else ""),
        "salary": _normalize_salary(blob),
        "location": _pick_location_line(blob),
    }


def _matches_post_filters(job: dict[str, str], filters: dict[str, Any]) -> bool:
    length = str(filters.get("length") or "").strip()
    if length:
        duration = (job.get("schedule") or "").lower()
        title = (job.get("title") or "").lower()
        if duration and ("regular" in duration or "seasonal" in duration):
            if length.lower() not in duration and length.lower() not in title:
                return False

    employment = str(filters.get("employmentType") or "Both").strip().lower()
    if employment and employment not in {"both", ""}:
        job_type = (job.get("jobType") or "").lower()
        if "flex" in employment and "flex" not in job_type:
            return False
        if "full" in employment and "flex" not in employment and "full" not in job_type:
            return False

    return _matches_pay(job.get("salary") or "", filters.get("payRateMin"), filters.get("payRateMax"))


def _matches_pay(salary: str, pay_min: Any, pay_max: Any) -> bool:
    text = (salary or "").strip()
    if not text or re.search(r"consultar|n/?a|not specified|unpaid", text, re.I):
        return True
    values = _pay_values(text)
    if not values:
        return True
    low = float(pay_min) if pay_min not in (None, "") else 0
    high = float(pay_max) if pay_max not in (None, "") else 100
    job_high = max(values)
    job_low = 0.0 if re.search(r"up\s*to|até", text, re.I) else min(values)
    return job_low <= high and job_high >= low


def _fill_job_name(page, job_title: str) -> None:
    if not job_title.strip():
        return
    field = page.get_by_placeholder(re.compile(r"search job", re.I))
    if field.count() == 0:
        field = page.locator("input[type='search'], input[aria-label*='Search' i], input[placeholder*='Search' i]")
    if field.count() == 0:
        print("[warehouse] campo Job Search não encontrado; filtro será aplicado depois", flush=True)
        return
    _dismiss_overlays(page)
    _human_type(page, field.first, job_title.strip())
    page.keyboard.press("Enter")
    _pause(1.2, 2.0)


def _collect_from_json(payload: Any, bucket: dict[str, dict[str, str]]) -> None:
    if isinstance(payload, list):
        for item in payload:
            _collect_from_json(item, bucket)
        return
    if not isinstance(payload, dict):
        return
    title = payload.get("title") or payload.get("jobTitle") or payload.get("name")
    url = payload.get("url") or payload.get("jobUrl") or payload.get("applyUrl") or payload.get("href")
    raw_id = str(payload.get("jobId") or payload.get("externalId") or "")
    job_id = _extract_job_id(raw_id, str(payload.get("id") or ""), str(url or ""))
    if not job_id and raw_id and "jobsearch" not in raw_id.lower() and len(raw_id) >= 8:
        job_id = raw_id
    if title and job_id:
        address = _first_job_text(
            payload.get("streetAddress"),
            payload.get("fullAddress"),
            payload.get("formattedAddress"),
            payload.get("address"),
        )
        location = address or str(payload.get("location") or payload.get("city") or "")
        city, state = _parse_location(location)
        _store_job(
            bucket,
            {
                "externalId": job_id,
                "title": str(title),
                "url": _job_detail_url(job_id),
                "location": location,
                "city": str(payload.get("city") or city),
                "state": str(payload.get("state") or state),
                "jobType": _first_job_text(payload.get("jobType"), payload.get("employmentType")),
                "salary": _normalize_salary(
                    _first_job_text(
                        payload.get("payRate"),
                        payload.get("salary"),
                        payload.get("compensation"),
                        payload.get("payRateMax"),
                    )
                ),
                "schedule": _normalize_duration(
                    _first_job_text(payload.get("duration"), payload.get("schedule"), payload.get("jobDuration"))
                ),
            },
        )
    for value in payload.values():
        if isinstance(value, (dict, list)):
            _collect_from_json(value, bucket)


def _wait_for_job_results(page) -> None:
    try:
        page.locator("text=/\\d+\\s+jobs? found/i").first.wait_for(timeout=15_000)
    except Exception:
        pass
    _pause(0.8, 1.2)


CARD_SELECTORS = (
    '[data-test-id="jobCard"]',
    '[data-test-id="jobSearchResultItem"]',
    '[data-testid="jobCard"]',
)

_JOB_ID_FROM_EL = """el => {
  const JOB = /JOB-[A-Z]{2}-\\d+/i;
  const JOBID = /jobId=([^&#]+)/i;
  const blobs = [];
  const push = (value) => { if (value) blobs.push(String(value)); };
  const scan = (node) => {
    if (!node) return;
    push(node.outerHTML);
    push(node.innerHTML);
    push(node.innerText);
    push(node.textContent);
    for (const attr of node.getAttributeNames?.() || []) push(node.getAttribute(attr));
    for (const key of ['jobId', 'jobID', 'job-id', 'id', 'value', 'href']) {
      try { push(node[key]); } catch {}
    }
    for (const child of node.children || []) scan(child);
    if (node.shadowRoot || node.shadowRootUnl) scan(node.shadowRoot || node.shadowRootUnl);
  };
  scan(el);
  const blob = blobs.join(' ');
  return (blob.match(JOB) || [])[0] || decodeURIComponent((blob.match(JOBID) || [])[1] || '');
}"""

_DEEP_TEXT_JS = """el => {
  const chunks = [];
  const push = (value) => {
    const text = String(value || '').replace(/\\s+/g, ' ').trim();
    if (text) chunks.push(text);
  };
  const walk = (root) => {
    if (!root) return;
    push(root.innerText || root.textContent || '');
    const nodes = root.querySelectorAll ? root.querySelectorAll('*') : [];
    for (const node of nodes) {
      const cls = (node.getAttribute && node.getAttribute('class')) || '';
      const testId = (node.getAttribute && (
        node.getAttribute('data-test-id') ||
        node.getAttribute('data-testid') ||
        node.getAttribute('data-test-component') ||
        ''
      )) || '';
      const own = Array.from(node.childNodes || [])
        .filter((n) => n.nodeType === 3)
        .map((n) => n.textContent || '')
        .join(' ');
      if (
        /jobDetailText/i.test(cls) ||
        /pay/i.test(testId) ||
        /pay\\s*rate/i.test(own) ||
        /(?:US)?\\$\\s*\\d/.test(own)
      ) {
        push(node.innerText || node.textContent || own);
      }
      if (node.shadowRoot || node.shadowRootUnl) walk(node.shadowRoot || node.shadowRootUnl);
    }
  };
  walk(el);
  if (el && (el.shadowRoot || el.shadowRootUnl)) walk(el.shadowRoot || el.shadowRootUnl);
  return chunks.join('\\n');
}"""

_DETAIL_FIELDS_JS = """() => {
  const byId = {};
  const detailTexts = [];
  const chunks = [];
  const textOf = (el) => (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
  const walk = (root) => {
    if (!root) return;
    const t = (root.innerText || root.textContent || '').trim();
    if (t) chunks.push(t);
    const q = (sel) => (root.querySelectorAll ? Array.from(root.querySelectorAll(sel)) : []);
    for (const el of q('[data-test-id], [data-testid]')) {
      const id = (el.getAttribute('data-test-id') || el.getAttribute('data-testid') || '').trim();
      const text = textOf(el);
      if (id && text && text.length < 400) byId[id] = text;
    }
    for (const el of q('[class*="jobDetailText"], [class*="JobDetailText"], [data-test-component="StencilText"]')) {
      const text = textOf(el);
      if (text && text.length < 400) detailTexts.push(text);
    }
    for (const el of q('*')) {
      const own = Array.from(el.childNodes || [])
        .filter((n) => n.nodeType === 3)
        .map((n) => n.textContent || '')
        .join('');
      if (/pay\\s*rate/i.test(own) || /(?:US)?\\$\\s*\\d/.test(own)) {
        const text = textOf(el) || own.trim();
        if (text && text.length < 400) detailTexts.push(text);
      }
      if (el.shadowRoot || el.shadowRootUnl) walk(el.shadowRoot || el.shadowRootUnl);
    }
  };
  walk(document);
  return { byId, detailTexts, text: chunks.join('\\n') };
}"""

_SHADOW_CARDS_JS = """() => {
  const JOB = /JOB-[A-Z]{2}-\\d+/i;
  const JOBID = /jobId=([^&#]+)/i;
  const items = [];
  const seen = new Set();
  const deepText = (root) => {
    const chunks = [];
    const walk = (nodeRoot) => {
      if (!nodeRoot) return;
      chunks.push(nodeRoot.innerText || nodeRoot.textContent || '');
      const nodes = nodeRoot.querySelectorAll ? nodeRoot.querySelectorAll('*') : [];
      for (const node of nodes) {
        const cls = (node.getAttribute && node.getAttribute('class')) || '';
        const comp = (node.getAttribute && node.getAttribute('data-test-component')) || '';
        if (/jobDetailText/i.test(cls) || /StencilText/i.test(comp)) {
          chunks.push(node.innerText || node.textContent || '');
        }
        if (node.shadowRoot || node.shadowRootUnl) walk(node.shadowRoot || node.shadowRootUnl);
      }
    };
    walk(root);
    if (root && (root.shadowRoot || root.shadowRootUnl)) walk(root.shadowRoot || root.shadowRootUnl);
    return chunks.join('\\n');
  };
  const walkCards = (root) => {
    if (!root || !root.querySelectorAll) return;
    for (const el of root.querySelectorAll('[data-test-id="jobCard"], [data-test-id="jobSearchResultItem"]')) {
      const text = deepText(el);
      const href = el.getAttribute('href') || '';
      const blob = [href, el.outerHTML || '', text].join(' ');
      const id = (blob.match(JOB) || [])[0] || decodeURIComponent((blob.match(JOBID) || [])[1] || '');
      const key = id || text.replace(/\\s+/g, ' ').slice(0, 80);
      if (!text.trim() || seen.has(key)) continue;
      seen.add(key);
      items.push({ href, jobId: id, text: text.slice(0, 4000) });
    }
    for (const el of root.querySelectorAll('*')) {
      if (el.shadowRoot || el.shadowRootUnl) walkCards(el.shadowRoot || el.shadowRootUnl);
    }
  };
  walkCards(document);
  return items;
}"""


def _visible_result_count(page) -> int | None:
    for pattern in (r"total\s+(\d+)\s+jobs?\s+found", r"(\d+)\s+jobs?\s+found"):
        try:
            loc = page.get_by_text(re.compile(pattern, re.I)).first
            if loc.count():
                match = re.search(pattern, loc.inner_text(timeout=1_500), re.I)
                if match:
                    return int(match.group(1))
        except Exception:
            continue
    try:
        found = page.evaluate(
            """() => {
              const norm = (value) => (value || '').replace(/\\s+/g, ' ').trim();
              let best = null;
              const walk = (root) => {
                for (const el of root.querySelectorAll('*')) {
                  const own = norm(el.childNodes.length ? Array.from(el.childNodes).filter((n) => n.nodeType === 3).map((n) => n.textContent).join(' ') : el.textContent);
                  const text = norm(el.textContent || '');
                  const match = (own || text).match(/total\\s*(\\d+)\\s*jobs?\\s*found/i);
                  if (match && text.length < 120) best = Number(match[1]);
                  if (el.shadowRoot || el.shadowRootUnl) walk(el.shadowRoot || el.shadowRootUnl);
                }
              };
              walk(document);
              return best;
            }"""
        )
    except Exception:
        return None
    return int(found) if found is not None else None


def _card_locator(page):
    best = None
    best_count = 0
    for selector in CARD_SELECTORS:
        loc = page.locator(selector)
        try:
            count = loc.count()
        except Exception:
            count = 0
        if count > best_count:
            best = loc
            best_count = count
    return best, best_count


def _wait_for_job_cards(page) -> None:
    for selector in CARD_SELECTORS:
        try:
            page.locator(selector).first.wait_for(state="visible", timeout=2_500)
            return
        except Exception:
            continue


def _count_job_cards(page) -> int:
    _wait_for_job_cards(page)
    _, count = _card_locator(page)
    if count:
        return count
    try:
        return int(
            page.evaluate(
                """() => {
                  let count = 0;
                  const walk = (root) => {
                    count += root.querySelectorAll('[data-test-id="jobCard"]').length;
                    for (const el of root.querySelectorAll('*')) {
                      if (el.shadowRoot || el.shadowRootUnl) walk(el.shadowRoot || el.shadowRootUnl);
                    }
                  };
                  walk(document);
                  return count;
                }"""
            )
        )
    except Exception:
        return 0


def _job_id_from_locator(card) -> str:
    try:
        found = card.evaluate(_JOB_ID_FROM_EL)
    except Exception:
        found = ""
    job_id = _extract_job_id(str(found or ""))
    if job_id:
        return job_id
    for selector in ('a[href*="jobId"]', 'a[href*="jobDetail"]', '[href*="JOB-"]'):
        try:
            href = card.locator(selector).first.get_attribute("href", timeout=800)
        except Exception:
            href = None
        job_id = _extract_job_id(href or "")
        if job_id:
            return job_id
    return ""


def _locator_deep_text(locator) -> str:
    parts: list[str] = []
    try:
        parts.append((locator.inner_text(timeout=2_500) or "").strip())
    except Exception:
        pass
    try:
        parts.append(str(locator.evaluate(_DEEP_TEXT_JS) or "").strip())
    except Exception:
        pass
    return "\n".join(part for part in parts if part)


def _job_from_card_locator(card) -> dict[str, str] | None:
    text = _locator_deep_text(card)
    if not text:
        return None
    job_id = _job_id_from_locator(card)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = next((line for line in lines if not _is_junk_title(line) and len(line) > 4), "")
    if not title:
        return None
    parsed = _parse_card_text(text)
    location_line = parsed.get("location") or next(
        (line for line in lines if re.search(r",[A-Z]{2}$|, [A-Z]{2}$", line)),
        "",
    )
    if not location_line:
        location_line = next((line for line in lines if "mi" in line.lower() or "," in line), "")
    city, state = _parse_location(location_line)
    return {
        "externalId": job_id,
        "title": title,
        "url": _job_detail_url(job_id) if job_id else "",
        "location": location_line or f"{city}, {state}".strip(", "),
        "city": city,
        "state": state,
        "jobType": parsed["jobType"],
        "salary": parsed["salary"],
        "schedule": parsed["schedule"],
    }


def _scrape_locator_cards(page) -> list[dict[str, str]]:
    loc, count = _card_locator(page)
    if not loc or count == 0:
        return []
    jobs: list[dict[str, str]] = []
    seen: set[str] = set()
    for index in range(count):
        job = _job_from_card_locator(loc.nth(index))
        if not job:
            continue
        key = job.get("externalId") or job.get("title") or ""
        if not key or key in seen:
            continue
        seen.add(key)
        jobs.append(job)
    print(f"[warehouse] cards via locator: {len(jobs)}/{count}", flush=True)
    return jobs


def _wait_for_job_id_in_url(page, timeout_ms: int = 6_000) -> str:
    deadline = time.time() + timeout_ms / 1000
    job_id = _extract_job_id(page.url)
    while not job_id and time.time() < deadline:
        try:
            page.wait_for_timeout(250)
        except Exception:
            break
        job_id = _extract_job_id(page.url)
    if job_id:
        return job_id
    try:
        blob = page.evaluate("() => location.href + ' ' + document.body.innerText")
    except Exception:
        blob = ""
    return _extract_job_id(str(blob or ""))


def _click_job_card(page) -> bool:
    loc, count = _card_locator(page)
    if loc and count:
        try:
            loc.first.click(force=True, timeout=4_000)
            return True
        except Exception:
            try:
                loc.first.click(timeout=4_000)
                return True
            except Exception:
                pass
    try:
        if page.evaluate(
            """() => {
              const walk = (root) => {
                const card = root.querySelector(
                  '[data-test-id="jobCard"], [data-test-id="jobSearchResultItem"]'
                );
                if (card) {
                  card.click();
                  return true;
                }
                for (const el of root.querySelectorAll('*')) {
                  if ((el.shadowRoot || el.shadowRootUnl) && walk(el.shadowRoot || el.shadowRootUnl)) return true;
                }
                return false;
              };
              return walk(document);
            }"""
        ):
            return True
    except Exception:
        pass
    for pattern in _CARD_TEXT_CLICK:
        try:
            target = page.get_by_text(re.compile(pattern, re.I)).first
            if target.count():
                target.click(timeout=4_000)
                print(f"[warehouse] cliquei no texto da vaga ({pattern})", flush=True)
                return True
        except Exception:
            continue
    return False


def _scrape_single_job(page) -> list[dict[str, str]]:
    print("[warehouse] 1 vaga: lendo jobCard avulso", flush=True)
    loc, _ = _card_locator(page)
    text = ""
    job_id = ""
    if loc and loc.count():
        card = loc.first
        text = _locator_deep_text(card)
        job_id = _job_id_from_locator(card)
    if not text:
        shadow_jobs = _scrape_shadow_cards(page)
        if shadow_jobs:
            job = shadow_jobs[0]
            if job_id:
                job["externalId"] = job_id
                job["url"] = _job_detail_url(job_id)
            text = "\n".join(
                part
                for part in (
                    job.get("title"),
                    job.get("jobType"),
                    job.get("schedule"),
                    job.get("salary"),
                    job.get("location"),
                )
                if part
            )
            if _needs_detail(job) and _click_job_card(page):
                _pause(1.0, 1.6)
                _fill_missing(job, _read_job_detail(page))
            return [job]
    if not text:
        for pattern in _CARD_TEXT_CLICK:
            try:
                loc_text = page.get_by_text(re.compile(pattern, re.I)).first
                if loc_text.count():
                    text = (loc_text.inner_text(timeout=1_500) or "").strip()
                    if text:
                        break
            except Exception:
                continue
    if job_id:
        print(f"[warehouse] jobId no card: {job_id}", flush=True)
        jobs = _jobs_from_single_card(text, job_id)
        if jobs and _needs_detail(jobs[0]) and _click_job_card(page):
            _pause(1.0, 1.6)
            _fill_missing(jobs[0], _read_job_detail(page))
        return jobs
    if not _click_job_card(page):
        leftover = [job for job in _scrape_cards(page) if not _is_junk_title(job.get("title") or "")]
        if leftover:
            _enrich_missing_job_ids(page, leftover[:1])
            return leftover[:1]
        print("[warehouse] jobCard não encontrado", flush=True)
        return []
    job_id = _wait_for_job_id_in_url(page)
    if not job_id:
        print("[warehouse] jobCard aberto sem jobId na URL", flush=True)
        leftover = [job for job in _scrape_cards(page) if not _is_junk_title(job.get("title") or "")]
        if leftover:
            _enrich_missing_job_ids(page, leftover[:1])
            return leftover[:1]
        return []
    print(f"[warehouse] jobId avulso: {job_id}", flush=True)
    jobs = _jobs_from_single_card(text, job_id)
    detail = _read_job_detail(page)
    if jobs:
        _fill_missing(jobs[0], detail)
        if detail.get("title") and (_is_junk_title(jobs[0].get("title") or "") or not jobs[0].get("title")):
            jobs[0]["title"] = detail["title"]
        return jobs
    if detail.get("title") or detail.get("salary"):
        city, state = detail.get("city") or "", detail.get("state") or ""
        return [
            {
                "externalId": job_id,
                "title": detail.get("title") or "Warehouse Associate",
                "url": _job_detail_url(job_id),
                "location": detail.get("location") or f"{city}, {state}".strip(", "),
                "city": city,
                "state": state,
                "jobType": detail.get("jobType") or "",
                "salary": detail.get("salary") or "",
                "schedule": detail.get("schedule") or "",
            }
        ]
    return []


def _title_from_detail(page) -> str:
    for selector in (
        '[data-test-id*="jobTitle" i]',
        '[data-test-id*="job-title" i]',
        "h1",
        "h2",
    ):
        try:
            loc = page.locator(selector).first
            if not loc.count():
                continue
            value = (loc.inner_text(timeout=1_500) or "").strip()
            if value and not _is_junk_title(value) and len(value) > 4:
                return value
        except Exception:
            continue
    try:
        loc = page.get_by_text(re.compile(r"warehouse associate", re.I)).first
        if loc.count():
            value = (loc.inner_text(timeout=1_500) or "").strip()
            if value and not _is_junk_title(value):
                return value
    except Exception:
        pass
    return ""


def _fields_from_test_ids(by_id: dict[str, Any]) -> dict[str, str]:
    result = {"salary": "", "schedule": "", "location": "", "jobType": "", "title": ""}
    for key, value in (by_id or {}).items():
        compact = re.sub(r"[^a-z0-9]+", "", str(key).lower())
        text = str(value or "").strip()
        if not text:
            continue
        if not result["salary"] and "pay" in compact:
            if _normalize_salary(text) or re.search(r"pay\s*rate|\$\s*\d", text, re.I):
                result["salary"] = text
        elif not result["schedule"] and "duration" in compact:
            result["schedule"] = text
        elif not result["location"] and any(token in compact for token in ("address", "street")):
            result["location"] = text
        elif not result["jobType"] and "type" in compact and "duration" not in compact:
            result["jobType"] = text
        elif not result["title"] and "title" in compact:
            result["title"] = text
    if not result["location"]:
        for key, value in (by_id or {}).items():
            compact = re.sub(r"[^a-z0-9]+", "", str(key).lower())
            text = str(value or "").strip()
            if "location" in compact and _looks_like_street(text):
                result["location"] = text
                break
    return result


def _read_job_detail(page) -> dict[str, str]:
    payload: dict[str, Any] = {}
    try:
        payload = page.evaluate(_DETAIL_FIELDS_JS) or {}
    except Exception:
        payload = {}
    by_id = payload.get("byId") or {}
    detail_texts = [str(item) for item in (payload.get("detailTexts") or []) if item]
    parsed = _parse_card_text("\n".join([*detail_texts, str(payload.get("text") or "")]))
    from_ids = _fields_from_test_ids(by_id)
    location = from_ids.get("location") or parsed.get("location") or ""
    city, state = _parse_location(location)
    title = _title_from_detail(page) or from_ids.get("title") or ""
    salary = (
        _normalize_salary(from_ids.get("salary") or "")
        or _normalize_salary("\n".join(detail_texts))
        or parsed.get("salary")
        or ""
    )
    return {
        "title": title,
        "jobType": from_ids.get("jobType") or parsed.get("jobType") or "",
        "salary": salary,
        "schedule": _normalize_duration(from_ids.get("schedule") or parsed.get("schedule") or ""),
        "location": location,
        "city": city,
        "state": state,
    }


def _needs_detail(job: dict[str, str]) -> bool:
    return not (
        job.get("salary")
        and job.get("schedule")
        and _looks_like_street(job.get("location") or "")
    )


def _enrich_job_details(page, jobs: list[dict[str, str]]) -> None:
    missing = [job for job in jobs if _needs_detail(job)]
    for job in missing[:6]:
        job_id = _extract_job_id(job.get("externalId", ""), job.get("url", ""))
        if not job_id:
            continue
        try:
            page.goto(_job_detail_url(job_id), wait_until="domcontentloaded", timeout=30_000)
        except Exception:
            continue
        _pause(1.2, 2.0)
        _dismiss_overlays(page, generic_x=False)
        _fill_missing(job, _read_job_detail(page))
        print(
            f"[warehouse] detalhe {job_id}: pay={job.get('salary')!r} duration={job.get('schedule')!r} loc={job.get('location')!r}",
            flush=True,
        )


def _jobs_from_single_card(text: str, job_id: str) -> list[dict[str, str]]:
    title = next(
        (
            line.strip()
            for line in text.splitlines()
            if line.strip() and not _is_junk_title(line) and len(line.strip()) > 4
        ),
        "",
    )
    parsed = _parse_card_text(text)
    location_line = parsed.get("location") or next(
        (line.strip() for line in text.splitlines() if "mi" in line.lower() or "," in line),
        "",
    )
    city, state = _parse_location(location_line)
    return [
        {
            "externalId": job_id,
            "title": title or "Warehouse Associate",
            "url": _job_detail_url(job_id),
            "location": location_line or f"{city}, {state}".strip(", "),
            "city": city,
            "state": state,
            "jobType": parsed["jobType"],
            "salary": parsed["salary"],
            "schedule": parsed["schedule"],
        }
    ]


def _jobs_from_raw_cards(raw_items: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    jobs: list[dict[str, str]] = []
    for item in raw_items or []:
        text = str(item.get("text") or "")
        href = str(item.get("href") or "")
        job_id = _extract_job_id(str(item.get("jobId") or ""), href, text)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        title = next((line for line in lines if not _is_junk_title(line) and len(line) > 4), "")
        if not title:
            continue
        parsed = _parse_card_text(text)
        location_line = parsed.get("location") or next(
            (line for line in lines if re.search(r",[A-Z]{2}$|, [A-Z]{2}$", line)),
            "",
        )
        if not location_line:
            location_line = next((line for line in lines if "mi" in line.lower() or "," in line), "")
        city, state = _parse_location(location_line)
        jobs.append(
            {
                "externalId": job_id,
                "title": title,
                "url": _job_detail_url(job_id) if job_id else "",
                "location": location_line or title,
                "city": city,
                "state": state,
                "jobType": parsed["jobType"]
                or next((line for line in lines if re.search(r"flex|full.?time|part.?time", line, re.I)), ""),
                "salary": parsed["salary"] or _normalize_salary(text),
                "schedule": parsed["schedule"]
                or _normalize_duration(next((line for line in lines if re.search(r"regular|seasonal", line, re.I)), "")),
            }
        )
    return jobs


def _scrape_shadow_cards(page) -> list[dict[str, str]]:
    try:
        raw_items = page.evaluate(_SHADOW_CARDS_JS) or []
    except Exception:
        raw_items = []
    jobs = _jobs_from_raw_cards(raw_items)
    if jobs:
        print(f"[warehouse] cards via shadow: {len(jobs)}", flush=True)
    return jobs


def _scrape_cards(page) -> list[dict[str, str]]:
    locator_jobs = _scrape_locator_cards(page)
    shadow_jobs = _scrape_shadow_cards(page)
    if locator_jobs:
        shadow_by_id = {job.get("externalId"): job for job in shadow_jobs if job.get("externalId")}
        shadow_by_title = {job.get("title"): job for job in shadow_jobs if job.get("title")}
        for job in locator_jobs:
            extra = shadow_by_id.get(job.get("externalId")) or shadow_by_title.get(job.get("title"))
            if extra:
                _fill_missing(job, extra)
        return locator_jobs
    if shadow_jobs:
        return shadow_jobs
    try:
        raw_items = page.evaluate(
            """() => {
              const JOB = /JOB-[A-Z]{2}-\\d+/i;
              const JOBID = /jobId=([^&#]+)/i;
              const items = [];
              const seen = new Set();
              const visible = (el) => {
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return (
                  style.visibility !== 'hidden' &&
                  style.display !== 'none' &&
                  rect.width > 0 &&
                  rect.height > 0
                );
              };
              const push = (href, jobId, text) => {
                const blob = [href || '', jobId || '', text || ''].join(' ');
                const id = (jobId || '').trim() || (blob.match(JOB) || [])[0] || ((blob.match(JOBID) || [])[1] || '');
                const clean = (text || '').trim();
                const key = id || clean.slice(0, 120);
                if (!clean || seen.has(key)) return;
                seen.add(key);
                items.push({ href: href || '', jobId: id, text: clean.slice(0, 2000) });
              };
              const walk = (root) => {
                for (const el of root.querySelectorAll('*')) {
                  if (el.shadowRoot || el.shadowRootUnl) walk(el.shadowRoot || el.shadowRootUnl);
                  if (!visible(el)) continue;
                  const href = el.getAttribute?.('href') || el.getAttribute?.('data-href') || '';
                  let jobId = el.getAttribute?.('data-job-id') || el.getAttribute?.('data-jobid') || '';
                  for (const attr of el.getAttributeNames?.() || []) {
                    const val = el.getAttribute(attr) || '';
                    if (JOB.test(val) || JOBID.test(val) || /jobDetail/i.test(val)) {
                      jobId = jobId || (val.match(JOB) || [])[0] || ((val.match(JOBID) || [])[1] || '');
                      push(val, jobId, el.innerText || el.textContent || '');
                    }
                  }
                  if (href && (JOB.test(href) || /jobId|jobDetail/i.test(href))) {
                    push(href, jobId, el.innerText || el.textContent || '');
                  }
                  const text = (el.innerText || '').trim();
                  if (
                    text.length > 20 &&
                    text.length < 1800 &&
                    /duration\\s*:/i.test(text) &&
                    /pay\\s*rate\\s*:/i.test(text)
                  ) {
                    push(href, jobId, text);
                  }
                }
              };
              walk(document);
              return items;
            }"""
        )
    except Exception:
        raw_items = []
    print(f"[warehouse] cards no DOM: {len(raw_items or [])}", flush=True)
    return _jobs_from_raw_cards(raw_items)


def _enrich_missing_job_ids(page, jobs: list[dict[str, str]]) -> None:
    for job in jobs:
        if _extract_job_id(job.get("externalId", ""), job.get("url", "")):
            continue
        title = job.get("title") or ""
        if not title:
            continue
        try:
            clicked = page.evaluate(
                """(title) => {
                  const wanted = title.toLowerCase();
                  const visible = (el) => {
                    const rect = el.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0;
                  };
                  const walk = (root) => {
                    for (const el of root.querySelectorAll('a, button, [role="link"], [role="button"]')) {
                      const text = (el.innerText || '').toLowerCase();
                      if (visible(el) && text.includes(wanted)) {
                        el.click();
                        return true;
                      }
                    }
                    for (const el of root.querySelectorAll('*')) {
                      if ((el.shadowRoot || el.shadowRootUnl) && walk(el.shadowRoot || el.shadowRootUnl)) return true;
                    }
                    return false;
                  };
                  return walk(document);
                }""",
                title,
            )
        except Exception:
            clicked = False
        if not clicked:
            continue
        _pause(1.2, 1.8)
        job_id = _extract_job_id(page.url)
        if job_id:
            job["externalId"] = job_id
            job["url"] = _job_detail_url(job_id)
            print(f"[warehouse] jobId via clique: {job_id}", flush=True)
        try:
            page.evaluate("() => history.back()")
            _pause(1.0, 1.6)
        except Exception:
            pass


def run_amazon_warehouse_search(filters: dict[str, Any]) -> list[dict[str, str]]:
    headless = os.environ.get("HEADLESS", "true").lower() != "false"
    collected: dict[str, dict[str, str]] = {}
    kill_extractor_browsers()
    try:
        return _run_amazon_warehouse_search(filters, headless, collected)
    except Exception as error:
        progress.fail(str(error))
        raise
    finally:
        progress.begin("close", "Encerrando o navegador e processos restantes")
        kill_extractor_browsers()
        progress.finish("close")


def _run_amazon_warehouse_search(
    filters: dict[str, Any],
    headless: bool,
    collected: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    progress.begin("launch", "Iniciando o navegador" + (" (headless)" if headless else " (janela visível)"))
    with open_camoufox(headless) as browser:
        page = browser.new_page()
        page.set_default_timeout(15_000)
        attach_trawl_init_script(page)
        progress.set_page(page)

        def on_response(response) -> None:
            url = response.url.lower()
            if response.status != 200:
                return
            if not any(token in url for token in ("job", "search", "hiring")):
                return
            ctype = (response.headers.get("content-type") or "").lower()
            if "json" not in ctype and "graphql" not in ctype:
                return
            try:
                _collect_from_json(response.json(), collected)
            except Exception:
                return

        page.on("response", on_response)
        progress.begin("navigate", JOB_SEARCH_URL)
        page.goto(JOB_SEARCH_URL, wait_until="domcontentloaded", timeout=60_000)
        _pause(2.5, 4.0)
        progress.begin("overlays", "Procurando banners e botões de fechar")
        _dismiss_overlays(page)
        _pause(0.8, 1.4)
        _dismiss_overlays(page)

        zip_code = str(filters.get("zipCode") or "").strip()
        if not zip_code:
            raise RuntimeError("zipCode é obrigatório")

        collected.clear()
        progress.begin("zip", zip_code)
        used_guide = _fill_guide_zip(page, zip_code)
        print(f"[warehouse] assistente={'sim' if used_guide else 'não'}", flush=True)
        _dismiss_overlays(page, generic_x=False)

        if used_guide:
            hours = filters.get("workHours")
            progress.begin("hours", f"0–{hours} h/semana" if hours not in (None, "") else "sem limite definido")
            _set_hours(page, int(hours) if hours is not None and hours != "" else None)

            progress.begin("schedule")
            _wait_wizard(page, "times work best")
            schedule = [item for item in (filters.get("schedule") or []) if item]
            progress.detail(", ".join(schedule) if schedule else "nenhum turno informado — só avança")
            schedule_ok = _select_chips(page, schedule) if schedule else False
            _advance_wizard(page, selected=schedule_ok)

            length = str(filters.get("length") or "").strip()
            progress.begin("length", length or "nenhuma duração informada — só avança")
            _wait_wizard(page, "how long are you planning")
            length_ok = _click_chip(page, length) if length else False
            if length and not length_ok:
                print(f"[warehouse] não achei o chip '{length}'", flush=True)
            _advance_wizard(page, selected=length_ok)

            when_start = str(filters.get("whenStart") or "").strip()
            progress.begin("when", when_start or "nenhuma data informada — só avança")
            _wait_wizard(page, "when can you start")
            when_ok = _select_when_start(page, when_start) if when_start else False
            if when_start and not when_ok:
                print(f"[warehouse] não achei a opção '{when_start}'", flush=True)
            _advance_wizard(page, selected=when_ok, finish=True)
            collected.clear()
        else:
            progress.skip("hours", "schedule", "length", "when", detail="assistente indisponível — usou a busca direta")
            _fill_search_zip(page, zip_code)

        job_title = str(filters.get("jobTitle") or "").strip()
        progress.begin("title", job_title or "sem filtro por nome da vaga")
        _fill_job_name(page, job_title)
        _dismiss_overlays(page, generic_x=False)
        progress.begin("results", "Aguardando o site aplicar os filtros")
        _wait_for_job_results(page)
        try:
            page.wait_for_timeout(3000)
        except Exception:
            print("[warehouse] página fechou antes da coleta", flush=True)
            return []

        progress.begin("collect")
        result_count = _visible_result_count(page)
        card_count = _count_job_cards(page)
        print(f"[warehouse] total visível={result_count} cards={card_count}", flush=True)
        progress.detail(f"{result_count if result_count is not None else '?'} vagas visíveis, {card_count} cards no DOM")
        if result_count == 0 and card_count == 0:
            collected.clear()
            dom_jobs = []
        elif result_count == 1 or card_count == 1:
            collected.clear()
            dom_jobs = _scrape_single_job(page)
            if not dom_jobs or not any(_extract_job_id(job.get("externalId", ""), job.get("url", "")) for job in dom_jobs):
                extra = _scrape_cards(page)
                if extra:
                    _enrich_missing_job_ids(page, extra[:1])
                    dom_jobs = extra[:1]
        else:
            dom_jobs = _scrape_cards(page)
            if not dom_jobs:
                _pause(2.0, 2.5)
                dom_jobs = _scrape_cards(page)
            _enrich_missing_job_ids(page, dom_jobs)
        for job in dom_jobs:
            _store_job(collected, job)

        progress.begin("details", f"{len(collected)} vaga(s) para detalhar")
        _enrich_job_details(page, list(collected.values()))

        progress.begin("filter")
        jobs = []
        for raw in collected.values():
            normalized = _normalize_job(raw)
            if not normalized or not _matches_job_title(normalized, job_title):
                continue
            if not _matches_post_filters(normalized, filters):
                continue
            jobs.append(normalized)
        print(
            f"[warehouse] {len(jobs)} vagas extraídas (json+dom={len(collected)} brutos)",
            flush=True,
        )
        progress.detail(f"{len(jobs)} vaga(s) extraída(s)")
        progress.shot()
        if not headless:
            watch_ms = int(os.environ.get("WATCH_SECONDS", "90")) * 1000
            print(f"[warehouse] janela aberta para validação por {watch_ms // 1000}s", flush=True)
            try:
                page.wait_for_timeout(watch_ms)
            except Exception:
                print("[warehouse] janela fechada durante a validação", flush=True)
        try:
            page.close()
        except Exception:
            pass

    return jobs
