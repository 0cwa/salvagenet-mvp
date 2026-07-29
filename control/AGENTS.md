# Control-contract instructions

- Schemas and OpenAPI are external contracts; T01 owns enrollment/profile schemas and T06 owns OpenAPI.
- Reject unknown fields in v1alpha1.
- No shell, raw QMP, raw QEMU arguments, raw kernel arguments, or unrestricted forwarding fields.
- Examples contain placeholders only and must validate without secrets.
- Contract changes require matching tests and task-owner review.
