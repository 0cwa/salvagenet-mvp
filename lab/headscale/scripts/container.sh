#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
runtime=$(./scripts/runtime.sh)

compose() {
  case "$runtime" in
    docker-compose)
      docker compose --env-file .env -f compose.yaml "$@"
      ;;
    podman-compose)
      podman compose --env-file .env -f compose.yaml "$@"
      ;;
    *)
      return 2
      ;;
  esac
}

if [[ "$runtime" != podman-direct ]]; then
  action=${1:?missing action}
  shift
  case "$action" in
    configtest) compose run --rm headscale configtest ;;
    up) compose up -d ;;
    exec) compose exec -T headscale "$@" ;;
    down) compose down ;;
    *) echo "unknown container action: $action" >&2; exit 2 ;;
  esac
  exit
fi

version=$(awk -F= '$1=="HEADSCALE_VERSION"{print $2}' .env)
listen_ip=$(awk -F= '$1=="HEADSCALE_LISTEN_IP"{print $2}' .env)
host_port=$(awk -F= '$1=="HEADSCALE_HOST_PORT"{print $2}' .env)
: "${version:?HEADSCALE_VERSION is missing from .env}"
: "${listen_ip:?HEADSCALE_LISTEN_IP is missing from .env}"
: "${host_port:?HEADSCALE_HOST_PORT is missing from .env}"
image="docker.io/headscale/headscale:$version"
container=nodehost-headscale
common=(
  --read-only
  --tmpfs "/var/run/headscale:rw,size=16m"
  --volume "$PWD/config/generated:/etc/headscale:ro,Z"
  --volume "$PWD/data:/var/lib/headscale:Z"
)

case "${1:?missing action}" in
  configtest)
    mkdir -p data
    podman run --rm "${common[@]}" "$image" configtest
    ;;
  up)
    mkdir -p data
    podman run --detach --replace --name "$container" \
      "${common[@]}" \
      --publish "$listen_ip:$host_port:8080" \
      --publish 127.0.0.1:9090:9090 \
      --health-cmd 'headscale health' \
      --health-interval 2s --health-timeout 2s --health-retries 30 \
      "$image" serve >/dev/null
    ;;
  exec)
    shift
    podman exec --interactive "$container" "$@"
    ;;
  down)
    podman rm --force --ignore "$container" >/dev/null
    ;;
  *)
    echo "unknown container action: $1" >&2
    exit 2
    ;;
esac
