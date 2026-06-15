"""Tests for Telegram/OSIRIS slash commands."""

from types import SimpleNamespace
import subprocess

import pytest

from gateway.slash_commands import GatewaySlashCommandsMixin
from hermes_cli.commands import GATEWAY_KNOWN_COMMANDS, telegram_menu_commands


class _Event:
    def __init__(self, args: str = "") -> None:
        self._args = args

    def get_command_args(self) -> str:
        return self._args


@pytest.mark.asyncio
async def test_osint_without_args_returns_usage_without_subprocess():
    runner = GatewaySlashCommandsMixin()
    out = await runner._handle_osint_command(_Event())

    assert "`/osint_radar`" in out
    assert "`/osint sanctions Garantex`" in out


@pytest.mark.asyncio
async def test_osint_sanctions_without_query_returns_usage_without_subprocess():
    runner = GatewaySlashCommandsMixin()
    out = await runner._handle_osint_sanctions_command(_Event())

    assert "Usage: `/osint_sanctions <entity>`" in out


@pytest.mark.asyncio
async def test_osint_health_runs_local_wrapper(monkeypatch):
    calls = []

    monkeypatch.setattr("gateway.slash_commands.Path.exists", lambda _self: True)

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return SimpleNamespace(returncode=0, stdout='{"status":"operational"}', stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    runner = GatewaySlashCommandsMixin()
    out = await runner._handle_osint_health_command(_Event())

    assert '{"status":"operational"}' in out
    assert calls
    assert calls[0][0][:2] == ["/root/scripts/osiris_intel/osiris_intel.py", "health"]
    assert calls[0][1]["cwd"] == "/root"


@pytest.mark.asyncio
async def test_osint_router_maps_sanctions_to_single_query_arg(monkeypatch):
    calls = []

    monkeypatch.setattr("gateway.slash_commands.Path.exists", lambda _self: True)

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout='{"total":1}', stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    runner = GatewaySlashCommandsMixin()
    out = await runner._handle_osint_command(_Event("sanctions Garantex Europe"))

    assert '{"total":1}' in out
    assert calls[0] == [
        "/root/scripts/osiris_intel/osiris_intel.py",
        "sanctions",
        "Garantex Europe",
    ]


def test_osint_commands_are_gateway_known_and_in_telegram_menu():
    for name in {
        "osint",
        "osint_radar",
        "osint_health",
        "osint_sanctions",
        "osint_address",
        "osint_cve",
    }:
        assert name in GATEWAY_KNOWN_COMMANDS

    menu, _hidden = telegram_menu_commands(max_commands=14)
    names = {name for name, _desc in menu}
    assert {
        "osint",
        "osint_radar",
        "osint_sanctions",
    }.issubset(names)
