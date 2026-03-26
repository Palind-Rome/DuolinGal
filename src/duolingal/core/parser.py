from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from duolingal.core.aligner import build_alignment_stub, export_alignment_csv
from duolingal.core.workspace import load_project_manifest
from duolingal.domain.models import LinesBuildResult, RawScriptNode


SPEAKER_KEYS = ("speaker_name", "speaker", "name", "character", "chara")
VOICE_KEYS = ("voice_file", "voice", "voicefile", "storage", "audio", "voicepath")
JP_KEYS = ("jp_text", "jp", "ja", "japanese", "text_jp", "message_jp")
EN_KEYS = ("en_text", "en", "english", "text_en", "message_en")
DEFAULT_TEXT_KEYS = ("text", "message")
LANGUAGE_CONTAINER_KEYS = ("texts", "languages", "lang")


def build_lines_for_project(
    project_root: str | Path,
    script_root: str | Path | None = None,
) -> LinesBuildResult:
    manifest = load_project_manifest(project_root)
    resolved_project_root = Path(manifest.workspace_path)
    resolved_script_root = _resolve_script_root(resolved_project_root, script_root)
    if not resolved_script_root.exists():
        raise ValueError(f"未找到脚本目录：{resolved_script_root}")

    json_files = sorted(resolved_script_root.rglob("*.json"))
    if not json_files:
        raise ValueError(f"在 {resolved_script_root} 下未找到可解析的 JSON 脚本。")

    nodes: list[RawScriptNode] = []
    for json_file in json_files:
        nodes.extend(parse_script_json_file(json_file, root=resolved_script_root))

    lines = build_alignment_stub(nodes)
    dataset_dir = resolved_project_root / "dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    output_path = export_alignment_csv(lines, dataset_dir / "lines.csv")
    nodes_path = _write_nodes_jsonl(nodes, dataset_dir / "script_nodes.jsonl")

    return LinesBuildResult(
        project_root=str(resolved_project_root),
        script_root=str(resolved_script_root),
        output_path=str(output_path),
        nodes_path=str(nodes_path),
        scene_count=len(json_files),
        node_count=len(nodes),
        line_count=len(lines),
    )


def parse_script_json_file(path: str | Path, root: str | Path | None = None) -> list[RawScriptNode]:
    json_path = Path(path).expanduser().resolve()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    scene_id = _scene_id_for(json_path, Path(root).expanduser().resolve() if root else None)

    nodes: list[RawScriptNode] = []
    for index, candidate in enumerate(_iter_candidate_dicts(payload)):
        node = _dict_to_node(candidate, scene_id=scene_id, order_index=index, source_path=json_path)
        if node is not None:
            nodes.append(node)
    return nodes


def _iter_candidate_dicts(payload: Any) -> Iterable[dict[str, Any]]:
    if isinstance(payload, dict):
        if _looks_like_dialogue_candidate(payload):
            yield payload
        for value in payload.values():
            yield from _iter_candidate_dicts(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from _iter_candidate_dicts(item)


def _looks_like_dialogue_candidate(payload: dict[str, Any]) -> bool:
    normalized = {key.lower() for key in payload}
    direct_keys = set(SPEAKER_KEYS) | set(VOICE_KEYS) | set(JP_KEYS) | set(EN_KEYS) | set(DEFAULT_TEXT_KEYS)
    if normalized & direct_keys:
        return True
    for container_key in LANGUAGE_CONTAINER_KEYS:
        raw_container = _get_case_insensitive(payload, container_key)
        if isinstance(raw_container, dict):
            container_keys = {key.lower() for key in raw_container}
            if container_keys & {"jp", "ja", "japanese", "en", "english"}:
                return True
    return False


def _dict_to_node(
    payload: dict[str, Any],
    scene_id: str,
    order_index: int,
    source_path: Path,
) -> RawScriptNode | None:
    normalized_keys = {key.lower() for key in payload}
    if normalized_keys and normalized_keys.issubset({"jp", "ja", "japanese", "en", "english"}):
        return None

    speaker_name = _first_string(payload, SPEAKER_KEYS)
    voice_file = _first_string(payload, VOICE_KEYS)
    jp_text = _first_string(payload, JP_KEYS)
    en_text = _first_string(payload, EN_KEYS)

    for container_key in LANGUAGE_CONTAINER_KEYS:
        raw_container = _get_case_insensitive(payload, container_key)
        if not isinstance(raw_container, dict):
            continue
        jp_text = jp_text or _first_string(raw_container, ("jp", "ja", "japanese"))
        en_text = en_text or _first_string(raw_container, ("en", "english"))

    if jp_text is None and en_text is None:
        jp_text = _first_string(payload, DEFAULT_TEXT_KEYS)

    if not any([speaker_name, voice_file, jp_text, en_text]):
        return None

    return RawScriptNode(
        scene_id=scene_id,
        order_index=order_index,
        speaker_name=speaker_name,
        jp_text=jp_text,
        en_text=en_text,
        voice_file=voice_file,
        source_path=str(source_path),
        metadata={"candidate_keys": ",".join(sorted(payload.keys()))},
    )


def _first_string(payload: dict[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = _get_case_insensitive(payload, key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _get_case_insensitive(payload: dict[str, Any], key: str) -> Any:
    for payload_key, payload_value in payload.items():
        if payload_key.lower() == key.lower():
            return payload_value
    return None


def _scene_id_for(path: Path, root: Path | None) -> str:
    if root is None:
        return path.stem
    relative = path.relative_to(root)
    return "__".join(relative.with_suffix("").parts)


def _resolve_script_root(project_root: Path, script_root: str | Path | None) -> Path:
    if script_root is not None:
        return Path(script_root).expanduser().resolve()

    preferred_root = (project_root / "decompiled_script").resolve()
    if preferred_root.exists() and any(preferred_root.rglob("*.json")):
        return preferred_root

    return (project_root / "extracted_script").resolve()


def _write_nodes_jsonl(nodes: list[RawScriptNode], destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        for node in nodes:
            handle.write(json.dumps(node.model_dump(mode="json"), ensure_ascii=False) + "\n")
    return destination
