# Security model

## Protected paths

The renderer accepts network requests to the authenticated desktop Host on its assigned loopback port. The Host and the commands it starts inherit a macOS socket policy that permits outbound TCP only to the local inference port. The supplied oMLX launcher uses a separate sandbox with the same IP destination restriction, binds to IPv4 loopback and enables offline model loading. The server requires a credential. Use the inference subkey for desktop clients and protect the separate administrative key. The normal deployment assumes a trusted service on port 8000.

The server policy takes effect when the server is started through `macos/serve.py start`. Starting the standalone oMLX GUI or another model server independently gives that process its own network behavior. In particular, the reference oMLX release's built-in benchmark can attempt to submit results to a public leaderboard. [oMLX benchmark implementation](https://github.com/jundot/omlx/blob/v0.8.0/omlx/admin/benchmark.py)

## Boundaries operators should test

- **Disk and backups.** Local application state and cached model context can contain sensitive material. Keep the profile and workspaces on approved volumes and review cloud-sync, backup and retention settings.
- **Other processes.** The IP policies cover the named Host and inference processes. The native shell and Chromium use application-level controls. Chromium can perform network reachability probes separately from HTTP requests. The OS, application acquisition, package managers and unrelated programs have their own network behavior. An air-gapped or deny-all requirement needs independent enforcement.
- **Same-user access.** Local tools can access files allowed to the current OS user. Plugins, shell commands, IPC, local services and operating-system brokers can expand the boundary. Review enabled tools and use organization-managed endpoint controls for untrusted workloads. An environment-variable allowlist does not protect a secret that another process can read from disk.
- **Updates.** Automatic application updates are disabled. Track upstream advisories, review changes against the pinned source, rebuild and rerun acceptance tests. Reevaluate macOS sandbox behavior on each OS upgrade.

## Acceptance test

Run `python3 macos/verify.py` after installation and after changes. It checks the app signature and identifier, the absence of the update feed, the installed policy bytes, access to the expected local model, and denial of test IPv4, IPv6 and off-policy loopback destinations under each profile. Then exercise a synthetic desktop conversation, check that feedback controls are absent, stop inference and verify requests fail locally, and inspect process-level network activity. Record exactly which operating system, application, tools and model were tested. These checks do not prove device-wide isolation.

For a suspected vulnerability, use GitHub's private vulnerability reporting link under the repository's Security tab if available. Keep the initial report to a synthetic reproduction and the affected version. Do not submit live session files, user prompts, model caches, tokens, internal hostnames or customer records.

## Installer and updates

The tagged installer downloads the published, checksum-pinned installation kit, the signed vendor desktop runtime, oMLX and a pinned public model snapshot. These downloads expose ordinary connection metadata to the respective hosts. Chat data is not needed for setup. The installer reconstructs the desktop on the receiving Mac, verifies the resulting application archive, and signs the local application. It does not request an administrator password. A per-user LaunchAgent starts inference on login. After setup it checks the sandbox and performs a small synthetic local generation before reporting readiness. Updates require an explicit installation or rebuild.
