"""
email_cleaner.py — Free email-validity filter (no paid API needed).

Purpose: stop bouncing email addresses from reaching Instantly. The previous
A-record-only check let 23% bounces through on FMCSA Signal Hub and auto-paused
the campaign. This module layers:

  1. Heuristic filter   — role-based locals, bad syntax, obviously dead TLDs
  2. Real MX lookup     — dnspython if available, else nslookup subprocess
  3. SMTP handshake     — optional, off by default. Only from a throwaway IP
                          you don't share with your Instantly senders, or you
                          will burn your sender reputation.

Usage:
    from email_cleaner import validate_email, VerdictLevel

    v = validate_email("owner@trucking-dead-domain.com")
    if v.level == VerdictLevel.VALID:
        upload_lead(...)

Verdict levels:
    VALID       — heuristic + MX passed. Safe to send.
    RISKY       — role-based or freemail-business mismatch. Caller decides.
    INVALID     — clearly bad. Drop.
"""

from __future__ import annotations

import re
import socket
import subprocess
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache

try:
    import dns.resolver  # type: ignore
    HAS_DNSPYTHON = True
except ImportError:
    HAS_DNSPYTHON = False


class VerdictLevel(str, Enum):
    VALID = "valid"
    RISKY = "risky"
    INVALID = "invalid"


@dataclass
class Verdict:
    email: str
    level: VerdictLevel
    reason: str


# Local parts that never belong to a real decision-maker inbox.
# Census data is riddled with these — auto-forwarders and team aliases that
# either bounce or land in a group mailbox that nobody reads.
ROLE_LOCAL_PARTS = {
    "info", "admin", "administrator", "contact", "help", "support", "sales",
    "service", "office", "team", "hello", "hi", "mail", "email", "inquiries",
    "inquiry", "billing", "accounts", "accounting", "finance", "hr",
    "dispatch", "operations", "ops", "safety", "compliance", "reception",
    "postmaster", "webmaster", "noreply", "no-reply", "donotreply",
    "abuse", "marketing", "media", "press", "legal", "privacy",
}

# TLDs that are almost never used by real US trucking businesses.
# Not exhaustive — just the ones we actually see bounce in census data.
BAD_TLDS = {
    "test", "example", "invalid", "localhost", "local", "internal",
    "lan", "home", "corp",
}

# Free-mail providers. Valid addresses, but weaker buying signal — many
# owner-operators legitimately use gmail.com. We keep these but flag RISKY
# so the caller can decide (e.g. deprioritize in sequence, don't cold-blast).
FREEMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "icloud.com", "me.com", "msn.com", "live.com", "ymail.com",
    "protonmail.com", "proton.me", "mail.com", "comcast.net", "verizon.net",
    "sbcglobal.net", "att.net", "cox.net", "earthlink.net", "juno.com",
    "bellsouth.net", "charter.net", "roadrunner.com", "rr.com",
}

# Very short, obviously-wrong strings (census sometimes has 2-char "emails").
_EMAIL_RE = re.compile(r"^[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}$", re.IGNORECASE)


def _split_email(email: str) -> tuple[str, str] | None:
    if not email or "@" not in email:
        return None
    local, _, domain = email.strip().lower().partition("@")
    if not local or not domain or "." not in domain:
        return None
    return local, domain


def heuristic_check(email: str) -> Verdict | None:
    """
    Fast pre-filter. Returns a Verdict if the email is obviously bad OR
    obviously role-based, otherwise None (meaning: proceed to MX check).
    """
    email = (email or "").strip()
    if not email:
        return Verdict(email, VerdictLevel.INVALID, "empty")
    if not _EMAIL_RE.match(email):
        return Verdict(email, VerdictLevel.INVALID, "bad_syntax")

    parts = _split_email(email)
    if parts is None:
        return Verdict(email, VerdictLevel.INVALID, "unparseable")
    local, domain = parts

    tld = domain.rsplit(".", 1)[-1]
    if tld in BAD_TLDS or tld.isdigit() or len(tld) < 2:
        return Verdict(email, VerdictLevel.INVALID, f"bad_tld:{tld}")

    if local in ROLE_LOCAL_PARTS:
        return Verdict(email, VerdictLevel.RISKY, f"role_local:{local}")

    if domain in FREEMAIL_DOMAINS:
        return Verdict(email, VerdictLevel.RISKY, "freemail")

    return None  # heuristic passes — continue to MX


@lru_cache(maxsize=4096)
def has_mx(domain: str, timeout: float = 4.0) -> bool:
    """
    True if the domain has an MX record (or a fallback A record usable as
    implicit MX, per RFC 5321 §5.1). Cached so repeated lookups of the same
    domain within a run are free.
    """
    domain = (domain or "").strip().lower()
    if not domain or "." not in domain:
        return False

    if HAS_DNSPYTHON:
        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = timeout
            resolver.lifetime = timeout
            answers = resolver.resolve(domain, "MX")
            if answers:
                return True
        except Exception:
            pass
        # Fall through to A record as per RFC 5321 §5.1
        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = timeout
            resolver.lifetime = timeout
            resolver.resolve(domain, "A")
            return True
        except Exception:
            return False

    # Fallback: nslookup subprocess. Available on Windows (built-in) and
    # most Linux distros. Slower and noisier than dnspython but works.
    try:
        result = subprocess.run(
            ["nslookup", "-type=MX", domain],
            capture_output=True, text=True, timeout=timeout,
        )
        if "mail exchanger" in result.stdout.lower() or "MX preference" in result.stdout:
            return True
    except Exception:
        pass

    # Last resort: A-record resolution via socket (same as the old check).
    try:
        socket.setdefaulttimeout(timeout)
        socket.getaddrinfo(domain, None)
        return True
    except Exception:
        return False


def validate_email(email: str, timeout: float = 4.0) -> Verdict:
    """Full check: heuristic → MX. Does NOT do SMTP handshake by default."""
    heuristic = heuristic_check(email)
    if heuristic is not None:
        return heuristic

    parts = _split_email(email)
    if parts is None:
        return Verdict(email, VerdictLevel.INVALID, "unparseable")
    _, domain = parts

    if not has_mx(domain, timeout=timeout):
        return Verdict(email, VerdictLevel.INVALID, "no_mx")

    return Verdict(email, VerdictLevel.VALID, "ok")


def is_sendable(email: str, accept_freemail: bool = True, accept_risky: bool = False) -> bool:
    """
    Convenience: True if this email should be added to an outbound campaign.
    By default, freemail is accepted (common for owner-operators) but other
    RISKY verdicts (role-based locals) are rejected.
    """
    v = validate_email(email)
    if v.level == VerdictLevel.VALID:
        return True
    if v.level == VerdictLevel.RISKY:
        if accept_risky:
            return True
        if accept_freemail and v.reason == "freemail":
            return True
        return False
    return False


# SMTP handshake check — OPTIONAL, not called automatically.
# WARNING: running this from the same IP range as your Instantly senders
# WILL damage your sender reputation. Run from a dedicated verification IP.
def smtp_probe(email: str, from_addr: str = "verify@example.com", timeout: float = 8.0) -> bool:
    """
    RCPT TO probe. Returns True if the mail server accepts the address,
    False if it rejects or errors. Many big providers (gmail, outlook) will
    accept any RCPT then silently drop — so this is most useful for small
    business domains, not freemail.
    """
    import smtplib
    parts = _split_email(email)
    if parts is None:
        return False
    _, domain = parts

    # Find MX host
    mx_host = domain
    if HAS_DNSPYTHON:
        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = timeout
            resolver.lifetime = timeout
            answers = sorted(resolver.resolve(domain, "MX"), key=lambda r: r.preference)
            if answers:
                mx_host = str(answers[0].exchange).rstrip(".")
        except Exception:
            pass

    try:
        with smtplib.SMTP(mx_host, 25, timeout=timeout) as server:
            server.helo("verifier.local")
            server.mail(from_addr)
            code, _ = server.rcpt(email)
            return code in (250, 251)
    except Exception:
        return False


if __name__ == "__main__":
    # Quick smoke test
    tests = [
        "owner@um-cargo.com",
        "info@some-trucking.com",
        "j.smith@gmail.com",
        "admin@local",
        "",
        "not-an-email",
        "real.person@fictional-bogus-domain-xxxxx.test",
    ]
    for e in tests:
        v = validate_email(e)
        print(f"{v.level.value:<8} {e:<50} {v.reason}")
