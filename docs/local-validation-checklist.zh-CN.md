# DuolinGal 本机验证清单

这份清单只做一件事：帮你在自己的电脑上把真实资源链路跑起来，同时避免把本机路径提交到 Git。

## 1. 先准备什么

你至少需要这三类东西：

1. 正版游戏目录
2. 外部工具
3. 本机工具配置文件

游戏目录里理想情况下至少有：

- `voice.xp3`
- `scn.xp3`
- `patch.xp3`
- `KAGParserEx.dll`
- `psbfile.dll`
- 游戏主程序 `.exe`

当前优先工具：

- `KrkrDump`
- `FreeMote` 的 `PsbDecompile.exe`

可选工具：

- `KrkrExtract`
- `FFmpeg`
- `GPT-SoVITS`

## 2. 哪些文件可以写真实路径

只把真实路径写进：

- `configs/toolchain.local.json`

不要把真实路径写进：

- `README.md`
- `docs/`
- `configs/toolchain.example.json`

仓库已经忽略这些本地文件：

- `configs/toolchain.local.json`
- `.env`
- `.venv/`
- `workspace/projects/`

## 3. 最小本机配置

先复制：

`configs/toolchain.example.json`

为：

`configs/toolchain.local.json`

然后只改本地副本。最小配置建议如下：

```json
{
  "krkrdump": {
    "path": "C:/YourPath/KrkrDump/KrkrDumpLoader.exe"
  },
  "freemote": {
    "path": "C:/YourPath/PsbDecompile.exe",
    "args": ["{input}", "{output}"]
  }
}
```

如果你还想保留离线 XP3 解包备用路径，再加：

```json
{
  "krkrextract": {
    "path": "C:/YourPath/KrkrExtract.exe",
    "args": ["{package}", "{output}"]
  }
}
```

## 4. 按顺序执行哪些命令

先分析并初始化项目：

```powershell
$env:PYTHONPATH='src'
python -m duolingal analyze "<GAME_DIR>"
python -m duolingal init-project "<GAME_DIR>" --project-id senren-banka
```

然后先跑预检：

```powershell
python -m duolingal preflight "<PROJECT_ROOT>" --config configs/toolchain.local.json
```

如果推荐的是 `prepare-krkrdump`，继续执行：

```powershell
python -m duolingal prepare-krkrdump "<PROJECT_ROOT>" --config configs/toolchain.local.json
```

这一步只会生成 `KrkrDump.json` 并打印本机启动命令。真正的 dump 需要你在自己的机器上运行它。

如果推荐的是 `extract`，说明当前环境更适合走离线解包：

```powershell
python -m duolingal extract "<PROJECT_ROOT>" --config configs/toolchain.local.json
```

脚本资源拿到后，再跑：

```powershell
python -m duolingal preflight "<PROJECT_ROOT>" --config configs/toolchain.local.json
python -m duolingal decompile-scripts "<PROJECT_ROOT>" --config configs/toolchain.local.json
python -m duolingal preflight "<PROJECT_ROOT>" --config configs/toolchain.local.json
python -m duolingal build-lines "<PROJECT_ROOT>"
```

## 5. `preflight` 重点看什么

你优先看：

- `overall_status`
- `recommended_commands`

常见情况：

- 推荐 `prepare-krkrdump`
  说明项目还没有脚本资源，但 `KrkrDump` 已经可用。
- 推荐 `extract`
  说明项目打算走离线 XP3 提取。
- 推荐 `decompile-scripts`
  说明已经有 `.scn/.psb/.psb.m`，但还没有 JSON。
- 推荐 `build-lines`
  说明已经有 JSON，可以生成 `lines.csv`。

## 6. 如果失败了，发我什么

如果某一步没跑通，请把下面这些信息一起发我：

1. 你执行的完整命令
2. `preflight` 的完整 JSON 输出
3. `workspace/projects/<PROJECT_ID>/logs/` 里最新的日志文件
4. `configs/toolchain.local.json` 的内容

如果你不想暴露本机目录，可以把路径打码，但不要改参数结构。
