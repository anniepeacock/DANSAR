import argparse
import json
import re
from pathlib import Path


def _normalize_key(key):
    """
    Convert UAVSAR annotation labels into simple JSON keys.
    """

    key = key.strip()
    key = re.sub(r"[^A-Za-z0-9_.]+", "_", key)
    key = re.sub(r"_+", "_", key)
    key = key.strip("_")
    return key.lower()


def annotation_to_nested_json_dict(ann_text, include_global=True):
    """
    Parse UAVSAR annotation text into a nested metadata dictionary.

    This parser treats the UAVSAR annotation file as line-based metadata.

    It skips:
        - blank lines
        - full-line comments starting with ;

    It also removes inline comments after semicolons, for example:

        grd_pwr.set_rows (pixels) = 13275 ; GRD Lines

    becomes:

        {"grd_pwr": {"set_rows": "13275"}}
    """

    if not isinstance(ann_text, str):
        raise TypeError(
            f"ann_text must be a string, not {type(ann_text).__name__}"
        )

    if not ann_text.strip():
        raise ValueError("ann_text is empty or contains only whitespace.")

    metadata = {"global": {}}

    line_pattern = re.compile(
        r"""
        ^\s*
        (?P<key>[A-Za-z0-9_.][A-Za-z0-9_.\s/-]*?)
        \s*
        (?:\([^)]*\))?
        \s*=\s*
        (?P<value>.*?)
        \s*$
        """,
        re.VERBOSE,
    )

    parsed_fields = 0

    try:
        for raw_line in ann_text.splitlines():
            line = raw_line.strip()

            if not line:
                continue

            if line.startswith(";"):
                continue

            # Remove inline comments.
            # Example:
            # grd_pwr.set_rows (pixels) = 13275 ; GRD Lines
            line = line.split(";", 1)[0].strip()

            if not line or "=" not in line:
                continue

            match = line_pattern.match(line)

            if not match:
                continue

            key = _normalize_key(match.group("key"))
            value = match.group("value").strip()

            if not key:
                continue

            if "." in key:
                group, field = key.split(".", 1)
                metadata.setdefault(group, {})
                metadata[group][field] = value
            elif include_global:
                metadata["global"][key] = value

            parsed_fields += 1

        if parsed_fields == 0:
            raise ValueError(
                "No valid UAVSAR annotation fields were found in ann_text."
            )

        if not metadata["global"]:
            metadata.pop("global")

        return metadata

    except ValueError:
        raise

    except Exception as exc:
        raise RuntimeError(
            "Unexpected error while parsing UAVSAR annotation text."
        ) from exc


def main():
    parser = argparse.ArgumentParser(
        description="Parse a UAVSAR .ann annotation file into nested JSON metadata."
    )

    parser.add_argument(
        "annotation_file",
        help="Path to the UAVSAR .ann annotation file."
    )

    parser.add_argument(
        "-o",
        "--output",
        help="Optional output JSON file. If omitted, JSON is printed to terminal."
    )

    parser.add_argument(
        "--no-global",
        action="store_true",
        help="Only keep grouped layer metadata such as grd_pwr, hgt, inc, slope."
    )

    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation level. Default: 2."
    )

    args = parser.parse_args()

    annotation_path = Path(args.annotation_file)

    if not annotation_path.exists():
        raise FileNotFoundError(f"File not found: {annotation_path}")

    ann_text = annotation_path.read_text()

    metadata = annotation_to_nested_json_dict(
        ann_text,
        include_global=not args.no_global,
    )

    json_text = json.dumps(metadata, indent=args.indent)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json_text)
        print(f"Wrote parsed metadata to: {output_path}")
    else:
        print(json_text)


if __name__ == "__main__":
    main()