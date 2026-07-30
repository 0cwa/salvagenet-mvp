from __future__ import annotations

import copy
import unittest
from pathlib import Path

from tools.roadmap.validate_seed import SeedError, load_seed, validate_seed


ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = ROOT / ".github/roadmap/seed.v1.json"


class RoadmapSeedTest(unittest.TestCase):
    def setUp(self) -> None:
        self.seed = load_seed(SEED_PATH)

    def test_repository_seed_is_complete_and_valid(self) -> None:
        result = validate_seed(self.seed, ROOT)
        self.assertEqual(7, result.milestone_count)
        self.assertEqual(49, result.item_count)
        self.assertEqual(24, len(result.acceptance_coverage))
        self.assertEqual(("GUEST-01",), result.seed_active_item_ids)

    def test_cycle_is_rejected(self) -> None:
        seed = copy.deepcopy(self.seed)
        by_id = {item["id"]: item for item in seed["items"]}
        by_id["WEB-00"]["blockedBy"] = ["WEB-01"]
        with self.assertRaisesRegex(SeedError, "dependency cycle"):
            validate_seed(seed, ROOT)

    def test_missing_acceptance_coverage_is_rejected(self) -> None:
        seed = copy.deepcopy(self.seed)
        for item in seed["items"]:
            item["acceptanceIds"] = [gate for gate in item["acceptanceIds"] if gate != "U04"]
        with self.assertRaisesRegex(SeedError, "U04"):
            validate_seed(seed, ROOT)

    def test_initial_active_item_requires_a_real_packet(self) -> None:
        seed = copy.deepcopy(self.seed)
        next(item for item in seed["items"] if item["id"] == "GUEST-01")["taskPacket"] = None
        with self.assertRaisesRegex(SeedError, "active.*no task packet"):
            validate_seed(seed, ROOT)

    def test_active_item_cannot_have_unfinished_blocker(self) -> None:
        seed = copy.deepcopy(self.seed)
        next(item for item in seed["items"] if item["id"] == "FND-01")["seedState"] = "review"
        with self.assertRaisesRegex(SeedError, "GUEST-01 is active"):
            validate_seed(seed, ROOT)

    def test_accepted_post_mvp_direction_cannot_disappear(self) -> None:
        seed = copy.deepcopy(self.seed)
        seed["items"] = [item for item in seed["items"] if item["id"] != "PLAT-12"]
        with self.assertRaisesRegex(SeedError, "PLAT-12"):
            validate_seed(seed, ROOT)


if __name__ == "__main__":
    unittest.main()
