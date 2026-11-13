from argparse import Namespace
from pathlib import Path


def test_local_browser_private_guard_is_opt_in(monkeypatch):
    from hermes_cli import config
    from tools import browser_url_policy as policy
    from tools import browser_session_cloud as cloud

    cfg = {"browser": {"enforce_private_url_guard_on_local": True}}
    monkeypatch.setattr(config, "read_raw_config", lambda: cfg)
    monkeypatch.setattr(cloud, "is_local_backend", lambda: True)
    monkeypatch.setattr(cloud, "allow_private_urls", lambda: False)
    monkeypatch.setattr(policy, "is_always_blocked_url", lambda _url: False)
    monkeypatch.setattr(policy, "is_safe_url", lambda _url: False)
    monkeypatch.setattr(policy, "check_website_access", lambda _url: None)
    assert policy.evaluate_url_safety("http://127.0.0.1/private") is not None
    assert policy.eval_ssrf_guard_active() is True
    cfg["browser"]["enforce_private_url_guard_on_local"] = False
    assert policy.evaluate_url_safety("http://127.0.0.1/private") is None
    assert policy.eval_ssrf_guard_active() is False


def test_explicit_workspace_survives_lazy_gateway_bootstrap(monkeypatch, tmp_path):
    import os
    from hermes_cli import main

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HERMES_CLI_IN_DIR", "")
    target = tmp_path / "project"
    target.mkdir()
    args = Namespace(in_dir=str(target))
    main._apply_in_dir(args)
    assert Path.cwd() == target
    assert Path(os.environ["HERMES_CLI_IN_DIR"]) == target
    assert args.no_restore_cwd is True
