# Local examples

Ignored location for generated/live enrollment files. Never commit credentials from this directory.

Android enrollment requires the separately delivered `GuestBootstrapSecret` to carry this issuer binding before any authority is installed:

```json
"binding": {
  "enrollmentId": "<same metadata.enrollmentId as NodeEnrollment>",
  "issuerSpkiSha256": "<same controller.spkiSha256 explicitly verified by the user>"
}
```

After enrollment and tailnet approval, Android displays the device Host API SPKI fingerprint and offers a Storage Access Framework export of the device trust certificate. The canonical Host API port is `7443`; keep the exported trust material outside automatic Android backup.
