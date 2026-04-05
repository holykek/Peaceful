from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from peaceful.converters.easyeffects import peace_to_easyeffects_dict
from peaceful.integrations.easyeffects_paths import easyeffects_output_dir
from peaceful.integrations.easyeffects_reload import try_load_output_preset
from peaceful import __version__
from peaceful.parser.peace import PeacePresetParser


def _cmd_visualize(args: argparse.Namespace) -> int:
    try:
        from peaceful.viz.realtime import run_visualizer
    except ImportError:
        print(
            "peaceful: visualization needs numpy and matplotlib. "
            "Install with: pip install 'peaceful[viz]'",
            file=sys.stderr,
        )
        return 1

    try:
        run_visualizer(
            args.preset_path,
            fs=args.sample_rate,
            watch=args.watch,
            interval_ms=args.interval_ms,
            show_bands=args.bands,
        )
    except OSError as e:
        print(f"peaceful: {e}", file=sys.stderr)
        return 1
    return 0


def _cmd_import(args: argparse.Namespace) -> int:
    parser = PeacePresetParser()
    try:
        result = parser.parse_file(args.preset_path)
    except OSError as e:
        print(f"peaceful: {e}", file=sys.stderr)
        return 1

    data = result.preset.to_json_dict()
    indent = 2 if args.pretty else None
    print(json.dumps(data, indent=indent))

    if result.warnings and (args.verbose or not result.preset.filters):
        for w in result.warnings:
            print(f"peaceful: {w}", file=sys.stderr)
    return 0


def _cmd_apply(args: argparse.Namespace) -> int:
    parser = PeacePresetParser()
    try:
        result = parser.parse_file(args.preset_path)
    except OSError as e:
        print(f"peaceful: {e}", file=sys.stderr)
        return 1

    band_mode = "RLC (BT)" if args.rlc else None
    n_in = len(result.preset.filters)
    try:
        doc = peace_to_easyeffects_dict(
            result.preset,
            band_mode=band_mode,
            allow_subsample=not args.no_subsample,
        )
    except ValueError as e:
        print(f"peaceful: {e}", file=sys.stderr)
        return 1

    n_out = int(doc["output"]["equalizer"]["num-bands"])
    if n_out < n_in:
        print(
            f"peaceful: trimmed {n_in} bands to {n_out} for Easy Effects (log-spaced).",
            file=sys.stderr,
        )

    name = args.name.strip()
    if name.endswith(".json"):
        name = name[: -len(".json")]
    out_name = f"{name}.json"

    try:
        out_dir = easyeffects_output_dir(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = (out_dir / out_name).resolve()
        out_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    except OSError as e:
        print(f"peaceful: {e}", file=sys.stderr)
        return 1

    pre = result.preset.preamp
    pre_s = f"{pre} dB" if pre is not None else "0 dB (none in file)"
    print(f"Wrote EasyEffects output preset: {out_path}")
    print(f"  bands in file: {n_in}; bands in preset JSON: {n_out}, input-gain (preamp): {pre_s}")

    if args.verbose and result.warnings:
        for w in result.warnings:
            print(w, file=sys.stderr)

    if sys.platform != "win32":
        flatpak_dir = (
            Path.home() / ".var/app/com.github.wwmm.easyeffects/config/easyeffects/output"
        ).resolve()
        if flatpak_dir.exists():
            try:
                outside_flatpak = not out_path.resolve().is_relative_to(flatpak_dir)
            except ValueError:
                outside_flatpak = True
            if outside_flatpak:
                print(
                    "Note: Flatpak EasyEffects often reads presets from\n"
                    f"  {flatpak_dir}\n"
                    "Set PEACEFUL_EASYEFFECTS_OUTPUT to that path if the preset does not appear in the UI.",
                    file=sys.stderr,
                )

    if not args.no_reload:
        ok, err = try_load_output_preset(name)
        if ok:
            print(f"Requested EasyEffects load: output preset “{name}”.")
        else:
            print(
                f"Could not auto-load ({err}). "
                "Start the service, then load manually:\n"
                f"  easyeffects --gapplication-service\n"
                f"  easyeffects -l {name}\n"
                "Or in the app: Presets → Output → choose the preset name.",
                file=sys.stderr,
            )

    return 0


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="peaceful",
        description="Import PEACE / Equalizer APO presets for Linux audio stacks.",
    )
    ap.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = ap.add_subparsers(dest="command", required=True)

    imp = sub.add_parser("import", help="Parse a preset file and print JSON")
    imp.add_argument("preset_path", metavar="preset.txt", help="Path to .txt preset")
    imp.add_argument(
        "--pretty",
        action="store_true",
        help="Indent JSON for readability",
    )
    imp.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print parse warnings to stderr",
    )
    imp.set_defaults(func=_cmd_import)

    vis = sub.add_parser(
        "visualize",
        aliases=["viz"],
        help="Realtime EQ curve (theoretical response); use --watch while editing preset",
    )
    vis.add_argument("preset_path", metavar="preset.txt", help="Path to .txt preset")
    vis.add_argument(
        "--watch",
        "-w",
        action="store_true",
        help="Poll the file and redraw when it changes",
    )
    vis.add_argument(
        "--interval-ms",
        type=int,
        default=200,
        metavar="N",
        help="Watch poll interval in milliseconds (default: 200)",
    )
    vis.add_argument(
        "--sample-rate",
        type=float,
        default=48_000.0,
        metavar="HZ",
        help="Sample rate for biquad evaluation (default: 48000)",
    )
    vis.add_argument(
        "--bands",
        action="store_true",
        help="Overlay faint per-band magnitude traces",
    )
    vis.set_defaults(func=_cmd_visualize)

    app = sub.add_parser(
        "apply",
        help="Convert PEACE preset → EasyEffects output JSON and install under easyeffects/output/",
    )
    app.add_argument("preset_path", metavar="preset.txt", help="Path to .txt preset")
    app.add_argument(
        "--name",
        "-n",
        default="peaceful_import",
        metavar="BASENAME",
        help="Output filename without .json (default: peaceful_import)",
    )
    app.add_argument(
        "--output-dir",
        "-o",
        default=None,
        metavar="DIR",
        help="Override output directory (default: XDG config …/easyeffects/output)",
    )
    app.add_argument(
        "--rlc",
        action="store_true",
        help="Use RLC (BT) band mode instead of APO (DR) for older EasyEffects",
    )
    app.add_argument(
        "--no-reload",
        action="store_true",
        help="Do not run easyeffects -l to load the preset",
    )
    app.add_argument(
        "--no-subsample",
        action="store_true",
        help="Error if more than 32 bands instead of trimming (Easy Effects limit)",
    )
    app.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print parser warnings to stderr",
    )
    app.set_defaults(func=_cmd_apply)

    args = ap.parse_args()
    code = args.func(args)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
