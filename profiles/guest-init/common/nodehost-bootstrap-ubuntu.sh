#!/usr/bin/env bash
set -euo pipefail
umask 077

: "${NODEHOST_METADATA_BASE:?missing NODEHOST_METADATA_BASE}"
: "${NODEHOST_BOOTSTRAP_TOKEN:?missing NODEHOST_BOOTSTRAP_TOKEN}"
secret_file=$(mktemp /run/nodehost-secret.XXXXXX.json)
trap 'rm -f "$secret_file"' EXIT

curl --fail --silent --show-error \
  --header "Authorization: Bearer $NODEHOST_BOOTSTRAP_TOKEN" \
  "$NODEHOST_METADATA_BASE/bootstrap-secret" \
  --output "$secret_file"

control_url=$(jq -er '.mesh.controlUrl' "$secret_file")
auth_key=$(jq -er '.mesh.oneUseAuthKey' "$secret_file")
hostname=$(jq -er '.mesh.hostname' "$secret_file")
ssh_user=$(jq -er '.ssh.user' "$secret_file")
ready_url=$(jq -er '.callback.readyUrl' "$secret_file")
callback_capability=$(jq -er '.callback.capability' "$secret_file")

id "$ssh_user" >/dev/null 2>&1 || useradd --create-home --shell /bin/bash "$ssh_user"
install -d -m 0700 -o "$ssh_user" -g "$ssh_user" "/home/$ssh_user/.ssh"
jq -r '.ssh.emergencyAuthorizedKeys[]?' "$secret_file" \
  > "/home/$ssh_user/.ssh/authorized_keys"
chown "$ssh_user:$ssh_user" "/home/$ssh_user/.ssh/authorized_keys"
chmod 0600 "/home/$ssh_user/.ssh/authorized_keys"

install -d -m 0755 /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/90-nodehost.conf <<EOF
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
EOF
user_ca=$(jq -er '.ssh.userCaPublicKey // empty' "$secret_file" || true)
if [[ -n "$user_ca" ]]; then
  printf '%s\n' "$user_ca" > /etc/ssh/nodehost-user-ca.pub
  chmod 0644 /etc/ssh/nodehost-user-ca.pub
  printf '%s\n' 'TrustedUserCAKeys /etc/ssh/nodehost-user-ca.pub' \
    >> /etc/ssh/sshd_config.d/90-nodehost.conf
fi
systemctl enable --now ssh
systemctl reload ssh

if ! command -v tailscale >/dev/null 2>&1; then
  install -d -m 0755 /usr/share/keyrings
  curl --fail --silent --show-error \
    https://pkgs.tailscale.com/stable/ubuntu/noble.noarmor.gpg \
    --output /usr/share/keyrings/tailscale-archive-keyring.gpg
  curl --fail --silent --show-error \
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
trap - EXIT

ipv4=$(tailscale ip -4 2>/dev/null | head -n 1 || true)
printf '{"state":"ready","hostname":"%s","tailscaleIpv4":"%s"}\n' \
  "$hostname" "$ipv4" \
  | curl --fail --silent --show-error \
      --request POST \
      --header "Authorization: Bearer $callback_capability" \
      --header 'Content-Type: application/json' \
      --data-binary @- \
      "$ready_url"

rm -f /var/lib/nodehost/bootstrap.env
