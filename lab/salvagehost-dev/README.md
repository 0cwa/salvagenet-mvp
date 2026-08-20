# SalvageHost development VM

`salvagehost-dev` is a disposable Ubuntu development VM for agent-assisted
SalvageNet work. It runs the Android, guest-QEMU, controller, and container
tooling inside the guest while sharing this checkout through virtiofs.

## Local configuration

```sh
cp lab/salvagehost-dev/.env.example lab/salvagehost-dev/.env
chmod 600 lab/salvagehost-dev/.env
$EDITOR lab/salvagehost-dev/.env
```

`.env` is ignored. It may hold local API keys for a fully trusted development
guest, but the provisioner never interpolates those values into cloud-init,
libvirt XML, command-line arguments, or logs. They remain in the mounted
checkout and must be sourced deliberately inside the guest.

## Provisioning

The host needs libvirt's modular daemons enabled and KVM available. Run this
from the repository root:

```sh
lab/salvagehost-dev/provision.sh
```

The helpers use the current root shell unchanged. Otherwise, they prefer
secureblue's `run0` and fall back to conventional `sudo`, so the same command
works on Fedora, Ubuntu, and similar libvirt hosts.

The script creates a sparse qcow2 overlay whose virtual size is controlled by
`SALVAGEHOST_VM_DISK_GIB` (100 GiB by default). It consumes host storage only
as the guest writes data. It also records the resolved Ubuntu image URL and
SHA-256 in ignored `.state/resolved-image.env`.

The default tracks Ubuntu Noble's current official cloud image. This avoids an
unreviewed collection of stale package pins while retaining the exact digest
used for each local VM. Set both `SALVAGEHOST_UBUNTU_IMAGE_URL` and
`SALVAGEHOST_UBUNTU_IMAGE_SHA256` in `.env` when a specific image must be
retained for a qualification run.

The guest login user is `ubuntu`; the configured public SSH key is installed
for it. The checkout mounts at `/workspace/salvagenet-mvp` and is persisted in
the guest's `/etc/fstab`.

The USB helper is dedicated HIL infrastructure, not a general device manager.
Its supported host boundary is systemd + udev + system libvirt
(`qemu:///system`) for the authorized phone, physical USB port, and
`nodehost-dev` VM. OpenRC, rootless or user-session libvirt, and arbitrary USB
devices remain unsupported. `SALVAGEHOST_USB_QEMU_GROUP` may name an existing
host group for the system libvirt/QEMU device node; if omitted, it defaults to
`qemu`. The reconciler still verifies that the live USB node uses that group.

## Guest use

```sh
ssh ubuntu@<guest-ip>
cd /workspace/salvagenet-mvp
source ~/.config/nodehost/env.sh
source lab/salvagehost-dev/.env # only when the guest needs local credentials
make doctor
make dev-full
```

The cloud-init profile installs the repository's development prerequisites,
then invokes the repository-pinned Go and Android SDK installers. Container
work happens in the Ubuntu guest using rootless Podman.

For physical testing, keep the dedicated phone's exact non-secret identity in
a separate config file. Do not put it in `.env`, because that file can contain
GitHub/OpenAI credentials:

```sh
sudo install -d -m 0755 /etc/salvagehost
sudo install -m 0644 lab/salvagehost-dev/usb-device.conf.example \
  /etc/salvagehost/nodehost-dev-usb.conf
sudo lab/salvagehost-dev/install-usb-reconciler.sh \
  --check --config /etc/salvagehost/nodehost-dev-usb.conf
sudo lab/salvagehost-dev/install-usb-reconciler.sh \
  --dry-run --config /etc/salvagehost/nodehost-dev-usb.conf
```

The installer is intentionally explicit. The host apply sequence is documented
in `install-usb-reconciler.sh --help`; it snapshots managed files for
`--rollback`, installs the event monitor, removes any old persistent udev rule,
and disables or removes the historical 30-second timer. A normal installation
has no periodic timer and no persistent `/etc/udev` rule. The timer and udev
templates remain only as manual/runtime references and are never enabled or
installed as host-wide policy.

Start the VM through the root-only activation boundary:

```sh
sudo /usr/local/libexec/salvagehost/start-nodehost-dev-with-usb.sh
```

The start command validates the exact serial `5VT7N16607000293`, VID/PID
`18d1:4ee7`, physical port `3-2`, `guest-usb` mode, `qemu:///system`, and the
absence of competing `adb`/`adbd`. It creates a transient `/run` session
marker, performs one bounded preflight, starts `nodehost-dev` if necessary,
and performs one bounded post-start reconciliation. Repeating it while the VM
is running is safe. The marker gates the qemu device permission and the
event-driven monitor, so a stopped VM causes no periodic USB work and does not
retain qemu ownership after cleanup. Plain `virsh start nodehost-dev` is
unsupported for HIL: it does not establish this session boundary and may start
the VM without the phone attached.

The strict HIL boundary expects the physical phone hostdev to be absent from
persistent libvirt XML. If an older setup left one behind, the start wrapper
removes that exact matching hostdev before starting the VM; it never writes
transient USB bus/device numbers to persistent XML. Do not use plain
`virsh start` as a workaround.

Stop it gracefully with:

```sh
sudo /usr/local/libexec/salvagehost/stop-nodehost-dev-with-usb.sh
```

The stop command never uses `virsh destroy`, kills ADB, or changes persistent
libvirt identity XML. It waits for a bounded graceful shutdown, then removes
the transient marker and re-evaluates the exact device under ordinary udev
policy. A host reboot also clears the `/run` marker automatically.

The installer does not place a udev rule under `/etc/udev/rules.d`. During an
explicit start, the wrapper creates one exact, transient rule under
`/run/udev/rules.d`, gated by the session marker, then starts the monitor. The
monitor listens for exact-device add/change events and performs bounded live
reconciliation; there is no `SYSTEMD_WANTS` trigger and no timer polling. It
refuses stale sessions when the VM is stopped, never calls libvirt from a hook,
and performs exact serial/VID/PID/physical-port checks plus ADB ownership
refusal.

Persistent XML contains no physical-phone USB hostdev. When the VM is running,
the reconciler attaches the current bus/device address in `--live` XML held in
a temporary file. Bus/device numbers are never written to persistent XML or
status state. It never starts, stops, or kills ADB. The ordinary `virsh start`
path is intentionally unsupported for HIL; use the wrapper so the qemu
permission session is established first.

After an explicitly authorized host apply, verify the target without changing
ADB ownership:

```sh
lab/salvagehost-dev/reconcile-usb-device.sh \
  --check --config /etc/salvagehost/nodehost-dev-usb.conf
ssh ubuntu@<guest-ip> 'lsusb; adb -s 5VT7N16607000293 get-state'
```

Device passthrough is local laboratory infrastructure; it does not enable the
project's deferred USB/AOA product feature or close a physical acceptance gate.

## Networking

NAT is always enabled. Setting `SALVAGEHOST_DIRECT_INTERFACE` adds a direct
macvtap NIC for a phone-reachable Headscale lab. Wi-Fi access points may reject
the guest MAC address; retain NAT as a fallback and use the included host
port-forward when direct DHCP is unavailable.

Set `SALVAGEHOST_LAN_INTERFACE` and leave the two forward ports at `8080` to
make the disposable Headscale lab reachable at `http://<host-lan-ip>:8080`:

```sh
lab/salvagehost-dev/configure-lan-forward.sh
```

The helper discovers the VM's current libvirt DHCP address and adds a
persistent firewalld TCP forward only on the zone that owns the configured LAN
interface. It records the rule in ignored `.state/lan-forward.env`; rerun it
after recreating the VM or changing the NAT lease. It refuses to overwrite an
unrelated forward on the same port. This intentionally exposes the disposable
lab service to devices on the local LAN, not to the internet; do not use it for
a production control server. Remove it with the exact rule printed in
`.state/lan-forward.env`, for example:

```sh
run0 -i firewall-cmd --zone=FedoraWorkstation --remove-forward-port='port=8080:proto=tcp:toaddr=192.168.122.195:toport=8080'
run0 -i firewall-cmd --permanent --zone=FedoraWorkstation --remove-forward-port='port=8080:proto=tcp:toaddr=192.168.122.195:toport=8080'
```
