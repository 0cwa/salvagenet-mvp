# Task dependency DAG

```text
T00 import/baseline --------+--------------------+
                            |                    |
T01 contracts/profiles -----+--> T02 QEMU -------+--+
                            |                       |
                            +--> T03 supervisor ----+-->
                                                    T07 vertical integration --> T08 QA
T04 lab/guest-init ---------+--> T05 host mesh ----+-->
                            +--> T06 API/CLI -------+

T09 USB MVP+ depends on T08 and every base acceptance item PASS.
```

## Shared-file ownership

| Shared area | Owner |
|---|---|
| Podroid import/wiring markers | T00 |
| schemas/profile registry | T01 |
| QEMU snapshots and adapter | T02 |
| Room schema/service lifecycle | T03 |
| lab and guest bootstrap assets | T04 |
| libtailscale vendor/integration | T05 |
| OpenAPI and controller CLI | T06 |
| app composition and E2E scripts | T07 |
| acceptance ledger and QA reports | T08 |
| executable USB code | T09 |

Agents must not edit another owner's shared contract without an explicit handoff.
