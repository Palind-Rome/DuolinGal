# DuolinGal 可行性与风险评估

## 结论

一句话结论：

**这个项目可以做，但只适合先作为“单作、单机、离线、研究型工具链”来推进。**

如果把目标写成“很快做出一个面向用户的一键式 galgame 英语配音平台”，那现在并不现实。真正的高风险点不是模型，而是“提取、对齐、回注”三段链路。

## 我认可 ChatGPT 的部分

- 先收敛到 **KiriKiri / KiriKiri Z**，是正确的。
- 先用 **《千恋万花》Steam 版** 做样本，比同时兼容多作稳得多。
- **离线批量生成** 比实时 TTS 更适合第一版。
- **GPT-SoVITS** 作为首选模型是合理的，但它不是项目成败的唯一决定因素。

## 我修正 ChatGPT 的部分

### 1. SCN / PSB 解析不是“普通步骤”，而是主风险

公开资料确实支持 KiriKiri / SCN / PSB 这一方向，但现代作品并不一定把可读台词直接保存在易处理的 `.ks` 里。社区 guide 明确提到，近年的 VN 通常不会把对话直接放在可读 `.ks` 脚本中，很多逻辑和数据已经编译进 `.scn`、`.psb` 甚至编译后的 TJS。  

这意味着：**真正的第一验证目标不是训练模型，而是证明你能稳定拿到“voice file + speaker + english line” 的样本表。**

### 2. “文本-语音自动对齐”被低估了

官方 KAG 标签文档里，`playse` 的 `storage` 确实能指向音频资源；这说明 KiriKiri 生态天然支持“脚本驱动音频播放”。  

但在《千恋万花》这类较新的 SCN 流程里，直接靠 KS 标签做还原往往不够，社区也确实针对《Senren * Banka》的 `.ks.scn` 提过兼容问题。  

所以更准确的说法不是“基本能自动对齐”，而是：

**存在自动对齐的工程基础，但是否能低成本跑通，要先做样本验证。**

### 3. 补丁覆盖链路仍然需要本地实测

`KirikiriTools` 的确提供了 `version.dll`、`unencrypted.xp3` 和 `Xp3Pack` 一类工具，适合做覆盖式资源验证。  

但在你自己的项目里，真正关键的不是“理论上能覆盖”，而是：

- 原作是否接受你生成的编码格式
- 是否严格要求原始目录结构
- 自动模式、快进、读档时是否会出问题

所以“patch.xp3 可行”目前应视为 **高可信假设**，不是已完成事实。

### 4. Web UI 不该优先

只要对齐和回注没过，Web UI 再漂亮都只是把未知风险藏起来。  

当前最值得投入代码的是：

- 目录分析器
- 外部工具封装层
- 项目工作区与元数据
- 对齐数据结构与最小导出能力

## 目前最合理的项目定位

DuolinGal 第一阶段最适合定位成：

**“《千恋万花》英语配音实验用的本地工具链”，而不是“万能 galgame 英语配音平台”。**

这个定位的好处是：

- 风险可控
- 成功标准清晰
- 每一步都有可验证产物
- 未来扩展到其他 KiriKiri 作品时，复用价值也更真实

## 三个硬门槛

在继续扩展功能之前，建议先过这三个门槛。

### 门槛 A：提取与解析

目标：

- 成功解包 `voice.xp3`
- 成功解包/反编译 `scn.xp3`
- 至少抽出 100 条候选有声台词节点

通过标准：

- 至少 85% 的样本能拿到 `scene / speaker / voice_file / en_text`

失败就先别碰训练。

### 门槛 B：回注与播放

目标：

- 人工替换 10 条语音
- 成功在游戏内播放

通过标准：

- 不崩溃
- 不错位
- 快进和读档至少做一次基础验证

失败就先别做批量补丁。

### 门槛 C：单角色音色验证

目标：

- 选 1 名主角色
- 清洗 10 到 20 分钟相对干净的样本
- 生成 20 条英文样例

通过标准：

- 你主观上能明显感知“还是这个角色在说英语”
- 但不要求达到商业英语配音水准

失败就先不要承诺“整作英配”。

## 你最应该警惕的风险

### 1. 法务和发布风险高于代码风险

真正敏感的不是你本地研究，而是：

- 是否分发了商业游戏原资源
- 是否分发了直接基于商业角色声线训练出的模型
- 是否把受限制许可的第三方工具二进制一起重新打包

因此仓库应坚持：

- 只发布工具和差异化产物
- 用户自备正版游戏
- 第三方工具尽量外部接入

### 2. 工具链许可并不都适合直接内置

`FreeMote` 仓库明确要求：使用其代码或二进制发布时需要附带许可证，并带有非商业限制说明。  

对 DuolinGal 而言，更稳妥的做法是把它当作用户自行提供的外部工具，而不是直接 vendoring 到仓库里。

### 3. 模型自然度可能拖累体验

即使 GPT-SoVITS 能跨语言推理，也不等于“日语角色音色说英语”会天然非常自然。  

第一阶段更合理的目标是：

- 角色感保留
- 英文可懂
- 可用于学习和实验

而不是追求商业级英配。

## 当前建议

现阶段最合理的推进方式是：

1. 只支持《千恋万花》。
2. 只做 CLI + 最小本地 API。
3. 先实现分析、工作区、工具封装、对齐 stub。
4. 通过真实资源样本验证 A/B/C 三个门槛后，再接 GPT-SoVITS 和补丁批处理。
5. 最后再做完整 Web UI。

## 参考资料

- [Steam 商店：Senren * Banka 语言信息](https://store.steampowered.com/app/1144400/SenrenBanka/)
- [SteamDB：`voice.xp3`、`scn.xp3`、`KAGParserEx.dll`、`psbfile.dll`](https://steamdb.info/depot/1144401/)
- [KrkrExtract：支持 krkr2 / krkrz 的 XP3 解包与封包](https://github.com/unlimit999/KrkrExtract)
- [KAG 官方标签文档：`playse` 与 `storage`](https://krkrz.github.io/krkr2doc/kag3doc/contents/Tags.html)
- [FreeMote：支持 `.scn`、`.psb`、`.psb.m`，含 `PsbDecompile` / `PsBuild`](https://github.com/UlyssesWu/FreeMote)
- [KrKrZSceneManager：面向 SCN 的字符串编辑器，README 中推荐配合 FreeMote](https://github.com/marcussacana/KrKrZSceneManager)
- [GARbro issue：`Senren * Banka` 的 `.ks.scn` 兼容问题](https://github.com/morkt/GARbro/issues/153)
- [VNTranslationTools：支持 KiriKiri `.ks` / `.scn` / `.txt` 的文本补丁流](https://github.com/arcusmaximus/VNTranslationTools)
- [GPT-SoVITS：Few-shot、多语言、API/WebUI、MIT License](https://github.com/RVC-Boss/GPT-SoVITS)
- [XTTS-v2 官方文档](https://docs.coqui.ai/en/latest/models/xtts.html)
- [Fish Speech README](https://github.com/fishaudio/fish-speech)
- [krkrz ecosystem guide：KAGParserEx 与编译 TJS 的社区经验](https://github.com/pantsudev/krkrz_ecosystem_guide)
