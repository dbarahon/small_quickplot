"""Discover GEOS QuickPlot recipes without executing portrait.script.

Read the installed portrait definitions directly. Running portrait.script
-list can be expensive (and timed out on Discover in October 2026).
"""
import re
from pathlib import Path

SUPPORTED_RCS = {
    "VERIFICATION.CERES_EBAF-TOA_Ed4.0.rc",
    "VERIFICATION.ERA5.rc",
    "VERIFICATION.GPCP.rc",
    "VERIFICATION.ISCCP.rc",
    "VERIFICATION.MAC-LWP.rc",
    "VERIFICATION.SRB.rc",
}
GENPLOT = re.compile(r'run\s+genplot\s+-EXPORT\s+(.+?)\s+-NAME\s+(\S+)', re.I)
FIELD = re.compile(r'\b([A-Za-z][A-Za-z0-9_]*)\:([A-Za-z][A-Za-z0-9_]*)\b')


def verification_catalog(geosutil):
    folder = Path(geosutil) / "plots/VERIFICATION_RCS"
    return sorted(p.name for p in folder.glob("VERIFICATION.*.rc")
                  if p.is_file() and p.name in SUPPORTED_RCS)


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
    allowed = set(verification_catalog(geosutil))
    def has_obs(name):
        folder = Path(geosutil) / "plots" / name
        return any((folder / rc).is_file() for rc in allowed)

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
        if not has_obs(name):
            continue
        task = {"collection": names[0] if len(names) == 1 else "diagnostics",
                "resolved_collection": "native", "variable": name,
                "component": "QUICKPLOT", "kind": "native",
                "plot_id": name, "level": None, "dimension": "derived",
                "compare": True, "exports": [f"{v}:{gc}" for v, gc in sources]}
        if missing:
            skipped.append(dict(task, reason="missing exports: " + ", ".join(missing)))
        else:
            tasks.append(task)

    # GEOS also has dedicated multi-panel observational recipes not expressed
    # as genplot -EXPORT lines in portrait.script.
    dedicated = {
        "precip": ("precip/precip", (("CN_PRCP", "MOIST"), ("LS_PRCP", "MOIST"),
                                    ("AN_PRCP", "MOIST"))),
        "toa_radz": ("olr/olr", (("OLR", "IRRAD"), ("OLC", "IRRAD"),
                                ("RSR", "SOLAR"), ("RSC", "SOLAR"))),
    }
    for name, (script, sources) in dedicated.items():
        if not any(src in selected for src in sources):
            continue
        missing = [f"{v}:{gc}" for v, gc in sources if (v, gc) not in available]
        if name == "precip" and missing and ("TPREC", "MOIST") in available:
            missing = []
        if missing:
            skipped.append({"variable": name, "reason": "missing exports: " + ", ".join(missing)})
        else:
            tasks.append({"collection": names[0] if len(names) == 1 else "diagnostics",
                          "resolved_collection": "native", "variable": name,
                          "component": "QUICKPLOT", "kind": "native_special",
                          "script": script, "level": None, "dimension": "derived",
                          "compare": True, "exports": [f"{v}:{gc}" for v, gc in sources]})
    if not tasks:
        skipped.append({"reason": "No eligible genplot recipes for selected collection",
                        "selected_exports": len(selected), "matching_recipes": len(seen)})
    return tasks, skipped


def prepare_legacy_genplot(geosutil, work):
    """Compatibility hook retained for historical callers (no mutation)."""
    return None
