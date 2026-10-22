# Licensing / 许可范围

Version 1.0, effective 2026-10-15. Chinese and English agreement texts are bundled in `LICENSES/`.

| Material / 材料 | Applicable license / 适用许可 |
| --- | --- |
| APLUX-authored `demo/` business code, `examples/`, `sdk/include/` headers and `sdk/python/` bindings, SDK verification utilities (`sdk/verify_release.py`, `sdk/lib/verify_release.py`); accompanying documentation / 阿加犀业务代码、示例、头文件、接口绑定及文档 | [Apache-2.0](LICENSES/Apache-2.0.txt) |
| APLUX proprietary contributions in `sdk/lib/libaudio8_asr.so` / 库中的阿加犀专有部分 | [Pandora 中文](LICENSES/Pandora-Model-SDK.zh-CN.txt) / [English](LICENSES/Pandora-Model-SDK.en.txt) |
| Third-party code, upstream models and weights, runtimes, data and sample media / 第三方代码、上游模型及权重、运行库、数据和示例素材 | Their own licenses and notices / 各自许可与声明，见 [NOTICE](NOTICE) 与 [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt) |

Free APLUX permission covers evaluation, development, demonstrations, small-device
pilots and paid PoCs. Charging for development, integration or validation alone does
not require a commercial APLUX license. Volume production, sales, deliveries or
production deployment at scale require prior written commercial authorization.
Reverse engineering of APLUX proprietary SDK binaries is prohibited, subject to the
agreement's exceptions. Applicable upstream restrictions must still be satisfied.

阿加犀免费许可涵盖体验、开发、演示、少量设备试点和付费 PoC；不因开发、集成、验证服务收费
就要求另行商业授权。批量生产、销售、交付或规模化正式部署前，须取得阿加犀书面商业授权。
专有 SDK 禁止逆向，协议明确的例外除外。以上许可仍受适用的上游许可边界约束。

The `sdk/lib/` license files accompany standalone SDK library downloads. Keep them,
all third-party notices and the applicable third-party license texts when handing
a permitted pilot build to a customer. Business code remains independently usable
under Apache-2.0; calling a proprietary SDK does not put the SDK under Apache-2.0.
The new notices do not retroactively revoke rights lawfully granted for earlier releases.

单独获取 SDK 时请保留 `sdk/lib/` 的许可及第三方声明文件。进行协议允许的试点内嵌交付时，
应将这些文件与适用的第三方许可一并交付。业务代码继续按 Apache-2.0 独立使用，调用专有 SDK
不使 SDK 自动适用 Apache-2.0。新的声明不追溯撤销旧版本已合法授予的权利。

## Separately distributed model files / 单独分发的模型文件

Model weights, tensors and third-party components keep their applicable licenses and required attribution.
The Pandora agreement covers only proprietary contributions that APLUX has the right to license. Consult the
licenses and notices accompanying each model download; this repository does not replace those terms.

模型权重、张量及第三方组件保留各自适用许可及必要署名。Pandora 协议仅覆盖阿加犀有权许可的专有部分，
不替代模型下载包随附的上游条款。

Silero VAD v5 is a third-party model under MIT, not proprietary APLUX material.
See LICENSES/Silero-VAD-MIT.txt.
