from __future__ import annotations

import pytest

from virtuoso_bridge.virtuoso.maestro import (
    maestro_open_waveform_viewer_skill,
    open_waveform_viewer,
)


def test_maestro_open_waveform_viewer_skill_plots_explicit_signals() -> None:
    skill = maestro_open_waveform_viewer_skill(
        "demoLib",
        "tb_inv",
        "Interactive.1",
        signals=["/IN", "/OUT"],
        results_dir="/tmp/psf/tran/psf",
        result="tran",
    )

    assert "isCallable('awvCreatePlotWindow)" in skill
    assert 'maeOpenSetup("demoLib" "tb_inv" "maestro" ?application "Assembler" ?mode "r")' in skill
    assert 'maeOpenResults(?session vbSession ?history "Interactive.1")' in skill
    assert 'openResults("/tmp/psf/tran/psf")' in skill
    assert 'v("/IN" ?result "tran" ?resultsDir vbResultsDir)' in skill
    assert 'v("/OUT" ?result "tran" ?resultsDir vbResultsDir)' in skill
    assert "awvCreatePlotWindow()" in skill
    assert 'awvPlotWaveform(vbWindowId vbWaveforms ?expr list("/IN" "/OUT"))' in skill


def test_maestro_open_waveform_viewer_skill_can_fallback_to_maestro_outputs() -> None:
    skill = maestro_open_waveform_viewer_skill(
        "demoLib",
        "tb_inv",
        "Interactive.1",
        signals=["vout"],
        test="tran",
    )

    assert 'maeGetOutputValue("vout" "tran")' in skill
    assert 'list("opened" "demoLib" "tb_inv" "maestro" "Interactive.1" vbWindowId)' in skill


def test_maestro_open_waveform_viewer_requires_signals() -> None:
    with pytest.raises(ValueError, match="signals must not be empty"):
        maestro_open_waveform_viewer_skill("demoLib", "tb_inv", "Interactive.1", signals=[])


def test_open_waveform_viewer_executes_generated_skill() -> None:
    class Client:
        skill: str | None = None
        timeout: int | None = None

        def execute_skill(self, skill: str, *, timeout: int):
            self.skill = skill
            self.timeout = timeout
            return {"status": "success", "output": '("opened" "demoLib" "tb_inv")'}

    client = Client()
    result = open_waveform_viewer(
        client,
        "demoLib",
        "tb_inv",
        "Interactive.1",
        signals=["/OUT"],
        timeout=30,
    )

    assert result == {"status": "success", "output": '("opened" "demoLib" "tb_inv")'}
    assert client.timeout == 30
    assert client.skill is not None
    assert 'awvPlotWaveform(vbWindowId vbWaveforms ?expr list("/OUT"))' in client.skill
