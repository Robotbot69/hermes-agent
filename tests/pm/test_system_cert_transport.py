"""System certificate selection must reach uv without permitting project overrides."""
from pm.environment import _base_environment


def test_system_certificates_survive_pm_environment_filter():
    env = _base_environment({"UV_SYSTEM_CERTS": "true", "UV_PROJECT_ENVIRONMENT": "other"})
    assert env["UV_SYSTEM_CERTS"] == "true"
    assert "UV_PROJECT_ENVIRONMENT" not in env
