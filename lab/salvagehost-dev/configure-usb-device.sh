#!/usr/bin/env bash
set -euo pipefail

# Compatibility entrypoint. The durable implementation lives in the
# reconciler; this wrapper never reads the credential-bearing lab .env and
# requires an explicit operation.

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
config_file=${SALVAGEHOST_USB_CONFIG:-/etc/salvagehost/nodehost-dev-usb.conf}
operation=

usage() {
  cat >&2 <<'EOF'
usage: configure-usb-device.sh --dry-run|--check|--status|--apply|--validate-config [--config FILE]

The config contains only the VM and exact USB identity. Use
install-usb-reconciler.sh for udev/systemd installation.
EOF
}

while (($#)); do
  case $1 in
    --config)
      (($# >= 2)) || { usage; exit 2; }
      config_file=$2
      shift 2
      ;;
    --dry-run|--check|--status|--apply|--validate-config)
      [[ -z $operation ]] || { usage; exit 2; }
      operation=$1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

[[ -n $operation ]] || { usage; exit 2; }
exec "$script_dir/reconcile-usb-device.sh" "$operation" --config "$config_file"
