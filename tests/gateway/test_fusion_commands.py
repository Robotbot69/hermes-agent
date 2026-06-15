"""Tests for Telegram/OpenRouter Fusion slash commands."""

import pytest

from gateway.slash_commands import GatewaySlashCommandsMixin


class _Event:
    def __init__(self, args: str = "") -> None:
        self._args = args

    def get_command_args(self) -> str:
        return self._args


@pytest.mark.asyncio
async def test_fusion_without_prompt_returns_usage_without_network():
    out = await GatewaySlashCommandsMixin._handle_fusion_command(object(), _Event())

    assert "Usage: `/fusion <question>`" in out
    assert "/fusionlite <question>" in out


@pytest.mark.asyncio
async def test_fusionlite_without_prompt_returns_usage_without_network():
    out = await GatewaySlashCommandsMixin._handle_fusionlite_command(object(), _Event())

    assert "Usage: `/fusionlite <question>`" in out
    assert "without the official Fusion server tool" in out
