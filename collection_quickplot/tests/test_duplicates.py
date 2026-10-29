import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "collection_quickplot.py"
spec = importlib.util.spec_from_file_location("collection_quickplot", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DuplicateFieldsTest(unittest.TestCase):
    def test_prog_priority_and_deduplication(self):
        data = {
            "geosgcm_moist": [{"export": "PHIS", "component": "AGCM"}],
            "geosgcm_prog": [{"export": "PHIS", "component": "AGCM"},
                             {"export": "QLTOT", "component": "AGCM"}],
            "geosgcm_surf": [{"export": "PHIS", "component": "AGCM"}],
        }
        tasks = module.create_tasks(data, ["geosgcm_moist", "geosgcm_prog"], [], False, [])
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0]["resolved_collection"], "geosgcm_prog")
        self.assertEqual(tasks[0]["collection"], "geosgcm_moist")
        self.assertEqual(tasks[1]["variable"], "QLTOT")

    def test_only_requested_collection_is_plotted(self):
        data = {
            "geosgcm_prog": [{"export": "PHIS", "component": "AGCM"}],
            "geosgcm_surf": [{"export": "TS", "component": "SURFACE"}],
        }
        tasks = module.create_tasks(data, ["geosgcm_surf"], [], False, [])
        self.assertEqual([t["variable"] for t in tasks], ["TS"])


if __name__ == "__main__":
    unittest.main()
