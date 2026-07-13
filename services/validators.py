import ipaddress
import re


FORBIDDEN_CHARS = re.compile(r"[;\&\|\$\`\(\)\{\}\\\<\>\*\?\[\]\!\#\=\~\n\r]")
DOMAIN_REGEX = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])$"
)
IPV4_REGEX = re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$")
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)


class ValidationError(Exception):
    pass


def _has_forbidden_chars(value: str) -> bool:
    return bool(FORBIDDEN_CHARS.search(value))


def validate_domain(value: str) -> str:
    value = value.strip().lower()
    if not value or len(value) > 253:
        raise ValidationError("Domain too long or empty.")
    if _has_forbidden_chars(value):
        raise ValidationError("Forbidden characters detected.")
    if value.startswith("http://") or value.startswith("https://"):
        value = value.split("//", 1)[1]
    if "/" in value:
        raise ValidationError("Path is not allowed in domain.")
    if not DOMAIN_REGEX.match(value):
        raise ValidationError("Invalid domain format.")
    return value


def validate_email(value: str) -> str:
    value = value.strip().lower()
    if not value or len(value) > 254:
        raise ValidationError("Email too long or empty.")
    if _has_forbidden_chars(value):
        raise ValidationError("Forbidden characters detected.")
    if not EMAIL_REGEX.match(value):
        raise ValidationError("Invalid email format.")
    return value


def validate_ipv4(value: str, allow_private: bool = True) -> str:
    value = value.strip()
    if not value:
        raise ValidationError("IP address is empty.")
    if _has_forbidden_chars(value):
        raise ValidationError("Forbidden characters detected.")

    match = IPV4_REGEX.match(value)
    if not match:
        raise ValidationError("Invalid IPv4 format.")

    for octet in match.groups():
        if int(octet) > 255:
            raise ValidationError("Invalid IPv4 octet.")

    try:
        ip_obj = ipaddress.ip_address(value)
    except ValueError as exc:
        raise ValidationError("Invalid IP address.") from exc

    if not allow_private and ip_obj.is_private:
        raise ValidationError("Private IP addresses are not allowed for this command.")

    return value
