"""Codex OAuth verifies TLS with CA bundles from the CLI and environment."""

from __future__ import annotations

import ssl
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from hermes_cli import auth_codex, auth_codex_browser


@pytest.fixture
def private_ca(tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC) - timedelta(minutes=1))
        .not_valid_after(datetime.now(UTC) + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
        .sign(key, hashes.SHA256())
    )
    cert_path, key_path = tmp_path / "private-ca.pem", tmp_path / "private-key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption()))
    try:
        yield cert_path, key_path
    finally:
        cert_path.unlink(missing_ok=True)
        key_path.unlink(missing_ok=True)


def _complete_tls_handshake(client_context, private_ca):
    """Verify a real TLS handshake without a socket that host security software can intercept."""
    cert_path, key_path = private_ca
    # The application injects truststore globally; this fixture is a TLS server,
    # so use stdlib SSL rather than its client certificate verifier.
    from agent.ssl_verify import _stdlib_ssl_context_class
    server_context = _stdlib_ssl_context_class()(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(str(cert_path), str(key_path))
    client_in, client_out = ssl.MemoryBIO(), ssl.MemoryBIO()
    server_in, server_out = ssl.MemoryBIO(), ssl.MemoryBIO()
    client = client_context.wrap_bio(client_in, client_out, server_hostname="localhost")
    server = server_context.wrap_bio(server_in, server_out, server_side=True)
    client_done = server_done = False
    for _ in range(10):
        for side, done in ((client, client_done), (server, server_done)):
            if not done:
                try:
                    side.do_handshake()
                    if side is client:
                        client_done = True
                    else:
                        server_done = True
                except (ssl.SSLWantReadError, ssl.SSLWantWriteError):
                    pass
        if data := client_out.read():
            server_in.write(data)
        if data := server_out.read():
            client_in.write(data)
        if client_done and server_done:
            return
    raise AssertionError("TLS handshake did not finish")


def _clear_ca_environment(monkeypatch):
    for name in ("HERMES_CA_BUNDLE", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"):
        monkeypatch.delenv(name, raising=False)


def test_codex_cli_ca_bundle_trusts_device_and_browser_login(private_ca, monkeypatch):
    from hermes_cli import auth

    _clear_ca_environment(monkeypatch)
    cert_path, _ = private_ca

    def probe(**_kwargs):
        with auth_codex._codex_http_client() as http_client:
            _complete_tls_handshake(http_client._transport._pool._ssl_context, private_ca)
        return {"trusted": True}

    monkeypatch.setattr(auth, "_codex_device_code_login", probe)
    monkeypatch.setattr(auth_codex_browser, "_codex_browser_login", probe)
    monkeypatch.setattr(auth_codex_browser, "_codex_login_flow", lambda args: args.flow)
    for flow in ("device_code", "browser"):
        args = SimpleNamespace(flow=flow, ca_bundle=str(cert_path), no_browser=True, timeout=None)
        assert auth_codex_browser.codex_oauth_login(args) == {"trusted": True}

    # The explicit bundle must not leak into later, unrelated requests.
    with auth_codex._codex_http_client() as http_client, pytest.raises(ssl.SSLCertVerificationError):
        _complete_tls_handshake(http_client._transport._pool._ssl_context, private_ca)


def test_codex_client_honors_hermes_ca_bundle_environment(private_ca, monkeypatch):
    _clear_ca_environment(monkeypatch)
    cert_path, _ = private_ca
    monkeypatch.setenv("HERMES_CA_BUNDLE", str(cert_path))
    with auth_codex._codex_http_client() as http_client:
        _complete_tls_handshake(http_client._transport._pool._ssl_context, private_ca)
