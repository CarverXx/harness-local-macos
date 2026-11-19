# Local Harness for macOS

An independent, source-based edition of DeepSeek Harness Desktop for Apple Silicon. It is intended for teams that need to review where prompts, tool results and files can go before using a desktop coding assistant with sensitive material. In the supplied configuration, the desktop connects to its own local Host, and the Host sends inference requests to oMLX on the same Mac. A cloud account is unnecessary.

## Install on an Apple Silicon Mac

[中文一键安装指南](README.zh-CN.md)

Paste this line into Terminal while logged in to your Mac.

```bash
curl -fsSL https://raw.githubusercontent.com/CarverXx/harness-local-macos/v1.0.0/install.sh | /bin/bash
```

Supports native Apple Silicon on macOS 15, 26 and 27. Allow 35 GB of free disk space for setup and ~16 GB of model downloads. We recommend at least 32 GB of unified memory. The on-disk inference cache can grow to 24 GB during use. The installer verifies a pinned first-party desktop runtime and applies a release patch locally, provisions oMLX and the model under your user account, registers a login service, then verifies the app and the loopback model endpoint. Open **Local Harness** in your home Applications folder when Terminal prints **Ready**. Rerun the same command after a network interruption. Port 8000 must be available. No Homebrew, Xcode, Node.js, or cloud credentials are needed. The Chinese guide selects the public ModelScope mirror and checks the same model hashes.

## Which data paths change?

| Upstream feature | Behavior in this edition |
| --- | --- |
| Message ratings and feedback | The thumbs-up/down UI, note submission, feedback service and `/feedback` command are disabled. Rating a reply cannot trigger the upstream feedback-context export through these paths. |
| Usage analytics and session telemetry | The desktop analytics client, product telemetry exporter and session OpenTelemetry exporter are disabled. Telemetry is also disabled in the Host environment. |
| Cloud model requests | The two built-in DeepSeek cloud providers are disabled. The configured provider sends prompts to `http://127.0.0.1:8000/v1` with a locally generated inference credential. A failed local request has no configured cloud fallback. |
| Web search, URL fetch and sidebar browsing | Built-in web search, web fetch and the sidebar browser are disabled. External pop-ups and the automatic browser handoff for account login are suppressed. Remote image clipboard fetches are restricted to the local model endpoint. |
| Background update requests | The startup, focus and wake checks are removed. The updater is disabled and the local build omits its feed and mandatory-update policy. Operators review and deploy updates manually. |
| Desktop and tool network access | The Electron renderer restricts HTTP(S) and WebSocket requests to the current loopback Host port. A macOS sandbox restricts outbound IP sockets from the Host and its command-line children to local TCP port 8000. The supplied oMLX launcher applies its own policy to the model server. |
| Shell credentials and workspaces | The desktop skips login-shell environment discovery. The Host inherits an explicit list of operating-system and local-runtime variables. Each installation creates its own application profile and inference key on the operator's Mac. |

**Scope for regulated deployments.** These controls cover specific application paths and processes. Native desktop components, Chromium network probes, same-user files, IPC, third-party helpers and OS services have separate trust boundaries. Local conversations, logs, model caches and files can persist on disk. A synced workspace or a privileged plugin can change the data flow. Validate those conditions on the systems where you intend to use it. [Security model and verification](SECURITY.md) · [Operator responsibilities and limitations](OPERATOR-NOTICE.md)

## Manual build and setup

The reference combination is **macOS on Apple Silicon**, DeepSeek Harness Desktop **0.2.2-rc.5**, **oMLX 0.8.0**, and **Qwen3.8-27B MLX 4-bit**. Port 8000 must be available on loopback. Build and model acquisition require access to public dependencies or an internal mirror. Inference uses local files.

1. Install Git, Node.js 22.12 or later, Python 3.9 or later and the macOS command-line tools. Obtain the matching official DeepSeek Harness desktop application and the oMLX application from their publishers. Install oMLX at `/Applications/oMLX.app`. [Desktop runtime](https://download.deepseek.com/dsh-desk/bin/mac-arm64/deepseek-harness-0.2.2-rc.5-mac-arm64.zip) · [oMLX release](https://github.com/jundot/omlx/releases/tag/v0.8.0)
2. From this repository, build a new application. The example expects an unused output path. The builder verifies the input application's signature and developer identity, matches its version and configuration to the pinned source, builds the desktop main process and applies the local policies.

   ```sh
   upstream_dir="$(mktemp -d)/upstream"
   git clone --depth 1 --branch dsh-v0.2.2-rc.5 \
     https://github.com/deepseek-ai/deepseek-harness.git "$upstream_dir"
   npm --prefix build ci --ignore-scripts
   mkdir -p "$HOME/Applications"
   ./build/build.sh "$upstream_dir" "$HOME/Applications/Local Harness.app" \
     "/Applications/DeepSeek Harness.app"
   ```

3. Provision the model with the Hugging Face CLI, or copy a verified snapshot from an internal artifact store. The snapshot repository name identifies the weight publisher. oMLX loads the files directly. [Pinned weights](https://huggingface.co/lmstudio-community/Qwen3.8-27B-MLX-4bit/tree/6067b15cf581666a4aecf6af3afaba4bb5efc20c)

   ```sh
   profile="$HOME/Library/Application Support/Local Harness"
   hf download lmstudio-community/Qwen3.8-27B-MLX-4bit \
     --revision 6067b15cf581666a4aecf6af3afaba4bb5efc20c \
     --local-dir "$profile/Models/Qwen3.8-27B-4bit"
   python3 macos/serve.py init
   python3 macos/serve.py start
   ```

   Leave the last command running, or have an approved local supervisor run that same command. Initialization creates separate admin and inference credentials under the current user's private `Inference` directory. The desktop uses the inference credential. The server runs with Hub offline mode, distribution across machines disabled, a 4 GB hot-cache ceiling and a 24 GB SSD-cache ceiling.

4. In another terminal, run the checks and open the desktop. Use a synthetic prompt to verify a complete turn before using organizational data.

   ```sh
   python3 macos/verify.py
   open "$HOME/Applications/Local Harness.app"
   ```

The application is locally ad-hoc signed. Organizations with a managed signing or notarization requirement should use their own approval and distribution process. The source patch can be reviewed or applied independently of the convenience builder. The builder reuses the matching vendor runtime and unmodified UI resources supplied by the operator.

## License and provenance

MIT. The original DeepSeek copyright notice and full license are included. This independent project has no affiliation with or endorsement from the upstream publishers. The repository distributes source changes, policy files, documentation and build tooling. [License](LICENSE) · [Third-party notices and upstream references](NOTICES.md)
