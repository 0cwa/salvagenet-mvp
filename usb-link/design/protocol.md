# MVP+ protocol sketch

AOA outer frames contain version, channel, flags, payload length, and payload. Channel 0 is authenticated link control; channel 1 carries QEMU stream-net Ethernet framing; channel 2 is reserved for later artifact transfer. Initial MTU is 1400 and eth0/SLIRP remains the fallback route.
