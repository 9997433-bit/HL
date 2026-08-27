"""``openfemlab align`` — rigid geometry alignment of test sensors to FE nodes."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from ..console import Reporter

NAME = "align"
HELP = "align test sensor coordinates to FE model nodes"


def add_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        NAME,
        help=HELP,
        description=(
            "Estimate a rigid transform between test sensor coordinates and FE "
            "node positions, then map each sensor to the nearest node within a "
            "distance gate.  Outputs a JSON sensor-map payload for correlation."
        ),
    )
    parser.add_argument(
        "model_coords",
        help="FE node coordinates CSV with columns x,y,z (optional id column)",
    )
    parser.add_argument(
        "sensor_coords",
        help="test sensor coordinates CSV with columns x,y,z (optional label column)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="-",
        help="output JSON file (default: stdout)",
    )
    parser.add_argument(
        "--max-distance",
        type=float,
        default=0.05,
        metavar="M",
        help="maximum nearest-node distance in model units (default: 0.05)",
    )
    parser.add_argument(
        "--reference-model",
        help="optional reference model coordinate CSV for transform estimation",
    )
    parser.add_argument(
        "--reference-sensors",
        help="optional reference sensor coordinate CSV paired with --reference-model",
    )
    return parser


def _read_coords(path: str) -> tuple[np.ndarray, list[str]]:
    rows: list[list[float]] = []
    labels: list[str] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if not row:
                continue
            if len(row) < 3:
                raise ValueError(f"coordinate file {path} needs at least three columns")
            try:
                coords = [float(row[0]), float(row[1]), float(row[2])]
            except ValueError:
                continue
            rows.append(coords)
            labels.append(row[3] if len(row) > 3 else f"sensor_{len(labels)}")
    if not rows:
        raise ValueError(f"no numeric coordinates found in {path}")
    return np.asarray(rows, dtype=np.float64), labels


def run(args: argparse.Namespace, reporter: Reporter) -> int:
    from openfemlab.correlation.geometry import map_sensors_to_nodes

    model_coords, _ = _read_coords(args.model_coords)
    sensor_coords, labels = _read_coords(args.sensor_coords)
    reference_model = None
    reference_sensors = None
    if args.reference_model and args.reference_sensors:
        reference_model, _ = _read_coords(args.reference_model)
        reference_sensors, _ = _read_coords(args.reference_sensors)

    alignment = map_sensors_to_nodes(
        model_coords,
        sensor_coords,
        max_distance=float(args.max_distance),
        reference_model_coords=reference_model,
        reference_sensor_coords=reference_sensors,
    )

    payload: dict[str, Any] = {
        "rows": [int(index) for index in alignment.node_indices.tolist()],
        "labels": labels,
        "distances": alignment.distances.tolist(),
        "matched": alignment.matched_mask.tolist(),
        "rigid_transform": alignment.as_meta(),
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output == "-":
        reporter.line(text.rstrip("\n"))
    else:
        Path(args.output).write_text(text, encoding="utf-8")
        reporter.note(f"written {args.output}")
    unmatched = int(np.count_nonzero(~alignment.matched_mask))
    if unmatched:
        reporter.warning(f"{unmatched} sensor(s) exceed the distance gate")
        return 2
    return 0
