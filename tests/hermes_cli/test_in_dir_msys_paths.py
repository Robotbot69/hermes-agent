"""``--in`` accepts Git Bash / MSYS-style paths on Windows.

Under Git Bash, ``hermes chat --in ~`` reaches the native CLI as
``/c/Users/<user>`` — the shell expands ``~`` to an MSYS POSIX path and
MSYS2's automatic argument conversion is disabled for native executables.
The resolver must translate the MSYS/Cygwin/WSL drive-root spellings to
native form before the isdir check, or every Git Bash invocation dies with
"--in directory not found" (hit live by the Bot Mode agent-messaging flow,
whose SOUL protocol tells agents to deliver with ``--in ~``).

The translation itself (``_msys_to_windows_path``) has exhaustive unit
coverage in tests/tools/test_local_env_windows_msys.py; this pins the
``--in`` call site actually applying it.
"""

from unittest import mock

from tools.environments.local import _msys_to_windows_path


class TestInDirMsysResolution:
    def test_git_bash_tilde_expansion_translates_on_windows(self):
        # Assert the translation itself — abspath/expanduser are platform
        # functions, and this test also runs on Linux CI where posix abspath
        # would treat 'C:\\...' as relative and prepend the runner's cwd.
        with mock.patch("tools.environments.local._IS_WINDOWS", True):
            translated = _msys_to_windows_path("/c/Users/alice")
            assert translated == "C:" + chr(92) + "Users" + chr(92) + "alice"
            # ntpath (what the resolver uses on Windows) sees it as absolute.
            import ntpath

            assert ntpath.isabs(translated)

    def test_native_and_posix_forms_untouched(self):
        with mock.patch("tools.environments.local._IS_WINDOWS", True):
            assert _msys_to_windows_path("C:/Users/alice") == "C:/Users/alice"
            assert _msys_to_windows_path("~/projects") == "~/projects"

    def test_non_windows_never_translates(self):
        with mock.patch("tools.environments.local._IS_WINDOWS", False):
            assert _msys_to_windows_path("/c/Users/alice") == "/c/Users/alice"

    def test_main_call_site_uses_translation(self, tmp_path):
        """The shared ``--in`` resolver applies MSYS translation."""
        import os

        import hermes_cli.main as main_mod

        target = tmp_path / "project"
        target.mkdir()
        start = os.getcwd()

        try:
            with mock.patch(
                "tools.environments.local._msys_to_windows_path",
                return_value=str(target),
            ) as translate:
                assert main_mod._apply_in_dir("/c/Users/alice/project") is True
                assert os.getcwd() == str(target.resolve())
        finally:
            os.chdir(start)

        translate.assert_called_once_with("/c/Users/alice/project")
