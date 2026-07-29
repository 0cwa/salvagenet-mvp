#!/usr/bin/env bash
set -euo pipefail
umask 077

: "${NODEHOST_METADATA_BASE:?missing NODEHOST_METADATA_BASE}"
: "${NODEHOST_BOOTSTRAP_TOKEN:?missing NODEHOST_BOOTSTRAP_TOKEN}"
[[ "$NODEHOST_METADATA_BASE" =~ ^https?://[^[:space:]]+/$ ]] || {
  echo "invalid NODEHOST_METADATA_BASE" >&2
  exit 1
}
[[ "$NODEHOST_BOOTSTRAP_TOKEN" =~ ^[A-Za-z0-9_-]{16,512}$ ]] || {
  echo "invalid NODEHOST_BOOTSTRAP_TOKEN" >&2
  exit 1
}

secret_file=$(mktemp /run/nodehost-secret.XXXXXX.json)
keys_file=$(mktemp /run/nodehost-authorized-keys.XXXXXX)
trap 'rm -f "$secret_file" "$keys_file"' EXIT

# Do not retry redemption: the metadata owner enforces a single successful use.
curl --fail --silent --show-error --max-time 30 --max-filesize 65536 \
  --proto '=http,https' \
  --header "Authorization: Bearer $NODEHOST_BOOTSTRAP_TOKEN" \
  "${NODEHOST_METADATA_BASE}bootstrap-secret" \
  --output "$secret_file"
unset NODEHOST_BOOTSTRAP_TOKEN
rm -f /var/lib/nodehost/bootstrap.env

control_url=$(jq -er '.mesh.controlUrl | select(type == "string" and test("^https?://[^[:space:]]+$"))' "$secret_file")
auth_key=$(jq -er '.mesh.oneUseAuthKey | select(type == "string" and length >= 16 and length <= 512)' "$secret_file")
hostname=$(jq -er '.mesh.hostname | select(type == "string" and test("^[A-Za-z0-9][A-Za-z0-9.-]{0,62}$"))' "$secret_file")
ssh_user=$(jq -er '.ssh.user | select(type == "string" and test("^[a-z_][a-z0-9_-]{0,31}$"))' "$secret_file")
ready_url=$(jq -er '.callback.readyUrl | select(type == "string" and test("^https?://[^[:space:]]+$"))' "$secret_file")
callback_capability=$(jq -er '.callback.capability | select(type == "string" and length >= 16 and length <= 1024)' "$secret_file")

jq -r '
  .ssh.emergencyAuthorizedKeys // []
  | select(type == "array" and length <= 16)
  | .[]
  | select(type == "string" and length <= 16384)
  | select(test("^(ssh-(ed25519|rsa)|ecdsa-sha2-nistp(256|384|521)) [A-Za-z0-9+/=]+( [^\\r\\n]*)?$"))
' "$secret_file" > "$keys_file"
expected_key_count=$(jq -er '(.ssh.emergencyAuthorizedKeys // []) | select(type == "array" and length <= 16) | length' "$secret_file")
actual_key_count=$(wc -l < "$keys_file")
[[ "$actual_key_count" -eq "$expected_key_count" ]] || {
  echo "bootstrap secret contains an invalid SSH authorized key" >&2
  exit 1
}

id "$ssh_user" >/dev/null 2>&1 || useradd --create-home --shell /bin/bash "$ssh_user"
install -d -m 0700 -o "$ssh_user" -g "$ssh_user" "/home/$ssh_user/.ssh"
install -m 0600 -o "$ssh_user" -g "$ssh_user" "$keys_file" \
  "/home/$ssh_user/.ssh/authorized_keys"

install -d -m 0755 /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/90-nodehost.conf <<EOF
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
EOF
user_ca=$(jq -er '.ssh.userCaPublicKey // "" | select(type == "string" and length <= 16384)' "$secret_file")
if [[ -n "$user_ca" ]]; then
  jq -ner --arg key "$user_ca" \
    '$key | test("^ssh-(ed25519|rsa) [A-Za-z0-9+/=]+( [^\\r\\n]*)?$")' \
    >/dev/null || {
      echo "bootstrap secret contains an invalid SSH user CA" >&2
      exit 1
    }
  printf '%s\n' "$user_ca" > /etc/ssh/nodehost-user-ca.pub
  chmod 0644 /etc/ssh/nodehost-user-ca.pub
  printf '%s\n' 'TrustedUserCAKeys /etc/ssh/nodehost-user-ca.pub' \
    >> /etc/ssh/sshd_config.d/90-nodehost.conf
fi
systemctl enable --now ssh
systemctl reload ssh

if ! command -v tailscale >/dev/null 2>&1; then
  install -d -m 0755 /usr/share/keyrings
  curl --fail --silent --show-error --max-time 30 --proto '=https' \
    https://pkgs.tailscale.com/stable/ubuntu/noble.noarmor.gpg \
    --output /usr/share/keyrings/tailscale-archive-keyring.gpg
  curl --fail --silent --show-error --max-time 30 --proto '=https' \
    https://pkgs.tailscale.com/stable/ubuntu/noble.tailscale-keyring.list \
    --output /etc/apt/sources.list.d/tailscale.list
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y tailscale
fi
systemctl enable --now tailscaled

# The key is one-use and short-lived. Keep shell tracing disabled and erase the
# downloaded secret immediately after registration.
tailscale up \
  --login-server "$control_url" \
  --auth-key "$auth_key" \
  --hostname "$hostname" \
  --accept-dns=true
unset auth_key
rm -f "$secret_file"

ipv4=$(tailscale ip -4 2>/dev/null | head -n 1 || true)
jq -nc --arg hostname "$hostname" --arg ipv4 "$ipv4" \
  '{state:"ready", hostname:$hostname, tailscaleIpv4:$ipv4}' \
  | curl --fail --silent --show-error --max-time 30 --proto '=http,https' \
      --request POST \
      --header "Authorization: Bearer $callback_capability" \
      --header 'Content-Type: application/json' \
      --data-binary @- \
      "$ready_url"
