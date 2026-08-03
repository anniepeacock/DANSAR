import argparse
import json
import re
from pathlib import Path


def _normalize_key(key):
    """
    Convert a UAVSAR annotation label into a stable JSON key.
    """

    key = key.strip()
    key = re.sub(r"[^A-Za-z0-9_.]+", "_", key)
    key = re.sub(r"_+", "_", key)
    return key.strip("_").lower()


def annotation_to_nested_json_dict(
    ann_text,
    include_global=True,
):
    """
    Parse UAVSAR annotation text into one complete nested dictionary.

    Grouped keys such as:

        grd_pwr.set_rows = 13275

    become:

        {
            "grd_pwr": {
                "set_rows": "13275"
            }
        }

    Ungrouped fields are stored under "global" when include_global=True.
    """

    if not isinstance(ann_text, str):
        raise TypeError(
            f"ann_text must be a string, "
            f"not {type(ann_text).__name__}"
        )

    if not ann_text.strip():
        raise ValueError(
            "ann_text is empty or contains only whitespace."
        )

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

    for raw_line in ann_text.splitlines():
        line = raw_line.strip()

        if not line or line.startswith(";"):
            continue

        # Everything after a semicolon is a comment.
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
            "No valid UAVSAR annotation fields were found."
        )

    if not metadata["global"]:
        metadata.pop("global")

    return metadata


def annotation_to_file_json_dicts(
    ann_text,
    include_global=True,
    annotation_filename=None,
    output_json=None,
    indent=2,
    overwrite=False,
):
    """
    Return one complete nested metadata dictionary for an annotation file.

    Despite the historical function name, this function does not try to
    discover raster filenames inside annotation values. It parses and returns
    every metadata group in the annotation.

    The returned dictionary can remain purely in memory. If output_json is
    provided, the same complete dictionary is also serialized to disk.

    Parameters
    ----------
    ann_text : str
        Full text of a UAVSAR .ann file.

    include_global : bool
        Include ungrouped fields under "global".

    annotation_filename : str, pathlib.Path, or None
        Optional source annotation filename recorded under "annotation".

    output_json : str, pathlib.Path, or None
        Optional path for saving the complete JSON document.

    indent : int or None
        JSON indentation used when output_json is supplied.

    overwrite : bool
        Permit replacement of an existing output_json.

    Returns
    -------
    dict
        Complete nested metadata dictionary containing all annotation groups.
    """

    metadata = annotation_to_nested_json_dict(
        ann_text,
        include_global=include_global,
    )

    if annotation_filename is not None:
        metadata = {
            "annotation": {
                "filename": Path(annotation_filename).name,
            },
            **metadata,
        }

    if output_json is not None:
        output_json = Path(output_json)

        if output_json.exists() and not overwrite:
            raise FileExistsError(
                f"Output JSON already exists: {output_json}. "
                "Use overwrite=True to replace it."
            )

        output_json.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_json.write_text(
            json.dumps(
                metadata,
                indent=indent,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

    return metadata


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Parse a UAVSAR annotation file into one complete "
            "nested JSON document containing all metadata groups."
        )
    )

    parser.add_argument(
        "annotation_file",
        help="Path to the UAVSAR .ann file.",
    )

    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help=(
            "Optional path for saving the complete JSON. "
            "If omitted, JSON is printed to the terminal."
        ),
    )

    parser.add_argument(
        "--no-global",
        action="store_true",
        help="Exclude ungrouped annotation fields.",
    )

    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation level. Default: 2.",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite an existing output JSON.",
    )

    args = parser.parse_args()

    annotation_path = Path(args.annotation_file)

    if not annotation_path.exists():
        raise FileNotFoundError(
            f"Annotation file not found: {annotation_path}"
        )

    if not annotation_path.is_file():
        raise ValueError(
            f"Annotation path is not a file: {annotation_path}"
        )

    metadata = annotation_to_file_json_dicts(
        annotation_path.read_text(encoding="utf-8"),
        include_global=not args.no_global,
        annotation_filename=annotation_path.name,
        output_json=args.output,
        indent=args.indent,
        overwrite=args.overwrite,
    )

    if args.output is None:
        print(
            json.dumps(
                metadata,
                indent=args.indent,
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
