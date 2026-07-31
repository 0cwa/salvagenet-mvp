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

For physical testing, attach the dedicated test phone as a USB host device to
the VM, then run `make hil-doctor` in the guest:

```sh
# Set the phone's own IDs in the ignored .env first.
lsusb
lab/salvagehost-dev/configure-usb-device.sh
```

The helper records a persistent libvirt USB host device by vendor/product,
rather than a transient bus/device address. It attaches the device immediately
when the VM is running and keeps the same definition for future VM starts.
`SALVAGEHOST_USB_STARTUP_POLICY=optional` lets the VM start without the phone;
rerun the helper after connecting a phone to attach it to an already-running
VM. Use `mandatory` only when a VM should refuse to start without that device.

Validate the real lifecycle before adding any more automation:

```sh
adb reboot
adb wait-for-device
adb devices -l
make hil-doctor
```

Device passthrough is local laboratory infrastructure; it does not enable the
project's deferred USB/AOA product feature.

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
