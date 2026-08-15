import importlib.util
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch


PROXY = Path(__file__).parents[1] / "scripts" / "sandbox" / "proxy.py"


class SandboxProxyTunnelTest(TestCase):
    def test_non_fixture_connect_uses_raw_tunnel(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            fixture_root = root / "http"
            certs = root / "certs"
            fixture_root.mkdir()
            certs.mkdir()
            argv = ["proxy.py", str(fixture_root), str(certs), str(certs / "real-ca.pem")]
            with patch.object(sys, "argv", argv):
                spec = importlib.util.spec_from_file_location("sandbox_proxy_test", PROXY)
                proxy = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(proxy)

            calls = []
            connection = object()
            with patch.object(
                proxy,
                "tunnel_https",
                side_effect=lambda conn, host, port: calls.append((conn, host, port)),
            ):
                proxy.handle_connect(connection, "registry.npmjs.org:443")

            self.assertEqual(calls, [(connection, "registry.npmjs.org", 443)])


if __name__ == "__main__":
    main()
