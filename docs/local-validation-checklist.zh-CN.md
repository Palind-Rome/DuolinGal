# DuolinGal 本机验证清单

这份文档只做一件事：告诉你现在需要在自己电脑上做什么，才能把《千恋万花》的真实资源链路跑起来。

## 1. 你现在需要准备什么

你需要准备 3 类东西：

1. 正版《千恋万花》游戏目录
2. 外部工具
3. 一份本机工具链配置

### 游戏目录

理想情况下，你的游戏目录里至少能看到这些文件：

- `voice.xp3`
- `scn.xp3`
- `patch.xp3`
- `KAGParserEx.dll`
- `psbfile.dll`
- 游戏主程序 `.exe`

### 外部工具

当前最需要的是这两个：

- `KrkrExtract`
- `FreeMote` 的 `PsbDecompile.exe`

后续再考虑：

- `FFmpeg`
- `GPT-SoVITS`

## 2. 你要修改哪个文件

复制：

`configs/toolchain.example.json`

到：

`configs/toolchain.local.json`

然后把里面的路径改成你本机的真实路径。

最低限度要配好：

```json
{
  "krkrextract": {
    "path": "C:/YourPath/KrkrExtract.exe",
    "args": ["{package}", "{output}"]
  },
  "freemote": {
    "path": "C:/YourPath/PsbDecompile.exe",
    "args": ["{input}", "{output}"]
  }
}
```

注意：

- 这只是模板，不保证刚好适配你下载的工具版本
- 如果你的工具版本命令行参数不同，需要你按实际版本调整 `args`

## 3. 你要执行哪些命令

下面这组命令就是你现在最该跑的一组。

先分析并初始化项目：

```powershell
$env:PYTHONPATH='src'
python -m duolingal analyze "你的千恋万花目录"
python -m duolingal init-project "你的千恋万花目录" --project-id senren-banka
```

然后先跑预检：

```powershell
python -m duolingal preflight "D:\DuolinGal\DuolinGal\workspace\projects\senren-banka" --config configs/toolchain.local.json
```

如果推荐的是 `extract`，继续执行：

```powershell
python -m duolingal extract "D:\DuolinGal\DuolinGal\workspace\projects\senren-banka" --config configs/toolchain.local.json
```

再跑一次预检。

如果推荐的是 `decompile-scripts`，继续执行：

```powershell
python -m duolingal decompile-scripts "D:\DuolinGal\DuolinGal\workspace\projects\senren-banka" --config configs/toolchain.local.json
```

再跑一次预检。

如果推荐的是 `build-lines`，继续执行：

```powershell
python -m duolingal build-lines "D:\DuolinGal\DuolinGal\workspace\projects\senren-banka"
```

## 4. 预检报告怎么看

`preflight` 会给你三样东西：

- `overall_status`
- `checks`
- `recommended_commands`

你先看 `recommended_commands` 就够了。

最常见的 3 种情况：

- 推荐 `extract`
  说明项目还没提取出 `scn.xp3` 内容
- 推荐 `decompile-scripts`
  说明已经有 `.scn/.psb`，但还没有可供 `build-lines` 使用的 JSON
- 推荐 `build-lines`
  说明当前已经有 JSON 输入，可以直接构建 `lines.csv`

## 5. 如果失败了，你需要发给我什么

如果你跑不通，不要只告诉我“失败了”，请把下面这些信息一起给我：

1. 你执行的完整命令
2. `preflight` 的完整 JSON 输出
3. `workspace/projects/senren-banka/logs/` 下最新的日志文件
4. `configs/toolchain.local.json` 的内容

如果你不想暴露本机目录，可以把路径打码，但不要改掉参数结构。

## 6. 我最希望你先完成什么

如果你现在只做一件事，我最希望你先完成这件事：

**把 `preflight -> extract -> preflight -> decompile-scripts -> preflight` 这条链跑起来。**

原因很简单：

- 这一步最能证明项目是不是真的能做
- 这一步不依赖 TTS
- 这一步一旦跑通，后面 `lines.csv`、手工回注、GPT-SoVITS 才有意义
