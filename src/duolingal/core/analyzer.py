from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from duolingal.domain.models import ConfidenceLevel, GameAnalysis, PackageInfo


@dataclass(frozen=True)
class KnownGameDefinition:
    game_id: str
    title: str
    engine: str
    script_format: str
    voice_language: str
    text_languages: tuple[str, ...]
    required_files: frozenset[str]
    supporting_files: frozenset[str]
    package_keywords: frozenset[str]


SENREN_BANKA = KnownGameDefinition(
    game_id="senren_banka",
    title="千恋万花",
    engine="kirikiri_z",
    script_format="scn_psb",
    voice_language="jp",
    text_languages=("jp", "en", "zh-hans", "zh-hant"),
    required_files=frozenset({"voice.xp3", "scn.xp3"}),
    supporting_files=frozenset({"patch.xp3", "kagparserex.dll", "psbfile.dll"}),
    package_keywords=frozenset({"senren", "banka"}),
)

KNOWN_GAMES = (SENREN_BANKA,)


def analyze_game_directory(root: str | Path) -> GameAnalysis:
    root_path = Path(root).expanduser().resolve()
    if not root_path.exists():
        return GameAnalysis(
            root_path=str(root_path),
            exists=False,
            warnings=["游戏目录不存在。"],
        )

    files = _scan_files(root_path)
    package_infos = [
        PackageInfo(name=path.name, relative_path=str(path.relative_to(root_path)))
        for path in files
        if path.suffix.lower() == ".xp3"
    ]
    dlls = sorted(path.name for path in files if path.suffix.lower() == ".dll")
    executables = sorted(path.name for path in files if path.suffix.lower() == ".exe")
    file_names = {path.name for path in files}
    normalized_file_names = {name.lower() for name in file_names}

    matched_game = _match_known_game(normalized_file_names, executables)
    warnings: list[str] = []
    notes: list[str] = []
    matched_signatures: list[str] = []

    engine = None
    confidence = ConfidenceLevel.LOW
    supported = False
    candidate_title = None
    script_format = None
    voice_language = None
    text_languages: list[str] = []
    game_id = None

    if package_infos:
        notes.append("目录中发现 XP3 资源包，符合 KiriKiri 系作品的基本特征。")
        matched_signatures.append("xp3-packages")

    if {"kagparserex.dll", "psbfile.dll"} & normalized_file_names:
        engine = "kirikiri_z"
        notes.append("检测到 KAG/PSB 相关 DLL，倾向于 KiriKiri Z + SCN/PSB 流程。")
        matched_signatures.append("kirikiri-z-dlls")
        confidence = ConfidenceLevel.MEDIUM

    if matched_game is not None:
        supported = True
        game_id = matched_game.game_id
        candidate_title = matched_game.title
        engine = matched_game.engine
        script_format = matched_game.script_format
        voice_language = matched_game.voice_language
        text_languages = list(matched_game.text_languages)
        confidence = ConfidenceLevel.HIGH
        matched_signatures.extend(sorted(matched_game.required_files & normalized_file_names))
        matched_signatures.extend(sorted(matched_game.supporting_files & normalized_file_names))
        notes.append(
            "当前目录与《千恋万花》Steam 版的已知资源布局高度相符，适合做第一阶段验证样本。"
        )
    else:
        warnings.append("尚未匹配到当前仓库支持的单作品指纹，后续需要扩展定义或人工确认。")

    if "voice.xp3" not in normalized_file_names:
        warnings.append("未找到 voice.xp3，语音提取链路暂时无法确认。")
    if "scn.xp3" not in normalized_file_names:
        warnings.append("未找到 scn.xp3，脚本/场景提取链路暂时无法确认。")

    if package_infos and "patch.xp3" in normalized_file_names:
        notes.append("发现 patch.xp3，可作为后续覆盖式补丁验证的参考。")

    return GameAnalysis(
        root_path=str(root_path),
        exists=True,
        game_id=game_id,
        candidate_title=candidate_title,
        engine=engine,
        script_format=script_format,
        voice_language=voice_language,
        text_languages=text_languages,
        confidence=confidence,
        supported=supported,
        matched_signatures=sorted(dict.fromkeys(matched_signatures)),
        packages=sorted(package_infos, key=lambda item: item.relative_path.lower()),
        dlls=dlls,
        executables=executables,
        warnings=warnings,
        notes=notes,
    )


def sanitize_project_id(raw: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    return slug or "project"


def _scan_files(root: Path, max_depth: int = 3) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            depth = len(path.relative_to(root).parts)
        except ValueError:
            continue
        if depth <= max_depth:
            files.append(path)
    return files


def _match_known_game(file_names: set[str], executables: list[str]) -> KnownGameDefinition | None:
    executable_names = [name.lower() for name in executables]
    for definition in KNOWN_GAMES:
        if not definition.required_files.issubset(file_names):
            continue
        if _matches_executable_keywords(executable_names, definition.package_keywords):
            return definition
        if definition.supporting_files & file_names:
            return definition
    return None


def _matches_executable_keywords(executables: list[str], keywords: frozenset[str]) -> bool:
    for executable in executables:
        stem = Path(executable).stem
        if all(keyword in stem for keyword in keywords):
            return True
    return False
