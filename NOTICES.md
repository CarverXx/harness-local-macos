# License and third-party notices

The source patch is derived from DeepSeek Harness, copyright (c) 2026 DeepSeek. The original MIT license is reproduced in this repository. MIT permits use, copying, modification, merging, publication, distribution, sublicensing and sale, provided its copyright and permission notices accompany copies or substantial portions. This project's additions are offered under the same MIT license. [Upstream license at the pinned commit](https://github.com/deepseek-ai/deepseek-harness/blob/9c2670d3bce5275e0d1610272958121af87787bb/LICENSE) · [Included license](LICENSE)

| Component | Relationship to this repository |
| --- | --- |
| DeepSeek Harness Desktop `dsh-v0.2.2-rc.5` | Source baseline `9c2670d3bce5275e0d1610272958121af87787bb`. The builder reads selected source files from this public commit. The operator supplies the signed macOS runtime separately. |
| Electron and dependencies in the desktop runtime | The locally built application retains the vendor's runtime files and notices. Individual third-party licenses apply. Consult the pinned upstream notices and component license files when reviewing or distributing a build. |
| oMLX `v0.8.0` | Separately installed inference server. The upstream project declares Apache-2.0. |
| Qwen3.8-27B MLX 4-bit | Separately acquired model. The referenced quantization's model card declares Apache-2.0. Review the model card and upstream model terms. |
| Build-time npm packages | Exact versions, registry URLs and integrity values are recorded in the lockfile. Packages retain their own licenses, including MIT and BlueOak-1.0.0 in the locked tree. |

The source license and the vendor's desktop/service terms address different material. Section I.4 of the DeepSeek Harness terms recognizes open-source grants and reserves brand rights. Product names in this repository identify the upstream projects and compatibility targets. The MIT license supplies no express trademark license. This repository includes no vendor installer, model weights, branded artwork or prebuilt application. Anyone distributing a separately packaged binary must review its actual contents, notices, applicable terms and branding rights.

[Upstream repository notices](https://github.com/deepseek-ai/deepseek-harness/blob/9c2670d3bce5275e0d1610272958121af87787bb/THIRD_PARTY_NOTICES.md) · [DeepSeek Harness terms](https://www.deepseek.com/harness/terms-of-use/) · [oMLX source](https://github.com/jundot/omlx/tree/v0.8.0) · [Model card](https://huggingface.co/lmstudio-community/Qwen3.8-27B-MLX-4bit/tree/6067b15cf581666a4aecf6af3afaba4bb5efc20c) · [Build lockfile](build/package-lock.json)
