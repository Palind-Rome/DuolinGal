# Patch 打包指南

当 `version.dll + unencrypted` 的单句 PoC 已验证成功后，或者当你已经完成整轮 GPT-SoVITS 量产与最终清理后，下一步就可以把覆盖文件树整理并打包成 `patch2.xp3`。

## 为什么还要打包

- 调试时：`unencrypted` 最快，改一个文件就能立即测
- 交付时：`patch2.xp3` 更整洁，也更接近 Kirikiri 游戏常见的补丁形式

## 准备阶段

先把已经验证成功的覆盖目录整理成补丁 staging 目录：

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-patch "<PROJECT_ROOT>" "<OVERRIDE_DIR>"
```

例如对单句 PoC：

```powershell
python -m duolingal prepare-patch "<PROJECT_ROOT>" "<PROJECT_ROOT>\\poc\\<LINE_ID>\\game-ready\\unencrypted"
```

如果你走的是“全角色量产 -> 最终清理副本”这条线，更推荐：

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-final-cleanup "<PROJECT_ROOT>"
```

然后在：

- `<PROJECT_ROOT>/tts-release/final-cleanup-v1/source/unencrypted`

这份安全副本上完成审核和删除，最后再重建 `patch-build`。

## 产物

命令会在项目目录下创建：

```text
<PROJECT_ROOT>/patch-build/
|-- patch2/
|   `-- ...override files...
|-- patch2.manifest.json
`-- pack-patch2.ps1
```

说明：

- `patch2/` 是准备给 `Xp3Pack` 打包的目录
- `patch2.manifest.json` 记录本次复制了哪些文件
- `pack-patch2.ps1` 是项目内可直接使用的打包脚本

## 当前推荐打包流程

1. 先准备或重建 `patch-build/patch2/`
2. 确保 `patch-build/` 下存在 `Xp3Pack.exe`
3. **在 `patch-build/` 目录里**运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\pack-patch2.ps1
```

4. 得到：
   - `<PROJECT_ROOT>/patch-build/patch2.xp3`
5. 再把这个 `patch2.xp3` 复制到你的游戏实验目录或正式发布目录

## 为什么要强调“在 patch-build 目录里运行”

当前 `Xp3Pack.exe` 的调用方式依赖当前工作目录。  
因此：

- 直接双击或在别的目录里调用 `pack-patch2.ps1`
- 可能会报 “Specified folder does not exist.”

更稳的做法就是：

```powershell
Set-Location "<PROJECT_ROOT>\\patch-build"
powershell -NoProfile -ExecutionPolicy Bypass -File .\pack-patch2.ps1
```

## 最终清理副本与打包的关系

如果你已经完成：

- `run-gptsovits-production`
- `prepare-final-cleanup`
- 审核 `cleanup-review.ready.csv`
- 删除清理副本中的弱句覆盖

那么推荐顺序是：

```text
量产完成
  -> prepare-final-cleanup
  -> 审核 cleanup-review
  -> 在 cleanup copy 上删除 .ogg
  -> rebuild-patch-from-clean-copy.ps1
  -> pack-patch2.ps1
  -> patch2.xp3
```

也就是说，正式 release 用的补丁，应该优先来自：

- 清理后的副本

而不是最初那棵未经收尾筛选的量产覆盖树。
