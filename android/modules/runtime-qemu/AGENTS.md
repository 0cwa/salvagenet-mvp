# runtime-qemu instructions

- Preserve imported Podroid launch/lifetime/socket behavior until golden tests pass.
- Public methods accept typed launch models only.
- Raw arguments may exist only in debug fixtures/source sets and must not enter release APIs.
- Keep QMP local and internal; persist/observe lifecycle through node-core contracts.
- Management port forwards default to loopback.
- One active VM; all paths still include an instance ID.
