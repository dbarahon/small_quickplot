import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "collection_quickplot.py"
spec = importlib.util.spec_from_file_location("collection_quickplot", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class HistoryParserTest(unittest.TestCase):
    def test_optional_operation(self):
        history = """EXPID: test
COLLECTIONS: 'geosgcm_moist'
::
geosgcm_moist.fields: 'DBZ_MAX', 'MOIST', 'DBZMAX', 'MAX',
                     'QLTOT', 'AGCM', 'QL',
                     'QITOT', 'AGCM',
::
"""
        with tempfile.TemporaryDirectory() as tmp:
            rc = Path(tmp) / "HISTORY.rc"
            rc.write_text(history)
            fields = module.parse_history(rc)["geosgcm_moist"]
        self.assertEqual(fields[0], {"export": "DBZ_MAX", "component": "MOIST",
                                     "alias": "DBZMAX", "operation": "MAX"})
        self.assertEqual(fields[1]["alias"], "QL")
        self.assertIsNone(fields[1]["operation"])
        self.assertEqual(fields[2]["alias"], "QITOT")


if __name__ == "__main__":
    unittest.main()
