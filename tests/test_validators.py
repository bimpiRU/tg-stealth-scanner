"""Unit tests for services.validators — the injection guard of the whole bot.

Pure stdlib (unittest); run with either:
    python -m unittest discover -s tests
    python -m pytest tests
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.validators import (  # noqa: E402
    ValidationError,
    validate_domain,
    validate_email,
    validate_ipv4,
)


class ValidateDomainTests(unittest.TestCase):
    def test_accepts_plain_domain(self):
        self.assertEqual(validate_domain("Example.COM"), "example.com")

    def test_accepts_subdomain(self):
        self.assertEqual(validate_domain("a.b.example.com"), "a.b.example.com")

    def test_strips_scheme(self):
        self.assertEqual(validate_domain("https://example.com"), "example.com")

    def test_rejects_path(self):
        with self.assertRaises(ValidationError):
            validate_domain("example.com/admin")

    def test_rejects_empty(self):
        with self.assertRaises(ValidationError):
            validate_domain("   ")

    def test_rejects_too_long(self):
        with self.assertRaises(ValidationError):
            validate_domain("a." * 200 + "com")

    def test_rejects_bad_format(self):
        for bad in ("-example.com", "example-.com", "exa mple.com", "example..com"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValidationError):
                    validate_domain(bad)

    def test_accepts_single_label_host(self):
        # Single-label hosts (localhost, internal names) are intentionally valid.
        self.assertEqual(validate_domain("localhost"), "localhost")

    def test_rejects_shell_metacharacters(self):
        for payload in (
            "example.com; rm -rf /",
            "example.com && whoami",
            "example.com | cat /etc/passwd",
            "$(id).com",
            "`id`.com",
            "example.com\nwhoami",
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(ValidationError):
                    validate_domain(payload)


class ValidateEmailTests(unittest.TestCase):
    def test_accepts_valid(self):
        self.assertEqual(validate_email("User@Example.com"), "user@example.com")

    def test_rejects_bad_format(self):
        for bad in ("no-at-sign", "a@b", "@example.com", "a@@b.com"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValidationError):
                    validate_email(bad)

    def test_rejects_injection(self):
        with self.assertRaises(ValidationError):
            validate_email("a@b.com; rm -rf /")


class ValidateIpv4Tests(unittest.TestCase):
    def test_accepts_public(self):
        self.assertEqual(validate_ipv4("1.1.1.1", allow_private=False), "1.1.1.1")

    def test_private_rejected_by_default(self):
        # Default is now allow_private=False (config ALLOW_PRIVATE_IPS off).
        with self.assertRaises(ValidationError):
            validate_ipv4("192.168.1.1")

    def test_allows_private_when_requested(self):
        self.assertEqual(validate_ipv4("192.168.1.1", allow_private=True), "192.168.1.1")

    def test_rejects_private_when_disallowed(self):
        for private in ("10.0.0.1", "192.168.0.5", "172.16.0.1", "127.0.0.1"):
            with self.subTest(private=private):
                with self.assertRaises(ValidationError):
                    validate_ipv4(private, allow_private=False)

    def test_rejects_octet_over_255(self):
        with self.assertRaises(ValidationError):
            validate_ipv4("256.1.1.1")

    def test_rejects_non_ipv4(self):
        for bad in ("1.2.3", "1.2.3.4.5", "abc", "1.1.1.1; ls"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValidationError):
                    validate_ipv4(bad)


if __name__ == "__main__":
    unittest.main()
