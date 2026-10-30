"""Discover native GEOS QuickPlot verification recipes from portrait.script.

The installed portrait.script is the authority on recipe definitions and plot
IDs. It documents "-v -list" as the supported way to enumerate those IDs.
"""
import re
import subprocess

PLOT_ID = re.compile(r"\bPORTRAIT\.([0-9]+)\b")
EXPORT_SECTION = re.compile(r"-EXPORT\s+(.+?)(?=\s+-[A-Za-z][A-Za-z_-]*\b|[\"']|$)")
FIELD = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*)\:([A-Za-z][A-Za-z0-9_]*)\b")
NAME = re.compile(r"-NAME\s+([A-Za-z][A-Za-z0-9_.-]*)")


def discover(geosutil, source, data, names):
    """Return native genplot recipes supported by the requested collections.

    All installed GEOS verification resource mappings remain authoritative.
    No verification files are fabricated or replaced.
    """
    script = geosutil / "plots/portrait.script"
    if not script.is_file():
        return [], [{"reason": "GEOS portrait.script unavailable"}]
    try:
        result = subprocess.run(
            ["tcsh", "-f", str(script), "-v", "-list", "-source", str(source)],
            capture_output=True, text=True, timeout=90, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [], [{"reason": "QuickPlot recipe enumeration failed: " + str(exc)}]
    if result.returncode != 0:
        return [], [{"reason": "QuickPlot recipe listing failed: " +
                     (result.stderr[-500:] or str(result.returncode))}]
    selected = {(f["export"], f["component"]) for col in names for f in data[col]}
    available = {(f["export"], f["component"]) for fields in data.values() for f in fields}
    recipes = []
    skipped = []
    seen = set()
    for line in (result.stdout + "\n" + result.stderr).splitlines():
        if "run genplot" not in line or "-EXPORT" not in line:
            continue
        number = PLOT_ID.search(line)
        fields = EXPORT_SECTION.search(line)
        if not number or not fields:
            continue
        sources = [tuple(x) for x in FIELD.findall(fields.group(1))]
        if not sources or not any(x in selected for x in sources):
            continue
        pid = "PORTRAIT." + number.group(1)
        if pid in seen:
            continue
        seen.add(pid)
        title = NAME.search(line)
        name = title.group(1) if title else "plot" + number.group(1)
        missing = [a + ":" + b for a, b in sources if (a, b) not in available]
        common = {"collection": names[0] if len(names) == 1 else "diagnostics",
                  "resolved_collection": "native", "variable": name,
                  "component": "QUICKPLOT", "kind": "native",
                  "plot_id": pid, "level": None, "dimension": "derived",
                  "compare": True, "exports": [a + ":" + b for a, b in sources]}
        if missing:
            skipped.append(dict(common, reason="missing " + ", ".join(missing)))
        else:
            recipes.append(common)
    if not recipes:
        skipped.append({"reason": "No matching native verification recipes found in portrait listing"})
    return recipes, skipped


def prepare_legacy_genplot(geosutil, work):
    """Avoid OpenGrADS 2.0.1 monthly-time sdfwrite for native genplot recipes.

    GEOS makplotz uses the temporary RGFILE only as the model grid reference.
    Use the already-open model file rather than rewriting the time axis.
    This local adaptation is experimental and never modifies GEOSUTIL.
    """
    source = geosutil / "plots/grads_util/genplot.gs"
    text = source.read_text()
    start = text.find("  'define qmodr = qmod'")
    end = text.find("              rgfile = result", start)
    if start < 0 or end < 0:
        raise RuntimeError("Unrecognized installed genplot.gs; refusing compatibility patch")
    end += len("              rgfile = result")
    text = text[:start] + "  rgfile = qfile.1\n" + text[end:]
    (work / "genplot.gs").write_text(text)

def verification_catalog(geosutil):
    """Return exactly the installed GEOS VERIFICATION_RCS catalog entries."""
    folder = geosutil / "plots/VERIFICATION_RCS"
    return sorted(p.name for p in folder.glob("VERIFICATION.*.rc") if p.is_file())


def prepare_verification_selector(geosutil, work):
    """Constrain getnumrc discovery to the installed VERIFICATION_RCS catalog.

    MERRA-2/ERA5 operational comparisons are independent CMPEXP datasets.
    If a GEOS installation lacks the catalog, preserve its native behavior.
    """
    allowed = verification_catalog(geosutil)
    if not allowed:
        return
    import shlex
    shell = [
        "#!/bin/sh",
        "dir=$1",
        ": > rcfiles.selected",
        'for rc in "$dir"/VERIFICATION*.rc; do',
        '  [ -f "$rc" ] || continue',
        '  case "${rc##*/}" in',
        "    " + "|".join(shlex.quote(n) for n in allowed) + ")",
        '       printf "%s\\n" "$rc" >> rcfiles.selected ;;',
        "  esac",
        "done",
        "wc -l < rcfiles.selected > rcfiles",
        "cat rcfiles.selected >> rcfiles",
    ]
    (work / "filter_verification.sh").write_text("\\n".join(shell) + "\\n")
    (work / "getnumrc.gs").write_text(
        "function getnumrc(args)\\n"
        "dir = subwrd(args,1)\\n"
        "'!/bin/sh ./filter_verification.sh 'dir\\n"
        "numrc = sublin(read('rcfiles'),2)\\n"
        "resultstr = numrc\\n"
        "k = 1\\n"
        "while (k <= numrc)\\n"
        "  file = sublin(read('rcfiles'),2)\\n"
        "  resultstr = resultstr' 'file\\n"
        "  k = k + 1\\n"
        "endwhile\\n"
        "return resultstr\\n"
    )
