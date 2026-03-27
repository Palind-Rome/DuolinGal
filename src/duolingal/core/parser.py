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
RESX_JSON_SUFFIX = ".resx.json"


def build_lines_for_project(
    project_root: str | Path,
    script_root: str | Path | None = None,
) -> LinesBuildResult:
    manifest = load_project_manifest(project_root)
    resolved_project_root = Path(manifest.workspace_path)
    resolved_script_root = _resolve_script_root(resolved_project_root, script_root)
    if not resolved_script_root.exists():
        raise ValueError(f"Script directory does not exist: {resolved_script_root}")

    json_files = sorted(_iter_script_json_files(resolved_script_root))
    if not json_files:
        raise ValueError(f"No parseable JSON script files were found under: {resolved_script_root}")

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

    structured_nodes = _parse_senren_scene_text_nodes(
        payload,
        scene_id=scene_id,
        source_path=json_path,
    )
    if structured_nodes:
        return structured_nodes

    nodes: list[RawScriptNode] = []
    for index, candidate in enumerate(_iter_candidate_dicts(payload)):
        node = _dict_to_node(candidate, scene_id=scene_id, order_index=index, source_path=json_path)
        if node is not None:
            nodes.append(node)
    return nodes


def _parse_senren_scene_text_nodes(
    payload: Any,
    scene_id: str,
    source_path: Path,
) -> list[RawScriptNode]:
    if not isinstance(payload, dict):
        return []

    raw_scenes = payload.get("scenes")
    if not isinstance(raw_scenes, list):
        return []

    nodes: list[RawScriptNode] = []
    for scene_index, scene in enumerate(raw_scenes):
        if not isinstance(scene, dict):
            continue

        raw_texts = scene.get("texts")
        if not isinstance(raw_texts, list):
            continue

        for text_index, entry in enumerate(raw_texts):
            node = _scene_text_entry_to_node(
                entry,
                scene_id=scene_id,
                order_index=len(nodes),
                source_path=source_path,
                scene_index=scene_index,
                text_index=text_index,
                scene=scene,
            )
            if node is not None:
                nodes.append(node)

    return nodes


def _scene_text_entry_to_node(
    entry: Any,
    scene_id: str,
    order_index: int,
    source_path: Path,
    scene_index: int,
    text_index: int,
    scene: dict[str, Any],
) -> RawScriptNode | None:
    if not isinstance(entry, list) or len(entry) < 3:
        return None

    texts = _extract_language_rows(entry[2])
    jp_text = texts.get("jp")
    en_text = texts.get("en")
    cn_text = texts.get("cn")
    tw_text = texts.get("tw")

    voice_id, voice_speaker = _extract_voice_metadata(entry[3] if len(entry) > 3 else None)
    speaker_name = _normalize_string(entry[0]) or voice_speaker
    voice_file = _normalize_voice_file(voice_id)

    if not any([speaker_name, voice_file, jp_text, en_text, cn_text, tw_text]):
        return None

    metadata: dict[str, str] = {
        "source_format": "senren_scene_texts",
        "scene_index": str(scene_index),
        "text_index": str(text_index),
    }
    if cn_text:
        metadata["cn_text"] = cn_text
    if tw_text:
        metadata["tw_text"] = tw_text
    if voice_id:
        metadata["voice_id"] = voice_id
    if len(entry) > 4 and isinstance(entry[4], int):
        metadata["duration_ms"] = str(entry[4])

    scene_label = _normalize_string(scene.get("label"))
    if scene_label:
        metadata["scene_label"] = scene_label
    scene_title = _normalize_string(scene.get("title"))
    if scene_title:
        metadata["scene_title"] = scene_title

    return RawScriptNode(
        scene_id=scene_id,
        order_index=order_index,
        speaker_name=speaker_name,
        jp_text=jp_text,
        en_text=en_text,
        voice_file=voice_file,
        source_path=str(source_path),
        metadata=metadata,
    )


def _extract_language_rows(raw_rows: Any) -> dict[str, str | None]:
    normalized = {"jp": None, "en": None, "cn": None, "tw": None}
    if not isinstance(raw_rows, list):
        return normalized

    language_order = ("jp", "en", "cn", "tw")
    for index, row in enumerate(raw_rows):
        if index >= len(language_order):
            break
        if not isinstance(row, list) or len(row) < 2:
            continue
        text = _normalize_string(row[1])
        if text:
            normalized[language_order[index]] = text

    return normalized


def _extract_voice_metadata(raw_voice_entries: Any) -> tuple[str | None, str | None]:
    if not isinstance(raw_voice_entries, list):
        return None, None

    for item in raw_voice_entries:
        if not isinstance(item, dict):
            continue
        voice_id = _normalize_string(item.get("voice"))
        speaker_name = _normalize_string(item.get("name"))
        if voice_id:
            return voice_id, speaker_name

    return None, None


def _normalize_voice_file(raw_voice_id: str | None) -> str | None:
    voice_id = _normalize_string(raw_voice_id)
    if not voice_id:
        return None
    if Path(voice_id).suffix:
        return voice_id
    return f"{voice_id}.ogg"


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


def _iter_script_json_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*.json"):
        if path.name.endswith(RESX_JSON_SUFFIX):
            continue
        yield path


def _scene_id_for(path: Path, root: Path | None) -> str:
    if root is None:
        return path.stem
    relative = path.relative_to(root)
    return "__".join(relative.with_suffix("").parts)


def _resolve_script_root(project_root: Path, script_root: str | Path | None) -> Path:
    if script_root is not None:
        return Path(script_root).expanduser().resolve()

    preferred_root = (project_root / "decompiled_script").resolve()
    if preferred_root.exists() and any(_iter_script_json_files(preferred_root)):
        return preferred_root

    return (project_root / "extracted_script").resolve()


def _write_nodes_jsonl(nodes: list[RawScriptNode], destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        for node in nodes:
            handle.write(json.dumps(node.model_dump(mode="json"), ensure_ascii=False) + "\n")
    return destination


def _normalize_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
