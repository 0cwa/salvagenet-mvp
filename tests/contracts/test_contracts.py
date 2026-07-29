import copy
import json
from pathlib import Path
import unittest

import jsonschema

ROOT = Path(__file__).resolve().parents[2]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class EnrollmentContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load("control/schemas/node-enrollment.schema.json")
        cls.validator = jsonschema.Draft202012Validator(cls.schema, format_checker=jsonschema.FormatChecker())
        cls.example = load("control/examples/node-enrollment.example.json")

    def test_example_validates(self) -> None:
        self.validator.validate(self.example)

    def test_unknown_nested_field_is_rejected(self) -> None:
        value = copy.deepcopy(self.example)
        value["hostMesh"]["qemuArgs"] = ["-dangerous"]
        self.assertFalse(self.validator.is_valid(value))

    def test_no_guest_ssh_authority_is_rejected(self) -> None:
        value = copy.deepcopy(self.example)
        value["guestAccess"].pop("sshUserCaPublicKey")
        self.assertFalse(self.validator.is_valid(value))

    def test_authorized_keys_can_replace_user_ca(self) -> None:
        value = copy.deepcopy(self.example)
        value["guestAccess"].pop("sshUserCaPublicKey")
        value["guestAccess"]["emergencyAuthorizedKeys"] = [
            "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExampleOnlyKey"
        ]
        self.validator.validate(value)

    def test_oversized_resources_are_rejected(self) -> None:
        value = copy.deepcopy(self.example)
        value["initialRuntime"]["memoryMiB"] = 16385
        self.assertFalse(self.validator.is_valid(value))


class GuestBootstrapContractTest(unittest.TestCase):
    def test_example_validates_and_unknown_fields_fail(self) -> None:
        schema = load("control/schemas/guest-bootstrap-secret.schema.json")
        validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
        example = load("control/examples/guest-bootstrap-secret.example.json")
        validator.validate(example)
        example["callback"]["shellCommand"] = "id"
        self.assertFalse(validator.is_valid(example))


class ProfileContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = jsonschema.Draft202012Validator(load("profiles/schema/vm-profile.schema.json"))

    def test_all_three_profiles_validate_to_same_shape(self) -> None:
        shapes = set()
        for profile_id in (
            "alpine-direct-qualification",
            "ubuntu-2404-arm64-uefi",
            "k3s-worker-lab",
        ):
            value = load(f"profiles/{profile_id}/profile.json")
            self.validator.validate(value)
            shapes.add(tuple(sorted(value["spec"])))
        self.assertEqual(1, len(shapes))

    def test_boot_modes_cannot_be_mixed(self) -> None:
        value = load("profiles/alpine-direct-qualification/profile.json")
        value["spec"]["boot"]["firmwareCodeArtifact"] = "aavmf-code"
        self.assertFalse(self.validator.is_valid(value))

    def test_raw_execution_fields_are_rejected_at_nested_boundaries(self) -> None:
        value = load("profiles/ubuntu-2404-arm64-uefi/profile.json")
        value["spec"]["machine"]["qemuArgs"] = ["-machine", "virt"]
        self.assertFalse(self.validator.is_valid(value))

    def test_nocloud_requires_typed_metadata_path(self) -> None:
        value = load("profiles/ubuntu-2404-arm64-uefi/profile.json")
        value["spec"]["initialization"].pop("metadataPath")
        self.assertFalse(self.validator.is_valid(value))


if __name__ == "__main__":
    unittest.main()
