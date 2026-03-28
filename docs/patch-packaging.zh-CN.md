# Patch 打包指南

当 `version.dll + unencrypted` 的单句 PoC 已验证成功后，下一步就可以把相同的覆盖文件树整理成 `patch2.xp3`。

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
- `pack-patch2.ps1` 是在本地游戏实验目录中使用的打包脚本

## 你手动要做的事

1. 把 `patch-build/patch2/` 整个目录复制到你的本地游戏实验目录
2. 确保 `Xp3Pack.exe` 可用
3. 在那个实验目录里运行 `pack-patch2.ps1`
4. 得到 `patch2.xp3` 后，和 `version.dll` 一起测试

## 为什么 DuolinGal 现在只做到 staging

因为真正打包时会涉及：

- 你本地的 `Xp3Pack.exe`
- 你本机实验目录
- 你的实际补丁命名策略

这些都属于本地外部工具链范围，不适合让仓库直接写入你的游戏目录。
