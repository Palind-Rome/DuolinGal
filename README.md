# DuolinGal

DuolinGal 是一个面向 galgame 英语听力实验的本地优先工具原型。当前仓库的目标不是“立刻做出完整英语配音平台”，而是先把最难、也最容易被低估的链路做扎实：

- 识别目标游戏目录与引擎特征
- 初始化标准化工作区
- 对接 XP3 / SCN / PSB 外部工具
- 为后续文本-语音对齐、训练、合成和补丁回注提供稳定骨架

当前第一版只针对《千恋万花》这条验证线，默认假设用户拥有正版游戏并在本地自行提取资源。

## 当前状态

- 已完成最小 CLI：`analyze`、`init-project`、`list-tools`
- 已完成最小 API 骨架：`/health`、`/api/analyze`、`/api/projects/init`
- 已完成 KiriKiri / 《千恋万花》目录指纹检测
- 已完成工作区初始化和项目清单输出
- 已完成外部工具需求建模
- 已完成对齐层数据结构和 CSV 导出 stub

## 为什么先做这些

这类项目最大的风险不是“能不能把 GPT-SoVITS 跑起来”，而是：

- 你能不能稳定地从目标游戏里拿到语音、脚本和英文文本
- 你能不能把英文文本和具体语音文件对齐到足够高的精度
- 你能不能在不破坏游戏运行的前提下把生成结果回注进去

所以仓库当前优先级是“证明链路成立”，不是“堆更多模型接口”。

## 快速开始

只使用 CLI 的情况下：

```powershell
$env:PYTHONPATH='src'
python -m duolingal analyze "D:\Games\SenrenBanka"
python -m duolingal init-project "D:\Games\SenrenBanka" --project-id senren-banka
python -m duolingal list-tools
```

如果你想启用本地 API：

```powershell
pip install -e .[api]
$env:PYTHONPATH='src'
uvicorn duolingal.api.app:create_app --factory --reload
```

运行测试：

```powershell
python -m unittest discover -s tests
```

## 仓库结构

```text
DuolinGal/
├─ apps/
│  ├─ api/
│  └─ web/
├─ docs/
├─ src/duolingal/
│  ├─ api/
│  ├─ core/
│  ├─ domain/
│  └─ services/
└─ tests/
```

## 重要边界

- 仓库不附带任何商业游戏资源。
- 仓库当前只实现“研究型工具链骨架”，不承诺自动化产出完整英语配音补丁。
- `FreeMote` 等第三方工具应按外部依赖接入，不建议直接把上游二进制打包进本项目发布物。

## 文档

- [可行性与风险评估](docs/feasibility.zh-CN.md)
- [修订后的项目方案](docs/project-plan.zh-CN.md)

