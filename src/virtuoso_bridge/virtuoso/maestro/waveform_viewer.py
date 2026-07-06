"""Open ViVA/AWV waveform windows for Maestro histories."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from virtuoso_bridge.virtuoso.ops import escape_skill_string


def _skill_string_list(values: Iterable[str]) -> str:
    return "list(" + " ".join(f'"{escape_skill_string(value)}"' for value in values) + ")"


def maestro_open_waveform_viewer_skill(
    lib: str,
    cell: str,
    history: str,
    *,
    signals: list[str] | tuple[str, ...],
    view: str = "maestro",
    application: str = "Assembler",
    test: str | None = None,
    result: str = "tran",
    results_dir: str | Path | None = None,
) -> str:
    """Build SKILL to open a ViVA/AWV plot window for explicit signals.

    TODO: measurement waveform setup is intentionally not implemented here.
    TODO: template plot restore/apply support is intentionally not implemented here.
    """
    if not signals:
        raise ValueError("signals must not be empty")

    escaped_lib = escape_skill_string(lib)
    escaped_cell = escape_skill_string(cell)
    escaped_history = escape_skill_string(history)
    escaped_view = escape_skill_string(view)
    escaped_application = escape_skill_string(application)
    escaped_test = escape_skill_string(test or "")
    escaped_result = escape_skill_string(result)
    signal_expr = _skill_string_list(signals)
    if results_dir is None:
        results_dir_expr = "nil"
        raw_open_expr = "nil"
    else:
        escaped_results_dir = escape_skill_string(str(results_dir))
        results_dir_expr = f'"{escaped_results_dir}"'
        raw_open_expr = f'car(errset(openResults("{escaped_results_dir}") nil))'

    signal_blocks: list[str] = []
    for signal in signals:
        escaped_signal = escape_skill_string(signal)
        output_value_expr = (
            f'errset(maeGetOutputValue("{escaped_signal}" "{escaped_test}") nil)'
            if test
            else f'errset(maeGetOutputValue("{escaped_signal}" vbTestName) nil)'
        )
        signal_blocks.append(
            "vbWaveform = nil "
            "vbWaveResult = if(vbRawResultsOpen "
            f'then errset(v("{escaped_signal}" ?result "{escaped_result}" ?resultsDir vbResultsDir) nil) '
            f'else errset(v("{escaped_signal}" ?result "{escaped_result}") nil)) '
            "vbWaveform = if(vbWaveResult then car(vbWaveResult) else nil) "
            "unless(vbWaveform "
            "when(vbTestName == \"\" "
            "vbTestNamesResult = errset(maeGetResultTests() nil) "
            "vbTestNames = if(vbTestNamesResult then car(vbTestNamesResult) else nil) "
            "when(vbTestNames vbTestName = car(vbTestNames))) "
            "when(vbTestName != \"\" "
            f"vbOutputResult = {output_value_expr} "
            "vbWaveform = if(vbOutputResult then car(vbOutputResult) else nil))) "
            f'unless(vbWaveform error("missing waveform: {escaped_signal}")) '
            "vbWaveforms = append(vbWaveforms list(vbWaveform)) "
        )

    return (
        "let((vbSession vbResultsOpenResult vbResultsOpen vbResultsDir vbRawResultsOpen "
        "vbWaveforms vbWaveform vbWaveResult vbTestName vbTestNamesResult vbTestNames "
        "vbOutputResult vbWindowResult vbWindowId vbPlotResult) "
        "unless(and(isCallable('maeOpenSetup) isCallable('maeOpenResults) "
        "isCallable('maeGetResultTests) isCallable('maeGetOutputValue) "
        "isCallable('maeCloseResults) isCallable('maeCloseSession) "
        "isCallable('openResults) isCallable('awvCreatePlotWindow) "
        "isCallable('awvPlotWaveform) isCallable('v)) "
        'error("waveform viewer API unavailable")) '
        f'vbSession = maeOpenSetup("{escaped_lib}" "{escaped_cell}" "{escaped_view}" '
        f'?application "{escaped_application}" ?mode "r") '
        'unless(vbSession error("open maestro failed")) '
        f'vbResultsOpenResult = errset(maeOpenResults(?session vbSession ?history "{escaped_history}") nil) '
        "vbResultsOpen = if(vbResultsOpenResult then car(vbResultsOpenResult) else nil) "
        'unless(vbResultsOpen error("open results failed")) '
        f"vbResultsDir = {results_dir_expr} "
        f"vbRawResultsOpen = {raw_open_expr} "
        f'vbTestName = "{escaped_test}" '
        "vbWaveforms = nil "
        f"{''.join(signal_blocks)}"
        "vbWindowResult = errset(awvCreatePlotWindow() nil) "
        "vbWindowId = if(vbWindowResult then car(vbWindowResult) else nil) "
        'unless(vbWindowId error("create waveform window failed")) '
        f"vbPlotResult = errset(awvPlotWaveform(vbWindowId vbWaveforms ?expr {signal_expr}) nil) "
        'unless(vbPlotResult && car(vbPlotResult) error("plot waveform failed")) '
        "errset(maeCloseResults() nil) "
        "errset(maeCloseSession(?session vbSession ?forceClose t) nil) "
        f'list("opened" "{escaped_lib}" "{escaped_cell}" "{escaped_view}" "{escaped_history}" vbWindowId))'
    )


def open_waveform_viewer(
    client: Any,
    lib: str,
    cell: str,
    history: str,
    *,
    signals: list[str] | tuple[str, ...],
    view: str = "maestro",
    application: str = "Assembler",
    test: str | None = None,
    result: str = "tran",
    results_dir: str | Path | None = None,
    timeout: int = 60,
) -> Any:
    """Open a ViVA/AWV plot window by executing generated SKILL."""
    skill = maestro_open_waveform_viewer_skill(
        lib,
        cell,
        history,
        signals=signals,
        view=view,
        application=application,
        test=test,
        result=result,
        results_dir=results_dir,
    )
    return client.execute_skill(skill, timeout=timeout)
