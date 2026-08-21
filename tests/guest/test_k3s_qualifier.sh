#!/usr/bin/env bash
set -euo pipefail

root=$(git rev-parse --show-toplevel)
cd "$root"
script=profiles/guest-init/k3s-worker-lab/qualify-k3s.sh
sh -n "$script"
if grep -Eq 'k3s (server|agent)|curl.*get\.k3s\.io' "$script"; then
  echo "qualifier must not install or join k3s" >&2
  exit 1
fi

temporary=$(mktemp -d)
trap 'rm -rf "$temporary"' EXIT
report="$temporary/report.json"
"$script" "$report"
jq -e '
  .schemaVersion == 1
  and .profile == "k3s-worker-lab"
  and (.outcome | IN("qualified", "qualified-with-warnings", "unsupported"))
  and .joinedCluster == false
  and (.checks.kernelSupported | type == "boolean")
  and (.checks.cgroupV2 | type == "boolean")
  and (.checks.namespaces | type == "boolean")
  and (.checks.overlayfs | type == "boolean")
  and (.checks.tun | type == "boolean")
  and (.checks.memoryMiB | type == "number")
  and (.checks.rootFreeMiB | type == "number")
' "$report" >/dev/null
test "$(wc -c < "$report")" -le 4096
test "$(stat -c %a "$report")" = 600

values="$temporary/values.json"
printf '%s\n' '{"METADATA_BASE":"http://10.0.2.2:8123/v1/bootstrap/token/","BOOTSTRAP_TOKEN":"safe-test-token_123","INSTANCE_ID":"nodehost-test-1","HOSTNAME":"worker-test-1"}' > "$values"
python3 tools/profiles/render-guest-init.py \
  profiles/guest-init/ubuntu/user-data.template.yaml \
  --values-json "$values" --output "$temporary/user-data"
python3 tools/profiles/render-guest-init.py \
  profiles/guest-init/common/meta-data.template.yaml \
  --values-json "$values" --output "$temporary/meta-data"
python3 tools/profiles/render-guest-init.py \
  profiles/guest-init/k3s-worker-lab/vendor-data.yaml \
  --allow-unresolved --output "$temporary/vendor-data"
grep -q '^#cloud-config$' "$temporary/user-data"
grep -q '^instance-id: nodehost-test-1$' "$temporary/meta-data"
grep -q '#!/usr/bin/env bash' "$temporary/vendor-data"
if grep -q '{{INCLUDE:' "$temporary/vendor-data"; then
  echo "renderer left an unresolved include" >&2
  exit 1
fi

bad_values="$temporary/bad-values.json"
printf '%s\n' '{"METADATA_BASE":"http://10.0.2.2/\nINJECTED=yes","BOOTSTRAP_TOKEN":"safe-test-token_123"}' > "$bad_values"
if python3 tools/profiles/render-guest-init.py \
    profiles/guest-init/ubuntu/user-data.template.yaml \
    --values-json "$bad_values" --output "$temporary/bad-output" 2>/dev/null; then
  echo "renderer accepted a newline injection" >&2
  exit 1
fi

grep -q '^PasswordAuthentication no$' profiles/guest-init/common/nodehost-bootstrap-ubuntu.sh
grep -q -- '--max-time 30' profiles/guest-init/common/nodehost-bootstrap-ubuntu.sh
for test_file in tests/guest/test_h02a_*.py; do
  python3 "$test_file"
done
printf 'guest-init, complete H02A contracts, and K3s qualifier checks: PASS\n'
