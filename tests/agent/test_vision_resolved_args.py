"""Test that call_llm vision path passes resolved provider args, not raw ones."""

from unittest.mock import patch, MagicMock


def test_vision_call_uses_resolved_provider_args():
    """Resolved provider/model/key/url from config must reach resolve_vision_provider_client."""
    from agent.auxiliary_client import call_llm

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="description"))],
        usage=MagicMock(prompt_tokens=10, completion_tokens=5),
    )

    with patch(
        "agent.auxiliary_client._resolve_task_provider_model",
        return_value=("my-resolved-provider", "my-resolved-model", "http://resolved", "resolved-key", "chat_completions"),
    ), patch(
        "agent.auxiliary_client.resolve_vision_provider_client",
        return_value=("my-resolved-provider", fake_client, "my-resolved-model"),
    ) as mock_vision:
        call_llm(
            "vision",
            provider="raw-provider",
            model="raw-model",
            base_url="http://raw",
            api_key="raw-key",
            messages=[{"role": "user", "content": "describe this"}],
        )

    # The resolved values must be passed, not the raw call_llm arguments
    call_args = mock_vision.call_args
    assert call_args.kwargs["provider"] == "my-resolved-provider"
    assert call_args.kwargs["model"] == "my-resolved-model"
    assert call_args.kwargs["base_url"] == "http://resolved"
    assert call_args.kwargs["api_key"] == "resolved-key"


def test_vision_base_url_override_keeps_explicit_provider():
    """Explicit provider should still drive credential resolution with custom base_url."""
    from agent.auxiliary_client import resolve_vision_provider_client

    fake_client = MagicMock()
    with patch(
        "agent.auxiliary_client._resolve_task_provider_model",
        return_value=(
            "zai",
            "glm-4v",
            "https://open.bigmodel.cn/api/paas/v4",
            None,
            "chat_completions",
        ),
    ), patch(
        "agent.auxiliary_client.resolve_provider_client",
        return_value=(fake_client, "glm-4v"),
    ) as mock_resolve:
        provider, client, model = resolve_vision_provider_client()

    assert provider == "zai"
    assert client is fake_client
    assert model == "glm-4v"
    assert mock_resolve.call_args.args[0] == "zai"
    assert mock_resolve.call_args.kwargs["explicit_base_url"] == "https://open.bigmodel.cn/api/paas/v4"


def test_explicit_gemini_vision_uses_native_client(monkeypatch):
    """auxiliary.vision.provider=gemini must use Gemini native, never Codex."""
    import agent.auxiliary_client as aux
    from agent.gemini_native_adapter import GeminiNativeClient

    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setattr(aux, "_select_pool_entry", lambda provider: (False, None))
    monkeypatch.setattr(aux, "_peek_pool_entry", lambda provider: None)

    provider, client, model = aux.resolve_vision_provider_client(
        provider="gemini",
        model="gemini-2.5-flash",
    )

    assert provider == "gemini"
    assert isinstance(client, GeminiNativeClient)
    assert model == "gemini-2.5-flash"


def test_auto_vision_prefers_gemini_before_codex_main(monkeypatch):
    """Auto vision should pick Gemini first and not send Gemini slugs to Codex."""
    import agent.auxiliary_client as aux
    from agent.gemini_native_adapter import GeminiNativeClient

    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setattr(aux, "_select_pool_entry", lambda provider: (False, None))
    monkeypatch.setattr(aux, "_peek_pool_entry", lambda provider: None)
    monkeypatch.setattr(aux, "_read_main_provider", lambda: "openai-codex")
    monkeypatch.setattr(aux, "_read_main_model", lambda: "gpt-5.5")

    provider, client, model = aux.resolve_vision_provider_client(provider="auto")

    assert provider == "gemini"
    assert isinstance(client, GeminiNativeClient)
    assert model.startswith("gemini-")
