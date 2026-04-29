#!/usr/bin/env python3
"""Import a structural Verilog netlist into a Virtuoso library as schematic+symbol.

Drives the (interactive) "File → Import → Verilog" form via SKILL — no
GUI clicks needed once the form has been initialized once per Virtuoso
session.

Prerequisites
-------------
* ``virtuoso-bridge start`` running, daemon loaded in CIW.
* Target library DEFINEd in ``cds.lib``.
* **One-time bootstrap per Virtuoso session**: open
  ``File → Import → Verilog`` once and close the dialog.  That triggers
  Cadence to ``loadi`` the form's SKILL file, after which the global
  symbol ``impHdlOptionsFormMain`` stays bound for the whole session.
  This script aborts with a friendly message if you forget.

The Verilog importer works on *structural* netlists — the kind Innovus
emits as ``<design>_import.v``.  RTL with behavioural always-blocks
won't elaborate to the cell library.
"""

from __future__ import annotations

import argparse
import os
import sys

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.ops import escape_skill_string


def _q(s: str) -> str:
    """Wrap a Python string as a SKILL string literal."""
    return f'"{escape_skill_string(s)}"'


# Field path inside ``impHdlOptionsFormMain`` is determined by the IC618
# importer schema — change here if Cadence renames it in another release.
SKILL_DRIVE_FORM = """\
hiDisplayForm(impHdlOptionsFormMain)
let((p)
  p = impHdlOptionsFormMain->impHdlImportFileTabMain->page1
  p->impHdlVerDesignField->value          = {file}
  p->impHdlTargetLibField->value          = {target}
  p->impHdlRefLibField->value             = {ref}
  p->impHdlRefSymbViewNameField->value    = {symview}
)
hiFormDone(impHdlOptionsFormMain)
ddUpdateLibList()
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 2)[0])
    parser.add_argument(
        "verilog",
        help="Path to the structural Verilog file (e.g. LFSR_32BIT_import.v)",
    )
    parser.add_argument(
        "--target-lib", required=True,
        help="OA library to write schematic+symbol into",
    )
    parser.add_argument(
        "--ref-lib", default="tcbn28hpcplusbwp12t30p140",
        help="Reference library that supplies leaf-cell symbols "
             "(default: tcbn28hpcplusbwp12t30p140)",
    )
    parser.add_argument(
        "--symbol-view", default="symbol",
        help="Symbol view name to look up in --ref-lib (default: symbol)",
    )
    parser.add_argument(
        "--cell", default=None,
        help="Override the top cell to verify after import "
             "(default: filename stem with any '_import' suffix removed)",
    )
    args = parser.parse_args()

    client = VirtuosoClient.from_env()

    # 1. Bootstrap check — has the user opened File→Import→Verilog at least once?
    r = client.execute_skill("boundp('impHdlOptionsFormMain)")
    if (r.output or "").strip() != "t":
        sys.exit(
            "ERROR: Verilog Import form is not loaded yet.\n"
            "  In Virtuoso CIW: File → Import → Verilog (and just close the dialog).\n"
            "  Then re-run this script."
        )

    # 2. Verify target library exists.
    r = client.execute_skill(
        f'sprintf(nil "%L" ddGetObj({_q(args.target_lib)})~>readPath)'
    )
    if (r.output or "").strip() in ('"nil"', "nil", ""):
        sys.exit(
            f"ERROR: library '{args.target_lib}' is not in Virtuoso's cds.lib.\n"
            f"  Add a 'DEFINE {args.target_lib} <path>' line first."
        )

    # 3. Drive the form.
    skill = SKILL_DRIVE_FORM.format(
        file=_q(args.verilog),
        target=_q(args.target_lib),
        ref=_q(args.ref_lib),
        symview=_q(args.symbol_view),
    )
    r = client.execute_skill(skill)
    if r.errors:
        sys.exit(f"SKILL error during import: {r.errors}")

    # 4. Verify schematic + symbol were created.
    cell = args.cell or os.path.basename(args.verilog).rsplit(".", 1)[0]
    if cell.endswith("_import"):
        cell = cell[: -len("_import")]

    sk_views = (
        f'sprintf(nil "%L" '
        f'  mapcar(lambda(v v~>name) ddGetObj({_q(args.target_lib)} {_q(cell)})~>views))'
    )
    r = client.execute_skill(sk_views)
    print(f"[OK] {args.target_lib}/{cell}/views: {r.output}")

    sk_sch = (
        f"let((cv) "
        f"  cv=dbOpenCellViewByType({_q(args.target_lib)} {_q(cell)} \"schematic\" nil \"r\") "
        f"  if(cv "
        f"     sprintf(nil \"instances=%d nets=%d terms=%d\" "
        f"             length(cv~>instances) length(cv~>nets) length(cv~>terminals)) "
        f"     \"OPEN_FAILED\")) "
    )
    r = client.execute_skill(sk_sch)
    print(f"[OK] {args.target_lib}/{cell}/schematic: {r.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
