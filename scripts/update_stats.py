#!/usr/bin/env python3
"""Regenerate stats.svg and top-langs.svg from live GitHub API data.

Uses only the Python standard library plus the `gh` CLI. The caller (local
shell or .github/workflows/update-stats.yml) must export GH_TOKEN.

Language percentages are computed against the TOTAL number of language bytes
across ALL languages in all non-fork repos. The top 8 languages are listed
individually and everything else is aggregated into an "Other" row, so the
displayed percentages always add up to 100.0%.
"""

import json
import math
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OWNER = "TheFirstIstari"
TOP_N = 8

# --- shared SVG chrome -------------------------------------------------------
BG = "#0d1117"
TEXT_BRIGHT = "#e6edf3"
TEXT_DIM = "#7d8590"
OTHER_COLOR = "#8b949e"  # GitHub gray

FONT_STACK = "-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif"

# Donut geometry
CENTER = (110.0, 105.0)
OUTER_R = 80.0
INNER_R = 50.0

# Legend geometry (9 rows must fit inside height 195)
LEGEND_X = 210
SWATCH = 10
SWATCH_RX = 2
ROW_START_Y = 34
ROW_STEP = 18
NAME_X = 226
NAME_SIZE = 11
PERCENT_X = 364
PERCENT_SIZE = 10

# Standard github-linguist colors. Anything not listed falls back to OTHER_COLOR.
LANGUAGE_COLORS = {
    "1C Enterprise": "#814514",
    "ABAP": "#E8274B",
    "AGS Script": "#B9D9FF",
    "AMPL": "#E6EFBB",
    "ANTLR": "#9DC3FF",
    "API Blueprint": "#2A5CAA",
    "APL": "#5A8164",
    "ASP": "#6A40FD",
    "ATS": "#1AC620",
    "ActionScript": "#882B0F",
    "Ada": "#02f88c",
    "Agda": "#315665",
    "Alloy": "#64C800",
    "AngelScript": "#C7D7DC",
    "ApacheConf": "#D12127",
    "AppleScript": "#101F1F",
    "Arc": "#aa2afe",
    "AsciiDoc": "#73a0c5",
    "AspectJ": "#a957b0",
    "Assembly": "#6E4C13",
    "Asymptote": "#ff0000",
    "Astro": "#ff5a03",
    "AutoHotkey": "#6594b9",
    "AutoIt": "#1C3552",
    "Awk": "#c30e9b",
    "Ballerina": "#FF5000",
    "Batchfile": "#C1F12E",
    "Beef": "#a52f4e",
    "Bicep": "#519aba",
    "Blade": "#f7523f",
    "BlitzMax": "#cd6400",
    "Boo": "#d4bec1",
    "Brainfuck": "#2F2530",
    "Brightscript": "#662A8B",
    "C": "#555555",
    "C#": "#7355dd",
    "C++": "#f34b7d",
    "C-ObjDump": "#aaa692",
    "C2hs Haskell": "#3e0347",
    "CLIPS": "#db901e",
    "CMake": "#DA3434",
    "COBOL": "#005CA5",
    "CSS": "#563d7c",
    "CSV": "#237346",
    "CWeb": "#0F6FC5",
    "Cabal Config": "#c5afe4",
    "Caddyfile": "#0F6FC5",
    "Cap'n Proto": "#c42727",
    "Ceylon": "#dfa535",
    "Chapel": "#8dc63f",
    "Cirru": "#ccccff",
    "Clarion": "#db901e",
    "Clarity": "#5546ff",
    "Classic ASP": "#6A40FD",
    "Clojure": "#db5855",
    "CodeQL": "#140f46",
    "CoffeeScript": "#244776",
    "ColdFusion": "#ed2cd6",
    "Common Lisp": "#3fb68b",
    "Common Workflow Language": "#B5314C",
    "Coq": "#d0b68c",
    "Crystal": "#000100",
    "Cuda": "#3A4E3A",
    "Cycript": "#ffff00",
    "Cython": "#fedf5b",
    "D": "#ba595e",
    "DIGITAL Command Language": "#555555",
    "DM": "#447265",
    "DNS Zone": "#1B50F1",
    "DTrace": "#c7c7c7",
    "Dafny": "#FFEC25",
    "Dart": "#00B4AB",
    "DataWeave": "#003a52",
    "Dockerfile": "#384d54",
    "Dogescript": "#cca760",
    "Dylan": "#6c616e",
    "E": "#ccce35",
    "ECL": "#8a1267",
    "EJS": "#a91e50",
    "EQ": "#a78649",
    "Eagle": "#9078A3",
    "Easybuild": "#C1C1C1",
    "Ecere Projects": "#6390AE",
    "EditorConfig": "#f1f1f1",
    "Edje Data Collection": "#C5A121",
    "Elixir": "#6e4a7e",
    "Elm": "#60B5CC",
    "Emacs Lisp": "#c065db",
    "EmberScript": "#FFF4F3",
    "Erlang": "#B83998",
    "F#": "#b845fc",
    "F*": "#572E30",
    "FIGlet Font": "#59ff5b",
    "FIRRTL": "#5FA493",
    "FORTRAN": "#4d41b1",
    "Factor": "#636746",
    "Fancy": "#7b9db4",
    "Fantom": "#14253c",
    "Faust": "#c37240",
    "Fennel": "#fff3d7",
    "Fluent": "#ffcc33",
    "Forth": "#341708",
    "Fortran": "#4d41b1",
    "FreeBasic": "#141AC9",
    "FreeMarker": "#0050b2",
    "Frege": "#00cafe",
    "Futhark": "#5f021f",
    "G-code": "#D08CF2",
    "GAML": "#FFC766",
    "GAMS": "#f49a22",
    "GAP": "#0000cc",
    "GCC Machine Description": "#FF9E9D",
    "GDB": "#c56f3d",
    "GDScript": "#355570",
    "GLSL": "#5686a5",
    "GN": "#000000",
    "Game Maker Language": "#71b417",
    "Genie": "#FB855D",
    "Genshi": "#492F27",
    "Gentoo Ebuild": "#A4A639",
    "Gentoo Eclass": "#A4A639",
    "Gerber Image": "#d87941",
    "Gettext Catalog": "#f49a22",
    "Gherkin": "#5B2063",
    "Git Attributes": "#F44D27",
    "Git Config": "#F44D27",
    "Glyph": "#c1ac7f",
    "Gnuplot": "#f0a9f0",
    "Go": "#00ADD8",
    "Golo": "#88562A",
    "Gosu": "#82937f",
    "Grace": "#615f8b",
    "Gradle": "#02303a",
    "Graph Modeling Language": "#F3A007",
    "GraphQL": "#e10098",
    "Graphviz (DOT)": "#2593b8",
    "Groovy": "#4298b8",
    "Groovy Server Pages": "#4298b8",
    "HAProxy": "#40E4C0",
    "HCL": "#844FBA",
    "HTML": "#e34c26",
    "HTML+Django": "#e34c26",
    "HTML+ECR": "#e34c26",
    "HTML+EEX": "#e34c26",
    "HTML+ERB": "#e34c26",
    "HTML+PHP": "#e34c26",
    "HTML+Razor": "#a50e25",
    "HTTP": "#005CA5",
    "Hack": "#878787",
    "Haml": "#ece2a9",
    "Handlebars": "#f7931e",
    "Harbour": "#284584",
    "Haskell": "#5e5086",
    "Haxe": "#df7900",
    "HCL": "#844FBA",
    "HLSL": "#aace60",
    "HolyC": "#ffefaf",
    "Hy": "#7790B2",
    "IDL": "#a3522f",
    "IGOR Pro": "#0000cc",
    "INI": "#d1dbe0",
    "IRC log": "#cf2e2e",
    "Idris": "#b30000",
    "Ignore List": "#000000",
    "Inform 7": "#6d3d6a",
    "Inno Setup": "#264f99",
    "Io": "#a9188d",
    "Ioke": "#078193",
    "Isabelle": "#FEFE00",
    "J": "#9EEDFF",
    "JFlex": "#DBCA00",
    "JSON": "#292929",
    "JSON5": "#267CB9",
    "JSONLD": "#8055DF",
    "JSONiq": "#0066bd",
    "JSX": "#f1e05a",
    "Jade": "#a86454",
    "Java": "#b07219",
    "Java Server Pages": "#6A40FD",
    "JavaScript": "#f1e05a",
    "Jison": "#56AEBF",
    "Jison Lex": "#56AEBF",
    "Jolie": "#843179",
    "Jq": "#c7254e",
    "Julia": "#a270ba",
    "Jupyter Notebook": "#DA5B0B",
    "KRL": "#28430A",
    "KiCad Layout": "#f4a731",
    "KiCad Legacy Layout": "#f4a731",
    "KiCad Schematic": "#f4a731",
    "Kit": "#4D8E96",
    "Kotlin": "#A97BFF",
    "LFE": "#4C3023",
    "LLVM": "#185619",
    "LOLCODE": "#cc9900",
    "LSL": "#3b3c6d",
    "LabVIEW": "#fede06",
    "Lasso": "#999999",
    "Latte": "#f2a542",
    "Lean": "#e8e8e8",
    "Less": "#1d365d",
    "Lex": "#DBCA00",
    "LilyPond": "#9ccc7c",
    "Liquid": "#67b8de",
    "Literate Agda": "#315665",
    "Literate CoffeeScript": "#244776",
    "Literate Haskell": "#5e5086",
    "LiveScript": "#499886",
    "Logos": "#425D66",
    "Logtalk": "#295b9a",
    "Lua": "#000080",
    "M": "#d0d0d0",
    "M4": "#a569bd",
    "MAXScript": "#c7a1c7",
    "MTML": "#b3bcef",
    "MUF": "#000000",
    "Macaulay2": "#d8ffff",
    "Makefile": "#427819",
    "Mako": "#7fc0de",
    "Markdown": "#083fa1",
    "Marko": "#42bff2",
    "Mask": "#f7b09c",
    "Mathematica": "#dd1100",
    "Matlab": "#e16737",
    "Max": "#c4a79c",
    "Mercury": "#ff2b2b",
    "Meson": "#007800",
    "Metal": "#8f14e9",
    "Microsoft Developer Studio Project": "#6A40FD",
    "MiniD": "#ff6c3a",
    "Mirah": "#a7a7a7",
    "Modelica": "#de1d31",
    "Modula-2": "#10253f",
    "Module Management System": "#10253f",
    "Monkey": "#8D6747",
    "Moocode": "#8D6747",
    "MoonScript": "#ff4585",
    "Motorola 68K Assembly": "#f8f0da",
    "Muse": "#7ab5bd",
    "Mustache": "#724b3b",
    "Myghty": "#f3a507",
    "NASL": "#126578",
    "NCL": "#28431f",
    "NL": "#f1f1f1",
    "NSIS": "#9296C2",
    "Nearley": "#990000",
    "Nemerle": "#3D3C6E",
    "NetLinx": "#0aa0ff",
    "NetLinx+ERB": "#0aa0ff",
    "NetLogo": "#ff6375",
    "NewLisp": "#87AED7",
    "Nextflow": "#3ac486",
    "Nginx": "#009639",
    "Nim": "#ffc200",
    "Nit": "#009917",
    "Nix": "#7e7eff",
    "Nu": "#c9df40",
    "NumPy": "#9C8AF9",
    "OCaml": "#3be133",
    "ObjDump": "#c56f3d",
    "Objective-C": "#438eff",
    "Objective-C++": "#6866fb",
    "Objective-J": "#ff0c5a",
    "Omgrofl": "#cabbff",
    "Opa": "#0563a1",
    "Opal": "#f7ede0",
    "Open Policy Agent": "#7d9199",
    "OpenCL": "#ed2e2d",
    "OpenQASM": "#AA70FF",
    "OpenRC runscript": "#3c8a8c",
    "OpenSCAD": "#e5cd45",
    "OpenStep Property List": "#d64a4a",
    "Org": "#77aa99",
    "Oxygene": "#cdd0e3",
    "Oz": "#fab738",
    "P4": "#7055b5",
    "PAWN": "#dbb284",
    "PHP": "#4F5D95",
    "PLpgSQL": "#336790",
    "PLSQL": "#dad8d8",
    "PLpgSQL": "#336790",
    "POV-Ray SDL": "#e8e8e8",
    "Pan": "#cc0000",
    "Papyrus": "#6600cc",
    "Parrot": "#12B3F3",
    "Parrot Assembly": "#12B3F3",
    "Parrot Internal Representation": "#12B3F3",
    "Pascal": "#E3F171",
    "Pep8": "#C76F5B",
    "Perl": "#0298c3",
    "Perl 6": "#0000fb",
    "Pickle": "#009900",
    "PicoLisp": "#006795",
    "PigLatin": "#cd0d3c",
    "Pike": "#005394",
    "PlantUML": "#56AEBF",
    "Pod": "#0000cc",
    "Pod 6": "#0000cc",
    "PogoScript": "#d80074",
    "Pony": "#289FAC",
    "PostCSS": "#dc3a0c",
    "PostScript": "#da291c",
    "PowerBuilder": "#8F0F8D",
    "PowerShell": "#012456",
    "Prisma": "#0c344b",
    "Processing": "#0096D8",
    "Prolog": "#74283c",
    "Propeller Spin": "#F4AABB",
    "Protocol Buffer": "#4B6B95",
    "Public Key": "#3DAFC7",
    "Pug": "#a86454",
    "Puppet": "#302B6D",
    "Pure Data": "#e9dc3c",
    "PureBasic": "#5a6986",
    "PureScript": "#1D222D",
    "Python": "#3572A5",
    "q": "#0040cd",
    "Q#": "#fed659",
    "QML": "#44a51c",
    "Qt Script": "#00b841",
    "R": "#198CE7",
    "RAML": "#77d9fb",
    "RDoc": "#705280",
    "REALbasic": "#1414fd",
    "REXX": "#d1dbe0",
    "Racket": "#3c5caa",
    "Ragel in Ruby Host": "#701516",
    "Rascal": "#fffaa0",
    "Reason": "#ff5847",
    "Rebol": "#358a5b",
    "Red": "#f50000",
    "Redcode": "#f50000",
    "Ren'Py": "#ff7f7f",
    "RenderScript": "#222222",
    "RobotFramework": "#00c0b5",
    "Roff": "#ecdebe",
    "Rouge": "#cc0088",
    "RPC": "#7784d3",
    "RPM Spec": "#eed8e0",
    "RUNOFF": "#665a4e",
    "Racket": "#3c5caa",
    "Rust": "#dea584",
    "SAS": "#B34936",
    "SCSS": "#c6538c",
    "SMT": "#3553a5",
    "SPARQL": "#0a3d85",
    "SQF": "#3F3F3F",
    "SQL": "#e38c00",
    "SQLPL": "#e38c00",
    "SRecode Template": "#0a0d22",
    "SSH Config": "#4169e1",
    "STON": "#3a3a3a",
    "SVG": "#ff9900",
    "Sage": "#3572A5",
    "SaltStack": "#646464",
    "Sass": "#a53b70",
    "Scala": "#c22d40",
    "Scaml": "#c2d4e2",
    "Scheme": "#1e4aec",
    "Scilab": "#ca0f21",
    "Self": "#0579aa",
    "ShaderLab": "#222c37",
    "Shell": "#89e051",
    "ShellSession": "#89e051",
    "Shen": "#120F14",
    "Sieve": "#4b7e4b",
    "Slice": "#003fa2",
    "Slim": "#2b2b2b",
    "Smali": "#cc7832",
    "Smalltalk": "#596706",
    "Smarty": "#f0c040",
    "Solidity": "#AA6746",
    "SourcePawn": "#f69e1d",
    "Squirrel": "#800000",
    "Stan": "#b2011d",
    "Standard ML": "#dc566d",
    "Starlark": "#76d275",
    "Stata": "#1a5f91",
    "Stylus": "#ff6347",
    "SubRip Text": "#f8c555",
    "SugarSS": "#2fcc9f",
    "Swift": "#F05138",
    "SystemVerilog": "#DAE1C2",
    "TOML": "#9c4221",
    "TXL": "#c4a79c",
    "Tcl": "#e4cc98",
    "Tcsh": "#e4cc98",
    "TeX": "#3D6117",
    "Terra": "#00004c",
    "Text": "#9daab3",
    "Textile": "#ffe7ae",
    "Thrift": "#D12127",
    "Turing": "#cf142b",
    "Turtle": "#3434aa",
    "Twig": "#c1d026",
    "Type Language": "#56C2D6",
    "TypeScript": "#3178c6",
    "Unified Parallel C": "#4E41CC",
    "Unity3D Asset": "#222c37",
    "Uno": "#9933cc",
    "UnrealScript": "#a54c4d",
    "V": "#4f87c4",
    "VBA": "#867db1",
    "VBScript": "#15dcdc",
    "VCL": "#148AA8",
    "VHDL": "#adb2cb",
    "Vala": "#a56de2",
    "Verilog": "#b2b7f8",
    "Vim Snippet": "#199f4b",
    "Vim script": "#199f4b",
    "Visual Basic": "#945db7",
    "Volt": "#1F1F1F",
    "Vue": "#41b883",
    "Wavefront Material": "#4E4E4E",
    "Wavefront Object": "#4E4E4E",
    "Web Ontology Language": "#39b54a",
    "WebAssembly": "#04133b",
    "WebIDL": "#02a4d3",
    "WebVTT": "#c4a79c",
    "Wget Config": "#E5E510",
    "Windows Registry Entries": "#00378F",
    "Wollok": "#a23738",
    "World of Warcraft Addon Data": "#F7E43F",
    "X BitMap": "#38ACE0",
    "X Font Directory Index": "#a4a4c4",
    "X PixMap": "#2dc100",
    "X10": "#4B6BEF",
    "XC": "#99DA07",
    "XML": "#0060ac",
    "XML Property List": "#0060ac",
    "XPages": "#e7e0ec",
    "XProc": "#F06A6A",
    "XQuery": "#5232E7",
    "XS": "#EB8CEB",
    "XSLT": "#EB8CEB",
    "Xojo": "#81b2cb",
    "Xtend": "#3B5F8F",
    "YAML": "#cb171e",
    "YANG": "#C1B11F",
    "Yacc": "#4B6C4B",
    "ZAP": "#0d665e",
    "ZIL": "#dc75e5",
    "Zeek": "#a1a1a1",
    "Zig": "#ec915c",
    "Zimpl": "#d67711",
    "desktop": "#4a4a4a",
    "eC": "#913960",
    "edn": "#db5855",
    "fish": "#4aae47",
    "mupad": "#e3f171",
    "nesC": "#94B0C2",
    "ooc": "#b0b77e",
    "reStructuredText": "#141414",
    "sed": "#89e051",
    "wdl": "#c3744a",
    "wisp": "#4B6BEF",
    "xBase": "#403a40",
}


# --- API helpers -------------------------------------------------------------
def api(endpoint):
    """Call `gh api <endpoint>` and return parsed JSON."""
    proc = subprocess.run(
        ["gh", "api", endpoint],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.stderr.write("gh api failed for %s\n%s\n" % (endpoint, proc.stderr.strip()))
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        sys.stderr.write("could not parse JSON for %s: %s\n" % (endpoint, exc))
        return None


def color_for(name):
    return LANGUAGE_COLORS.get(name, OTHER_COLOR)


# --- data collection ---------------------------------------------------------
def collect():
    if not os.environ.get("GH_TOKEN"):
        sys.exit("GH_TOKEN is not set; authenticate first (gh auth login or workflow secret)")

    search = api("search/commits?q=author:%s" % OWNER) or {}
    commits = search.get("total_count", 0)

    user = api("users/%s" % OWNER) or {}
    public_repos = user.get("public_repos", 0)
    followers = user.get("followers", 0)
    following = user.get("following", 0)

    repos = api("users/%s/repos?per_page=100" % OWNER) or []
    own = [r for r in repos if not r.get("fork")]

    totals = {}
    repos_with_data = 0
    for repo in own:
        langs = api("repos/%s/languages" % repo["full_name"])
        if not langs:
            continue
        repos_with_data += 1
        for name, size in langs.items():
            totals[name] = totals.get(name, 0) + size

    return {
        "commits": commits,
        "public_repos": public_repos,
        "followers": followers,
        "following": following,
        "totals": totals,
        "repos_with_data": repos_with_data,
    }


def rank(data):
    """Return [(label, bytes, color)] with top 8 languages plus an Other bucket."""
    totals = data["totals"]
    grand_total = sum(totals.values())

    ordered = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    rows = [(name, size, color_for(name)) for name, size in ordered[:TOP_N]]

    other_bytes = grand_total - sum(size for _, size, _ in rows)
    if other_bytes > 0:
        rows.append(("Other", other_bytes, OTHER_COLOR))

    return rows, grand_total


def percent_shares(rows, grand_total):
    """Largest-remainder rounding so displayed one-decimal percents total 100.0."""
    tenths = []
    for _, size, _ in rows:
        exact = (size / grand_total * 1000.0) if grand_total else 0.0
        tenths.append([int(exact), exact - int(exact)])

    deficit = 1000 - sum(t for t, _ in tenths)
    order = sorted(range(len(tenths)), key=lambda i: tenths[i][1], reverse=True)
    for k in range(deficit):
        tenths[order[k % len(order)]][0] += 1

    return [t / 10.0 for t, _ in tenths]


# --- rendering ---------------------------------------------------------------
def render_stats(data):
    rows = [
        ("Total Commits", data["commits"]),
        ("Public Repos", data["public_repos"]),
        ("Followers", data["followers"]),
        ("Following", data["following"]),
    ]
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="380" height="195" viewBox="0 0 380 195">',
        "<style>text{font-family:%s}</style>" % FONT_STACK,
        '<rect width="380" height="195" fill="%s" rx="4.5"/>' % BG,
        '<text x="16" y="26" fill="%s" font-size="13" font-weight="600">GitHub Stats</text>' % TEXT_BRIGHT,
    ]
    for i, (label, value) in enumerate(rows):
        y = 56 + i * 30
        out.append('<text x="16" y="%d" fill="%s" font-size="12">%s</text>' % (y, TEXT_DIM, label))
        out.append(
            '<text x="364" y="%d" fill="%s" font-size="12" font-weight="500" '
            'text-anchor="end">%s</text>' % (y, TEXT_BRIGHT, value)
        )
    out.append("</svg>")
    return "\n".join(out) + "\n"


def polar(cx, cy, r, angle_deg):
    rad = math.radians(angle_deg)
    return cx + r * math.cos(rad), cy + r * math.sin(rad)


def donut_segments(rows):
    """Annular wedge paths: outer arc out, line in, inner arc back, close."""
    total = sum(size for _, size, _ in rows)
    if total <= 0:
        return []

    paths = []
    angle = -90.0  # start at the top, sweep clockwise
    for label, size, color in rows:
        sweep = (size / total) * 360.0
        end = angle + sweep

        if sweep >= 360.0 - 1e-9:
            # Degenerate single-language case: draw as two half-circle wedges
            # so the arc commands stay valid.
            mid = angle + 180.0
            for half in (0.0, 180.0):
                a0 = angle + half
                a1 = a0 + 180.0
                ox0, oy0 = polar(*CENTER, OUTER_R, a0)
                ox1, oy1 = polar(*CENTER, OUTER_R, a1)
                ix1, iy1 = polar(*CENTER, INNER_R, a1)
                ix0, iy0 = polar(*CENTER, INNER_R, a0)
                d = (
                    "M %.1f %.1f A %g %g 0 1 1 %.1f %.1f "
                    "L %.1f %.1f A %g %g 0 1 0 %.1f %.1f Z"
                ) % (
                    ox0, oy0, OUTER_R, OUTER_R, ox1, oy1,
                    ix1, iy1, INNER_R, INNER_R, ix0, iy0,
                )
                paths.append((d, color))
            break

        large = 1 if sweep > 180.0 else 0
        ox0, oy0 = polar(*CENTER, OUTER_R, angle)
        ox1, oy1 = polar(*CENTER, OUTER_R, end)
        ix1, iy1 = polar(*CENTER, INNER_R, end)
        ix0, iy0 = polar(*CENTER, INNER_R, angle)
        d = (
            "M %.1f %.1f A %g %g 0 %d 1 %.1f %.1f "
            "L %.1f %.1f A %g %g 0 %d 0 %.1f %.1f Z"
        ) % (
            ox0, oy0, OUTER_R, OUTER_R, large, ox1, oy1,
            ix1, iy1, INNER_R, INNER_R, large, ix0, iy0,
        )
        paths.append((d, color))
        angle = end
    return paths


def render_top_langs(data, rows, percents):
    paths = donut_segments(rows)

    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="380" height="195" viewBox="0 0 380 195">',
        "<style>text{font-family:%s}</style>" % FONT_STACK,
        '<rect width="380" height="195" fill="%s" rx="4.5"/>' % BG,
        '<text x="16" y="26" fill="%s" font-size="13" font-weight="600">Most Used Languages</text>' % TEXT_BRIGHT,
    ]
    for d, color in paths:
        out.append('<path d="%s" fill="%s"/>' % (d, color))

    out.append(
        '<text x="110" y="99" fill="%s" font-size="16" font-weight="600" '
        'text-anchor="middle">%d</text>' % (TEXT_BRIGHT, data["repos_with_data"])
    )
    out.append(
        '<text x="110" y="117" fill="%s" font-size="10" text-anchor="middle">repos</text>' % TEXT_DIM
    )

    for i, ((label, _, color), pct) in enumerate(zip(rows, percents)):
        y = ROW_START_Y + i * ROW_STEP
        out.append(
            '<rect x="%d" y="%d" width="%d" height="%d" fill="%s" rx="%g"/>'
            % (LEGEND_X, y, SWATCH, SWATCH, color, SWATCH_RX)
        )
        out.append(
            '<text x="%d" y="%d" fill="%s" font-size="%d">%s</text>'
            % (NAME_X, y + 9, TEXT_BRIGHT, NAME_SIZE, label)
        )
        out.append(
            '<text x="%d" y="%d" fill="%s" font-size="%d" text-anchor="end">%.1f%%</text>'
            % (PERCENT_X, y + 9, TEXT_DIM, PERCENT_SIZE, pct)
        )

    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    data = collect()
    rows, grand_total = rank(data)
    percents = percent_shares(rows, grand_total)

    (REPO_ROOT / "stats.svg").write_text(render_stats(data))
    (REPO_ROOT / "top-langs.svg").write_text(render_top_langs(data, rows, percents))

    print("GitHub stats for %s" % OWNER)
    print("  total commits : %s" % data["commits"])
    print("  public repos  : %s" % data["public_repos"])
    print("  followers     : %s" % data["followers"])
    print("  following     : %s" % data["following"])
    print("Top languages (of %s bytes across %d repos with language data):"
          % (format(grand_total, ","), data["repos_with_data"]))
    for (label, size, color), pct in zip(rows, percents):
        print("  %-14s %14s bytes  %5.1f%%  %s" % (label, format(size, ","), pct, color))
    print("  sum: %.1f%%" % sum(percents))


if __name__ == "__main__":
    main()