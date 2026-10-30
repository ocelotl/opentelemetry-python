# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Zipkin Exporter Endpoints

A Zipkin span carries the network context of the node that recorded it. This
module holds the representation of that context, ``NodeEndpoint``, which the
encoders in ``opentelemetry.exporter.zipkin.encoder`` serialize into the
payload. Where it lands depends on the Zipkin API version: the v2 encoder
writes it once per span as ``localEndpoint``, and the v1 encoder repeats it
under the key ``endpoint`` inside every annotation and binary annotation,
because v1 has no per-span endpoint field.
"""

import ipaddress

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

IpInput = str | int | None
"""Accepted spellings of an IP address passed to ``NodeEndpoint``.

An address may be given as a string such as ``"192.168.0.1"``, as the integer
the address packs into, or as ``None`` when the address is unknown.
"""


class NodeEndpoint:
    """The network context of a node in the service graph.

    The service name is not a parameter. It is read once, at construction
    time, from the resource of the globally registered tracer provider, or
    from a freshly created ``Resource`` when that provider carries none. The
    exporter then overwrites it at the start of every non-empty export, with
    the service name taken from the resource of the first span of that batch,
    whenever that span carries one. The value sampled here is therefore used
    only until the first batch whose first span carries a service name, and
    every batch after that is sent under the most recent such name, including
    an empty batch and a batch whose first span carries none.

    Args:
        ipv4: Primary IPv4 address associated with this connection.
        ipv6: Primary IPv6 address associated with this connection.
        port: Depending on context, this could be a listen port or the
          client-side of a socket. None if unknown.

    Raises:
        ValueError: If ``ipv4`` does not parse as an IPv4 address, or if
            ``ipv6`` does not parse as an IPv6 address.
        KeyError: If the resource of the globally registered tracer provider
            carries no ``service.name`` attribute, since the service name is
            read from that resource with a plain subscript.
    """

    def __init__(
        self,
        ipv4: IpInput = None,
        ipv6: IpInput = None,
        port: int | None = None,
    ):
        """Initialize the endpoint.

        The parameters are documented on the class.
        """
        self.ipv4 = ipv4
        self.ipv6 = ipv6
        self.port = port

        tracer_provider = trace.get_tracer_provider()

        if hasattr(tracer_provider, "resource"):
            resource = tracer_provider.resource
        else:
            resource = Resource.create()

        self.service_name = resource.attributes[SERVICE_NAME]

    @property
    def ipv4(self) -> ipaddress.IPv4Address | None:
        """The parsed form of the ``ipv4`` argument given to the constructor.

        Returns:
            The address as an ``ipaddress.IPv4Address``, whatever spelling it
            was assigned in, or ``None`` when no IPv4 address was given. The
            encoders omit the ``ipv4`` field of the Zipkin endpoint when this
            is ``None``.
        """
        return self._ipv4

    @ipv4.setter
    def ipv4(self, address: IpInput) -> None:
        """Parse and store an IPv4 address.

        Args:
            address: The address, as a string, as the integer it packs into,
                or ``None`` to record that no IPv4 address is known.

        Raises:
            ValueError: If ``address`` parses as an IP address of a family
                other than IPv4, which in practice means an IPv6 address was
                assigned to the IPv4 attribute. ``ipaddress.ip_address``
                raises its own ``ValueError`` first when ``address`` is not an
                IP address at all.
        """
        if address is None:
            self._ipv4 = None
        else:
            ipv4_address = ipaddress.ip_address(address)
            if not isinstance(ipv4_address, ipaddress.IPv4Address):
                raise ValueError(f"{address!r} does not appear to be an IPv4 address")
            self._ipv4 = ipv4_address

    @property
    def ipv6(self) -> ipaddress.IPv6Address | None:
        """The parsed form of the ``ipv6`` argument given to the constructor.

        Returns:
            The address as an ``ipaddress.IPv6Address``, whatever spelling it
            was assigned in, or ``None`` when no IPv6 address was given. The
            encoders omit the ``ipv6`` field of the Zipkin endpoint when this
            is ``None``.
        """
        return self._ipv6

    @ipv6.setter
    def ipv6(self, address: IpInput) -> None:
        """Parse and store an IPv6 address.

        Args:
            address: The address, as a string, as the integer it packs into,
                or ``None`` to record that no IPv6 address is known.

        Raises:
            ValueError: If ``address`` parses as an IP address of a family
                other than IPv6, which in practice means an IPv4 address was
                assigned to the IPv6 attribute. ``ipaddress.ip_address``
                raises its own ``ValueError`` first when ``address`` is not an
                IP address at all.
        """
        if address is None:
            self._ipv6 = None
        else:
            ipv6_address = ipaddress.ip_address(address)
            if not isinstance(ipv6_address, ipaddress.IPv6Address):
                raise ValueError(f"{address!r} does not appear to be an IPv6 address")
            self._ipv6 = ipv6_address
