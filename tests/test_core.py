"""Core tests with no network or external-binary dependencies."""

from __future__ import annotations

import pytest

from mrrobot.core import registry
from mrrobot.core.config import Scope
from mrrobot.core.models import Mode
from mrrobot.core.runner import NotAuthorized
from mrrobot.core.updates import is_newer


def test_registry_has_tools():
    adapters = registry.all_adapters()
    assert adapters, "there should be at least one registered tool"
    assert registry.get("sherlock") is not None
    assert registry.get("NMAP") is not None  # case-insensitive


def test_version_comparison():
    assert is_newer("1.2.0", "1.1.9")
    assert not is_newer("1.0.0", "1.0.0")
    assert not is_newer("0.9.0", "1.0.0")


def test_scope_blocks_unauthorized_target():
    scope = Scope(domains=["example.com"], authorized=False)
    # authorized=False blocks everything active.
    assert not scope.allows("example.com")


def test_scope_allows_authorized_domain_and_wildcard():
    scope = Scope(domains=["example.com", "*.lab.local"], authorized=True)
    assert scope.allows("example.com")
    assert scope.allows("api.lab.local")
    assert not scope.allows("other.com")


def test_scope_allows_network_cidr():
    scope = Scope(networks=["192.168.1.0/24"], authorized=True)
    assert scope.allows("192.168.1.50")
    assert not scope.allows("10.0.0.1")


def test_active_tool_requires_scope():
    nmap = registry.get("nmap")
    assert nmap is not None
    assert nmap.meta.mode is Mode.ACTIVE
    empty_scope = Scope(authorized=False)
    with pytest.raises(NotAuthorized):
        nmap.run("scanme.nmap.org", scope=empty_scope)
