# digital_import — recipes for pulling P&R products into Virtuoso

Two cookbook scripts that complete the **RTL → GDS → integrate into
Virtuoso** loop after Genus + Innovus finish.

## Common prerequisites

1. ``virtuoso-bridge start`` is running and ``virtuoso-bridge status``
   shows the daemon as OK.
2. The Virtuoso work directory's ``cds.lib`` already contains a
   ``DEFINE`` line for every library these scripts touch, e.g.:

   ```
   DEFINE DIG_OUTPUT                  /home/you/work/DIG_OUTPUT
   DEFINE tsmcN28                     /home/process/.../tsmcN28        ← tech library
   DEFINE tcbn28hpcplusbwp12t30p140   /home/process/.../bwp12t30p140   ← std-cell ref library
   ```

   ``strmin`` will create the cellview directories on disk, but it does
   **not** edit ``cds.lib`` — if the target library is not registered,
   Virtuoso simply won't see the result.

## ``import_gds.py`` — physical layout via ``strmin``

Wraps Cadence's standalone ``strmin`` tool.  No GUI involvement; the
tool runs inside Virtuoso's child shell so PATH and licence env are
inherited.

```
python import_gds.py /path/to/foo.route_tapeout.gds \
       --target-lib DIG_OUTPUT \
       --tech-lib   tsmcN28 \
       --ref-libs   /path/to/ref_libs_dir
```

After completion the script prints ``instances=N shapes=M bbox=...`` for
the new ``layout`` view as a sanity check.

## ``import_verilog.py`` — schematic + symbol via the Import form

Drives Virtuoso's ``File → Import → Verilog`` dialog programmatically.
Produces both ``schematic`` and ``symbol`` views in the target library.

⚠  **One-time bootstrap per Virtuoso session**: the importer's SKILL form
is loaded lazily.  Before running this script the first time in a
session, you must open the dialog once manually:

> Virtuoso CIW → **File → Import → Verilog** → close the dialog

That triggers Cadence to ``loadi`` the form's SKILL file, after which
the global symbol ``impHdlOptionsFormMain`` is bound for the rest of the
session.  The script aborts with a clear message if you forget.

```
python import_verilog.py /path/to/foo_import.v \
       --target-lib DIG_OUTPUT \
       --ref-lib    tcbn28hpcplusbwp12t30p140
```

## Why these are recipes, not first-class CLI commands

Both scripts drive Virtuoso GUI forms or vendor shell tools whose
interfaces are private to a specific Cadence IC release (tested on
**IC618 SP201**).  They **may break on other IC versions** if Cadence
renames a form field or moves a tool.  Keeping them here as cookbook
examples — rather than as ``virtuoso-bridge import-*`` subcommands —
limits the blast radius when a Cadence upgrade shifts the ground.
