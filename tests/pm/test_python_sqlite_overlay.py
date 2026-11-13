"""A separately pinned SQLite archive must reach Python's DLL search path."""
import struct

import pytest

from pm.package import InstallError
from pm.packages import Python


def _pe(machine):
    header = bytearray(64)
    header[:2] = b"MZ"
    header[60:64] = (64).to_bytes(4, "little")
    return bytes(header) + b"PE\0\0" + struct.pack("<H", machine)


@pytest.mark.parametrize("machine,accepted", [(0x8664, True), (0xAA64, False)])
def test_pinned_sqlite_overlay_is_staged_before_python_publication(tmp_path, machine, accepted):
    (tmp_path / "DLLs").mkdir()
    (tmp_path / "python.exe").write_bytes(_pe(0x8664))
    bundled = tmp_path / "DLLs" / "sqlite3.dll"
    bundled.write_bytes(b"bundled")
    overlay = tmp_path / "sqlite3.dll"
    replacement = _pe(machine)
    overlay.write_bytes(replacement)
    if not accepted:
        with pytest.raises(InstallError):
            Python().stage(None, tmp_path, "test", "win32-x64")
        assert bundled.read_bytes() == b"bundled"
        return
    Python().stage(None, tmp_path, "test", "win32-x64")
    assert bundled.read_bytes() == replacement
    assert not overlay.exists()
