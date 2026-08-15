import importlib.util
import sys
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import MagicMock, patch


PROXY = Path(__file__).parents[1] / "scripts" / "sandbox" / "proxy.py"


class SandboxProxyTunnelTest(TestCase):
    def test_non_fixture_connect_uses_raw_tunnel(self):
        proxy = self._load_proxy()
        calls = []
        connection = object()
        with patch.object(
            proxy,
            "tunnel_https",
            side_effect=lambda conn, host, port: calls.append((conn, host, port)),
        ):
            proxy.handle_connect(connection, "registry.npmjs.org:443")

        self.assertEqual(calls, [(connection, "registry.npmjs.org", 443)])

    def test_raw_tunnel_has_no_transfer_timeout(self):
        proxy = self._load_proxy()
        connection = MagicMock()
        upstream = MagicMock()
        upstream.__enter__.return_value = upstream
        with (
            patch.object(proxy.socket, "create_connection", return_value=upstream),
            patch.object(proxy, "relay"),
        ):
            proxy.tunnel_https(connection, "registry.npmjs.org", 443)

        upstream.settimeout.assert_called_once_with(None)

    @staticmethod
    def _load_proxy():
        argv = ["proxy.py", "/nonexistent/http", "/nonexistent/certs", "/nonexistent/ca.pem"]
        with patch.object(sys, "argv", argv):
            spec = importlib.util.spec_from_file_location("sandbox_proxy_test", PROXY)
            proxy = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(proxy)
        return proxy


if __name__ == "__main__":
    main()
