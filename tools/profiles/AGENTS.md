# Profile tooling instructions

Pin mutable sources into `profiles/locks/images.lock.json`; never deploy directly from a mutable `current` URL. Scripts must be restart-safe and verify hashes before updating the lock.
