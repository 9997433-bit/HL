"""``openfemlab wizard`` — interactive menu for common workflows."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from ..console import Reporter

NAME = "wizard"
HELP = "guided menu for modal analysis, correlation, and HTML reports"

_MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "heading": "OpenFEMLab wizard",
        "pick": "Pick a workflow — empty input cancels.",
        "opt1": "Run the 60-second quickstart demo",
        "opt2": "Modal analysis (YAML/JSON model file)",
        "opt3": "Correlate model vs measured modal data",
        "opt4": "Update model parameters from measurements",
        "opt5": "Build an HTML report from a JSON artifact",
        "opt6": "Open the Web results dashboard (serve)",
        "opt7": "Initialize a CAE project workspace",
        "opt8": "Run the six-stage correction pipeline",
        "opt9": "SDM stiffness spring scan",
        "opt10": "Correlate FRF (measured vs synthesized)",
        "opt11": "Run a performance benchmark",
        "opt12": "Show command cheat sheet",
        "opt0": "Exit",
        "goodbye": "Goodbye.",
        "choice": "Choice",
        "model_path": "Model spec path",
        "modes": "Number of modes [6]",
        "test_path": "Measured data path",
        "corr_out": "Save correlation JSON (optional)",
        "update_spec": "Updating spec path",
        "update_out": "Output model spec (optional)",
        "report_json": "Report JSON path",
        "html_out": "HTML output path",
        "project_dir": "Project directory [.]",
        "pipeline_config": "Pipeline configuration path",
        "sdm_model": "Model spec for SDM scan",
        "frf_measured": "Measured FRF path (UFF/UNV)",
        "frf_model": "Damped model spec path",
        "bench_case": "Benchmark case [modal]",
        "running": "Running: openfemlab {}",
        "unknown": "Unknown choice: {choice!r}",
        "cheat_heading": "CLI cheat sheet",
    },
    "zh": {
        "heading": "OpenFEMLab 向导",
        "pick": "选择工作流 — 留空取消。",
        "opt1": "60 秒快速演示（quickstart）",
        "opt2": "模态分析（YAML/JSON 模型文件）",
        "opt3": "相关分析：模型 vs 实测模态",
        "opt4": "模型修正：根据测量更新参数",
        "opt5": "由 JSON 生成 HTML 报告",
        "opt6": "打开 Web 结果查看器（serve）",
        "opt7": "初始化 CAE 项目工作区",
        "opt8": "六阶段修正流水线（pipeline）",
        "opt9": "SDM 刚度弹簧扫描",
        "opt10": "FRF 相关（实测 vs 合成）",
        "opt11": "性能基准（bench）",
        "opt12": "命令速查表",
        "opt0": "退出",
        "goodbye": "再见。",
        "choice": "选项",
        "model_path": "模型规格路径",
        "modes": "模态阶数 [6]",
        "test_path": "实测数据路径",
        "corr_out": "保存相关 JSON（可选）",
        "update_spec": "修正配置路径",
        "update_out": "输出模型规格（可选）",
        "report_json": "报告 JSON 路径",
        "html_out": "HTML 输出路径",
        "project_dir": "项目目录 [.]",
        "pipeline_config": "流水线配置路径",
        "sdm_model": "SDM 扫描模型规格",
        "frf_measured": "实测 FRF 路径（UFF/UNV）",
        "frf_model": "阻尼模型规格路径",
        "bench_case": "基准用例 [modal]",
        "running": "正在运行: openfemlab {}",
        "unknown": "未知选项: {choice!r}",
        "cheat_heading": "命令速查",
    },
}

_CHEAT_SHEET = [
    "openfemlab quickstart",
    "openfemlab project init",
    "openfemlab modal model.yaml -n 8",
    "openfemlab correlate model.yaml measured.yaml",
    "openfemlab correlate model.yaml measured.yaml -o report.json --format json",
    "openfemlab correlate-frf measured.unv model.yaml",
    "openfemlab report report.json -o report.html --open",
    "openfemlab serve --root . --file reports/corr.json --open",
    "openfemlab update updating.yaml -o model.updated.yaml",
    "openfemlab pipeline run pipeline.yaml --strict",
    "openfemlab sdm scan model.yaml",
    "openfemlab bench modal",
    "openfemlab info",
    "pip install 'openfemlab[cli,plot,io]'",
]


def add_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        NAME,
        help=HELP,
        description=(
            "A text menu for engineers who prefer prompts over memorizing subcommands. "
            "Each choice runs the same CLI you would type manually, so scripts and CI "
            "stay unchanged."
        ),
    )
    parser.add_argument(
        "--lang",
        choices=("en", "zh"),
        default=_default_lang(),
        help="menu language (default: en, or zh when LANG is Chinese)",
    )
    parser.set_defaults(func=run)
    return parser


def _default_lang() -> str:
    lang = os.environ.get("LANG", "").lower()
    if lang.startswith("zh"):
        return "zh"
    return "en"


def run(args: argparse.Namespace, reporter: Reporter) -> int:
    msg = _MESSAGES[args.lang]
    reporter.heading(msg["heading"])
    reporter.note(msg["pick"])

    while True:
        reporter.line()
        reporter.line(f"  1  {msg['opt1']}")
        reporter.line(f"  2  {msg['opt2']}")
        reporter.line(f"  3  {msg['opt3']}")
        reporter.line(f"  4  {msg['opt4']}")
        reporter.line(f"  5  {msg['opt5']}")
        reporter.line(f"  6  {msg['opt6']}")
        reporter.line(f"  7  {msg['opt7']}")
        reporter.line(f"  8  {msg['opt8']}")
        reporter.line(f"  9  {msg['opt9']}")
        reporter.line(f" 10  {msg['opt10']}")
        reporter.line(f" 11  {msg['opt11']}")
        reporter.line(f" 12  {msg['opt12']}")
        reporter.line(f"  0  {msg['opt0']}")
        choice = _prompt(msg["choice"], reporter)

        if choice in ("0", "q", "quit", "exit"):
            reporter.success(msg["goodbye"])
            return 0
        if choice == "1":
            return _delegate(["quickstart"], reporter, msg)
        if choice == "2":
            model = _prompt(msg["model_path"], reporter)
            if not model:
                continue
            modes = _prompt(msg["modes"], reporter) or "6"
            return _delegate(["modal", model, "-n", modes], reporter, msg)
        if choice == "3":
            model = _prompt(msg["model_path"], reporter)
            test = _prompt(msg["test_path"], reporter)
            if not model or not test:
                continue
            out = _prompt(msg["corr_out"], reporter)
            cmd = ["correlate", model, test, "--format", "json"]
            if out:
                cmd.extend(["-o", out])
            code = _delegate(cmd, reporter, msg)
            if code == 0 and out:
                reporter.hint(f"openfemlab report {out} -o {Path(out).stem}.html")
                reporter.hint(f"openfemlab serve --file {out} --open")
            return code
        if choice == "4":
            spec = _prompt(msg["update_spec"], reporter)
            if not spec:
                continue
            out = _prompt(msg["update_out"], reporter)
            cmd = ["update", spec]
            if out:
                cmd.extend(["-o", out])
            return _delegate(cmd, reporter, msg)
        if choice == "5":
            source = _prompt(msg["report_json"], reporter)
            if not source:
                continue
            dest = _prompt(msg["html_out"], reporter) or f"{Path(source).stem}.html"
            return _delegate(["report", source, "-o", dest], reporter, msg)
        if choice == "6":
            return _delegate(["serve", "--open"], reporter, msg)
        if choice == "7":
            directory = _prompt(msg["project_dir"], reporter) or "."
            return _delegate(["project", "init", directory], reporter, msg)
        if choice == "8":
            config = _prompt(msg["pipeline_config"], reporter)
            if not config:
                continue
            return _delegate(["pipeline", "run", config, "--strict"], reporter, msg)
        if choice == "9":
            model = _prompt(msg["sdm_model"], reporter)
            if not model:
                continue
            return _delegate(["sdm", "scan", model], reporter, msg)
        if choice == "10":
            measured = _prompt(msg["frf_measured"], reporter)
            model = _prompt(msg["frf_model"], reporter)
            if not measured or not model:
                continue
            return _delegate(["correlate-frf", measured, model], reporter, msg)
        if choice == "11":
            case = _prompt(msg["bench_case"], reporter) or "modal"
            return _delegate(["bench", case], reporter, msg)
        if choice == "12":
            _cheat_sheet(reporter, msg)
            continue
        reporter.warning(msg["unknown"].format(choice=choice))


def _prompt(label: str, reporter: Reporter) -> str:
    print(f"{label}: ", end="", file=reporter.stream, flush=True)
    try:
        return input().strip()
    except EOFError:
        reporter.line()
        return ""


def _delegate(argv: list[str], reporter: Reporter, msg: dict[str, str]) -> int:
    from ..main import main as cli_main

    reporter.note(msg["running"].format(" ".join(argv)))
    return int(cli_main(argv))


def _cheat_sheet(reporter: Reporter, msg: dict[str, str]) -> None:
    reporter.heading(msg["cheat_heading"])
    for line in _CHEAT_SHEET:
        reporter.line(f"  {line}")
