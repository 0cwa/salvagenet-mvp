#!/usr/bin/env python3
"""Validate versioned JSON contracts and their checked-in examples."""

from copy import deepcopy
import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = (
    (
        ROOT / "control/schemas/node-enrollment.schema.json",
        (ROOT / "control/examples/node-enrollment.example.json",),
    ),
    (
        ROOT / "control/schemas/guest-bootstrap-secret.schema.json",
        (ROOT / "control/examples/guest-bootstrap-secret.example.json",),
    ),
    (
        ROOT / "profiles/schema/vm-profile.schema.json",
        tuple(sorted(ROOT.glob("profiles/*/profile.json"))),
    ),
)
FORBIDDEN_PROPERTY_NAMES = {
    "args", "command", "kernelargs", "kernelarguments", "kernelextra", "qemuargs",
    "qemuarguments", "rawqmp", "shell", "shellcommand",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def property_names(value: object) -> set[str]:
    if isinstance(value, dict):
        return {str(key).lower() for key in value} | set().union(
            *(property_names(child) for child in value.values()), set()
        )
    if isinstance(value, list):
        return set().union(*(property_names(child) for child in value), set())
    return set()


def expect_invalid(validator: jsonschema.Draft202012Validator, value: dict, reason: str) -> None:
    if validator.is_valid(value):
        raise AssertionError(f"schema accepted invalid fixture: {reason}")


def main() -> None:
    for schema_path, example_paths in CONTRACTS:
        schema = load(schema_path)
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(
            schema,
            format_checker=jsonschema.FormatChecker(),
        )
        for example_path in example_paths:
            example = load(example_path)
            validator.validate(example)
            unsafe = property_names(example) & FORBIDDEN_PROPERTY_NAMES
            assert not unsafe, f"{example_path}: forbidden contract properties: {sorted(unsafe)}"

            unknown = deepcopy(example)
            unknown["unexpectedField"] = True
            expect_invalid(validator, unknown, f"{example_path} unknown root field")

    enrollment_schema = load(CONTRACTS[0][0])
    enrollment_validator = jsonschema.Draft202012Validator(enrollment_schema, format_checker=jsonschema.FormatChecker())
    enrollment = load(CONTRACTS[0][1][0])
    bad_initial_profile = deepcopy(enrollment)
    bad_initial_profile["initialRuntime"]["profileId"] = "not-enrolled"
    # JSON Schema cannot express membership in a sibling array; enforce this contract invariant here.
    assert bad_initial_profile["initialRuntime"]["profileId"] not in bad_initial_profile["artifacts"]["profileIds"]
    assert enrollment["initialRuntime"]["profileId"] in enrollment["artifacts"]["profileIds"]

    no_guest_authority = deepcopy(enrollment)
    no_guest_authority["guestAccess"].pop("sshUserCaPublicKey")
    expect_invalid(enrollment_validator, no_guest_authority, "guest SSH authority is required")

    guest_schema = load(CONTRACTS[1][0])
    guest_validator = jsonschema.Draft202012Validator(guest_schema, format_checker=jsonschema.FormatChecker())
    guest = load(CONTRACTS[1][1][0])
    assert guest["binding"] == {
        "enrollmentId": enrollment["metadata"]["enrollmentId"],
        "issuerSpkiSha256": enrollment["controller"]["spkiSha256"],
    }, "guest bootstrap example binding must match the enrollment example"

    missing_binding = deepcopy(guest)
    missing_binding.pop("binding")
    expect_invalid(guest_validator, missing_binding, "guest enrollment binding is required")

    mixed_ssh = deepcopy(guest)
    mixed_ssh["ssh"]["emergencyAuthorizedKeys"] = [
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExampleEmergencyKey nodehost-example"
    ]
    expect_invalid(guest_validator, mixed_ssh, "guest SSH authorization forms are mutually exclusive")

    old_callback = deepcopy(guest)
    old_callback["callback"]["readyUrl"] = "http://10.0.2.2:18080/bootstrap/example/ready"
    expect_invalid(guest_validator, old_callback, "guest callback URL is fixed")

    for fingerprint in ("A" * 64, "a" * 63):
        invalid_fingerprint = deepcopy(guest)
        invalid_fingerprint["binding"]["issuerSpkiSha256"] = fingerprint
        expect_invalid(guest_validator, invalid_fingerprint, "issuer fingerprint must be 64 lowercase hex characters")

    profile_schema = load(CONTRACTS[2][0])
    profile_validator = jsonschema.Draft202012Validator(profile_schema)
    direct = load(ROOT / "profiles/alpine-direct-qualification/profile.json")
    mixed_boot = deepcopy(direct)
    mixed_boot["spec"]["boot"]["firmwareCodeArtifact"] = "aavmf-code"
    expect_invalid(profile_validator, mixed_boot, "mixed direct-kernel and UEFI boot fields")

    print("schemas/examples OK (draft 2020-12, strict unknown fields)")


if __name__ == "__main__":
    main()
