"""Discover GEOS QuickPlot recipes without executing portrait.script.

Read the installed portrait definitions directly. Running portrait.script
-list can be expensive (and timed out on Discover in October 2026).
"""
import re
from pathlib import Path

GENPLOT = re.compile(r'run\s+genplot\s+-EXPORT\s+(.+?)\s+-NAME\s+(\S+)', re.I)
FIELD = re.compile(r'\b([A-Za-z][A-Za-z0-9_]*)\:([A-Za-z][A-Za-z0-9_]*)\b')


def verification_catalog(geosutil):
    folder = Path(geosutil) / "plots/VERIFICATION_RCS"
    return sorted(p.name for p in folder.glob("VERIFICATION.*.rc") if p.is_file())


def discover(geosutil, source, data, names, levels):
    """Select direct native genplot recipes based on source export dependencies.

    The native recipe definition, variable name and product naming remain
    authoritative; do not infer new variable-to-observation mappings.
    """
    portrait = Path(geosutil) / "plots/portrait.script"
    if not portrait.is_file():
        return [], [{"reason": "GEOS portrait.script unavailable"}]
    try:
        source_text = portrait.read_text(errors="replace")
    except OSError as exc:
        return [], [{"reason": "Unable to read portrait.script: " + str(exc)}]

    selected = {(f["export"], f["component"]) for col in names for f in data[col]}
    available = {(f["export"], f["component"]) for fields in data.values() for f in fields}
    tasks, skipped, seen = [], [], set()
    for line in source_text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        match = GENPLOT.search(line)
        if not match:
            continue
        sources = FIELD.findall(match.group(1))
        name = match.group(2).strip()
        if not sources or not any(src in selected for src in sources):
            continue
        key = (name, tuple(sources))
        if key in seen:
            continue
        seen.add(key)
        missing = [f"{v}:{gc}" for v, gc in sources if (v, gc) not in available]
        task = {"collection": names[0] if len(names) == 1 else "diagnostics",
                "resolved_collection": "native", "variable": name,
                "component": "QUICKPLOT", "kind": "native",
                "plot_id": name, "level": None, "dimension": "derived",
                "compare": True, "exports": [f"{v}:{gc}" for v, gc in sources]}
        if missing:
            skipped.append(dict(task, reason="missing exports: " + ", ".join(missing)))
        else:
            tasks.append(task)

    if not tasks:
        skipped.append({"reason": "No eligible genplot recipes for selected collection",
                        "selected_exports": len(selected), "matching_recipes": len(seen)})
    return tasks, skipped


def prepare_legacy_genplot(geosutil, work):
    """Compatibility hook retained for historical callers (no mutation)."""
    return None
