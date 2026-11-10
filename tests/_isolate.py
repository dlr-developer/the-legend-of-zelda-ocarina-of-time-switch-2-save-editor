"""Test isolation bootstrap: isolates APPDATA, HOME, and XDG to a clean temporary directory."""
import atexit
import os
import shutil
import tempfile

_TEST_TMP_DIR = os.environ.get("OOT_TEST_ISOLATED_DIR")
if not _TEST_TMP_DIR:
    _TEST_TMP_DIR = tempfile.mkdtemp(prefix="oot_test_isolated_")
    os.environ["OOT_TEST_ISOLATED_DIR"] = _TEST_TMP_DIR
    os.environ["APPDATA"] = _TEST_TMP_DIR
    os.environ["XDG_CONFIG_HOME"] = _TEST_TMP_DIR
    os.environ["HOME"] = _TEST_TMP_DIR

    def _cleanup():
        shutil.rmtree(_TEST_TMP_DIR, ignore_errors=True)

    atexit.register(_cleanup)

TEST_TMP_DIR = _TEST_TMP_DIR
