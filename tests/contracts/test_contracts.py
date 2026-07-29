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
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load("control/schemas/guest-bootstrap-secret.schema.json")
        cls.validator = jsonschema.Draft202012Validator(cls.schema, format_checker=jsonschema.FormatChecker())
        cls.example = load("control/examples/guest-bootstrap-secret.example.json")
        cls.enrollment = load("control/examples/node-enrollment.example.json")

    def binding_matches_enrollment(self, guest: dict) -> bool:
        return guest["binding"] == {
            "enrollmentId": self.enrollment["metadata"]["enrollmentId"],
            "issuerSpkiSha256": self.enrollment["controller"]["spkiSha256"],
        }

    def test_example_validates_and_binding_matches_enrollment(self) -> None:
        self.validator.validate(self.example)
        self.assertTrue(self.binding_matches_enrollment(self.example))

    def test_missing_or_malformed_binding_is_rejected(self) -> None:
        fixtures = []
        missing = copy.deepcopy(self.example)
        missing.pop("binding")
        fixtures.append(missing)
        missing_fingerprint = copy.deepcopy(self.example)
        missing_fingerprint["binding"].pop("issuerSpkiSha256")
        fixtures.append(missing_fingerprint)
        extra = copy.deepcopy(self.example)
        extra["binding"]["controllerId"] = "primary-controller"
        fixtures.append(extra)
        for value in fixtures:
            with self.subTest(value=value.get("binding")):
                self.assertFalse(self.validator.is_valid(value))

    def test_binding_values_must_match_enrollment(self) -> None:
        mismatched_enrollment = copy.deepcopy(self.example)
        mismatched_enrollment["binding"]["enrollmentId"] = "different-enrollment-0001"
        mismatched_issuer = copy.deepcopy(self.example)
        mismatched_issuer["binding"]["issuerSpkiSha256"] = "b" * 64
        self.assertFalse(self.binding_matches_enrollment(mismatched_enrollment))
        self.assertFalse(self.binding_matches_enrollment(mismatched_issuer))

    def test_fingerprint_requires_exactly_64_lowercase_hex_characters(self) -> None:
        for fingerprint in ("A" * 64, "a" * 63):
            value = copy.deepcopy(self.example)
            value["binding"]["issuerSpkiSha256"] = fingerprint
            with self.subTest(fingerprint=fingerprint):
                self.assertFalse(self.validator.is_valid(value))

    def test_ssh_requires_exactly_one_nonempty_authorization_form(self) -> None:
        mixed = copy.deepcopy(self.example)
        mixed["ssh"]["emergencyAuthorizedKeys"] = [
            "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExampleEmergencyKey nodehost-example"
        ]
        empty_emergency = copy.deepcopy(self.example)
        empty_emergency["ssh"].pop("userCaPublicKey")
        empty_emergency["ssh"]["emergencyAuthorizedKeys"] = []
        for value in (mixed, empty_emergency):
            self.assertFalse(self.validator.is_valid(value))

    def test_old_callback_path_is_rejected(self) -> None:
        value = copy.deepcopy(self.example)
        value["callback"]["readyUrl"] = "http://10.0.2.2:18080/bootstrap/example/ready"
        self.assertFalse(self.validator.is_valid(value))

    def test_raw_execution_fields_are_rejected(self) -> None:
        for field, raw_value in (
            ("qemuArgs", ["-machine", "virt"]),
            ("kernelArgs", ["console=ttyAMA0"]),
            ("shellCommand", "id"),
        ):
            value = copy.deepcopy(self.example)
            value["callback"][field] = raw_value
            with self.subTest(field=field):
                self.assertFalse(self.validator.is_valid(value))

    def test_schema_shape_tracks_strict_production_parser(self) -> None:
        parser = (ROOT / "android/modules/node-shell/src/main/kotlin/org/nodehost/shell/GuestBootstrapSecretJson.kt").read_text(
            encoding="utf-8"
        )
        synchronized_fragments = (
            'exactly("apiVersion", "kind", "binding", "mesh", "ssh", "callback")',
            'exactly("enrollmentId", "issuerSpkiSha256")',
            'Regex("[a-f0-9]{64}")',
            'setOf("user", "userCaPublicKey")',
            'setOf("user", "emergencyAuthorizedKeys")',
            'exactly("readyUrl", "capability")',
            'http://10.0.2.2:8080/v1/bootstrap/ready',
        )
        for fragment in synchronized_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, parser)


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
