# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Proxy resolution from the environment, mirroring the behavior of ``requests``.

``urllib3`` reads no proxy configuration of its own, while ``requests`` does,
so the ``urllib3`` transport of this package calls ``_get_environ_proxy`` for
every request URL to reach the same decision ``requests`` would have reached.
The ``requests`` transport does not use this module.

The decision is made in two steps. ``_should_bypass_proxies`` answers whether
the URL is exempt, by the ``NO_PROXY`` environment variable and then by the
platform's own bypass rules. When it is not exempt, ``_get_environ_proxy``
picks the proxy URL out of the ``<scheme>_proxy`` and ``all_proxy``
environment variables, and ``_get_proxy_auth`` pulls the credentials out of
that proxy URL.
"""

from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import unquote, urlparse
from urllib.request import getproxies, proxy_bypass


def _get_no_proxy() -> str | None:
    """Return the raw value of the no-proxy environment variable.

    The lowercase ``no_proxy`` takes precedence over the uppercase
    ``NO_PROXY``, which is the order ``requests`` uses. The value is returned
    unparsed, as the comma separated list the caller splits.

    Returns:
        The value of ``no_proxy``, or of ``NO_PROXY`` when ``no_proxy`` is
        unset or empty, or ``None`` when neither holds a non-empty value. An
        empty value is reported as ``None`` because an empty list exempts
        nothing.
    """
    return os.environ.get("no_proxy") or os.environ.get("NO_PROXY")


def _is_ipv4_address(value: str) -> bool:
    """Return whether the string is a dotted-quad IPv4 address.

    This decides how a host is matched against the ``NO_PROXY`` entries: an
    IPv4 host is compared by address and by CIDR network, any other host by
    name. IPv6 is not recognised, so a bracketed IPv6 host takes the
    name-matching path.

    Args:
        value: The host part of a URL, or a single ``NO_PROXY`` entry.

    Returns:
        ``True`` when :class:`ipaddress.IPv4Address` accepts the string,
        ``False`` otherwise.
    """
    try:
        ipaddress.IPv4Address(value)
    except ValueError:
        return False
    return True


def _address_in_network(address: str, network: str) -> bool:
    """Return whether an IPv4 address falls inside a CIDR network.

    Host bits set in the network are ignored, so ``10.0.0.1/24`` is read as
    ``10.0.0.0/24`` instead of being rejected.

    Args:
        address: A dotted-quad IPv4 address, normally the host of the URL
            being checked.
        network: A single ``NO_PROXY`` entry, expected in CIDR form such as
            ``"10.0.0.0/8"``.

    Returns:
        ``False`` when the entry carries no ``/``, since an entry without a
        prefix length is matched as an exact address elsewhere. ``False`` as
        well when either argument fails to parse, so a malformed entry exempts
        nothing rather than raising. ``True`` only when both parse and the
        address lies in the network.
    """
    if "/" not in network:
        return False
    try:
        return ipaddress.IPv4Address(address) in ipaddress.IPv4Network(network, strict=False)
    except ValueError:
        return False


def _should_bypass_proxies(url: str) -> bool:
    """Return ``True`` if requests to *url* should not go through a proxy.

    Matches ``requests.utils.should_bypass_proxies``: entries in ``NO_PROXY``
    are compared against the host (IPv4 hosts by exact address or CIDR, other
    hosts by exact match or domain suffix on a ``.`` boundary, with or without
    port), then the platform's bypass rules
    are consulted via :func:`urllib.request.proxy_bypass`.

    An empty element, which two adjacent commas produce, is dropped when the
    list is split. An entry made only of dots survives that and is skipped
    separately, so a stray ``.`` does not exempt a hostname written with a
    trailing dot such as ``example.com.``.

    Args:
        url: The absolute URL the request is about to be sent to.

    Returns:
        ``True`` when the request should be sent directly. A URL with no host
        at all, which is what an unparseable or relative URL gives, is
        reported as bypassed, because there is nothing to match a proxy rule
        against. ``False`` when a proxy should be used, which includes the
        case where :func:`urllib.request.proxy_bypass` fails to answer.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname
    if hostname is None:
        return True

    no_proxy = _get_no_proxy()
    if no_proxy:
        entries = [entry for entry in no_proxy.replace(" ", "").split(",") if entry]
        if _is_ipv4_address(hostname):
            for entry in entries:
                if hostname == entry or _address_in_network(hostname, entry):
                    return True
        else:
            host_with_port = hostname
            if parsed.port:
                host_with_port += f":{parsed.port}"
            for entry in entries:
                suffix = entry.lstrip(".")
                if not suffix:
                    continue
                for candidate in (hostname, host_with_port):
                    if candidate == suffix or candidate.endswith(f".{suffix}"):
                        return True

    try:
        return bool(proxy_bypass(hostname))
    except (TypeError, socket.gaierror):
        return False


def _get_environ_proxy(url: str) -> str | None:
    """Return the proxy URL to use for *url*, or ``None`` for a direct connection.

    Proxies are read with :func:`urllib.request.getproxies`, which honors the
    ``<scheme>_proxy`` and ``all_proxy`` environment variables (lowercase taking
    precedence over uppercase) and falls back to the system proxy configuration
    on macOS and Windows. The scheme specific proxy is preferred over
    ``all_proxy``. Proxy URLs without a scheme are treated as ``http://``.

    The environment is read on every call, so the caller is expected to cache
    the answer per URL. ``Urllib3HTTPTransport`` does, in a 32 entry cache
    that its ``close`` empties, so a change to the proxy environment variables
    reaches a transport that stays open only once the entry for the URL has
    been evicted by 32 other URLs.

    Args:
        url: The absolute URL the request is about to be sent to. Its scheme
            selects which ``<scheme>_proxy`` variable applies, and its host is
            what the bypass rules are checked against.

    Returns:
        The proxy URL to send the request through, with a scheme guaranteed to
        be present. ``None`` when the host is exempt by the bypass rules, or
        when no proxy variable covers the scheme of the URL.
    """
    if _should_bypass_proxies(url):
        return None
    proxies = getproxies()
    scheme = urlparse(url).scheme.lower()
    proxy = proxies.get(scheme) or proxies.get("all")
    if not proxy:
        return None
    if "://" not in proxy:
        proxy = f"http://{proxy}"
    return proxy


def _get_proxy_auth(proxy_url: str) -> tuple[str, str] | tuple[None, None]:
    """Return the percent-decoded ``(username, password)`` from *proxy_url*.

    Percent decoding is what lets a password hold a ``@`` or a ``:``, which
    would otherwise end the credentials or split them.

    Args:
        proxy_url: A proxy URL as returned by ``_get_environ_proxy``, which may
            or may not carry a ``user:password@`` part.

    Returns:
        The decoded username and password. ``(None, None)`` when the URL
        carries no username, which is how the caller tells that no proxy
        authentication header is needed. A username with no password gives an
        empty string for the password rather than ``None``.
    """
    parsed = urlparse(proxy_url)
    if parsed.username is None:
        return None, None
    return unquote(parsed.username), unquote(parsed.password or "")
