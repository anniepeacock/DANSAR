import argparse
import json
import re
from copy import deepcopy
from pathlib import Path


DEFAULT_RASTER_EXTENSIONS = (
    ".grd",
    ".hgt",
    ".inc",
    ".slope",
    ".slc",
    ".mlc",
    ".dat",
    ".lks",
)


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


def _clean_annotation_value(value):
    """
    Remove whitespace and matching quotes from an annotation value.
    """

    value = str(value).strip()

    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {'"', "'"}
    ):
        value = value[1:-1].strip()

    return value


def _is_raster_filename(value, raster_extensions):
    """
    Return True when an annotation value looks like a raster filename.
    """

    value = _clean_annotation_value(value)

    if not value:
        return False

    suffixes = tuple(extension.lower() for extension in raster_extensions)
    return value.lower().endswith(suffixes)


def annotation_to_file_json_dicts(
    ann_text,
    include_global=True,
    raster_extensions=DEFAULT_RASTER_EXTENSIONS,
    annotation_filename=None,
):
    """
    Parse one UAVSAR annotation file into one metadata dictionary per raster.

    The existing nested parser remains the source of truth. This function
    finds fields whose values reference raster files and produces a smaller
    dictionary for each one.

    Each output dictionary contains:
        - "file": identity of the specific raster
        - "global": acquisition-level metadata, when requested and available
        - the relevant metadata group, such as "grd_pwr" or "hgt"

    Within the relevant group, sibling raster filename fields are removed.
    Shared fields such as set_rows, set_cols, row_addr, col_addr, row_mult,
    and col_mult remain available for header generation.

    Parameters
    ----------
    ann_text : str
        Full text of a UAVSAR .ann file.

    include_global : bool
        Include ungrouped acquisition metadata in every file dictionary.

    raster_extensions : iterable[str]
        Filename extensions treated as raster products.

    annotation_filename : str or pathlib.Path or None
        Optional source annotation filename recorded in the "file" section.

    Returns
    -------
    dict[str, dict]
        Mapping from raster filename to its file-specific metadata dictionary.

        Example key:
            product_HHHH.grd

        The corresponding JSON filename can therefore be:
            product_HHHH.grd.json
    """

    metadata = annotation_to_nested_json_dict(
        ann_text,
        include_global=include_global,
    )

    global_metadata = metadata.get("global")
    file_metadata = {}

    for group_name, group_values in metadata.items():
        if group_name == "global":
            continue

        if not isinstance(group_values, dict):
            continue

        raster_fields = {
            field_name: _clean_annotation_value(field_value)
            for field_name, field_value in group_values.items()
            if _is_raster_filename(field_value, raster_extensions)
        }

        if not raster_fields:
            continue

        shared_group_metadata = {
            field_name: deepcopy(field_value)
            for field_name, field_value in group_values.items()
            if field_name not in raster_fields
        }

        for field_name, raster_filename in raster_fields.items():
            if raster_filename in file_metadata:
                previous_key = file_metadata[raster_filename]["file"][
                    "annotation_key"
                ]
                current_key = f"{group_name}.{field_name}"

                raise ValueError(
                    "The same raster filename is referenced more than once "
                    f"in the annotation file: {raster_filename!r}. "
                    f"Found at {previous_key!r} and {current_key!r}."
                )

            output_metadata = {
                "file": {
                    "raster_filename": raster_filename,
                    "json_filename": f"{raster_filename}.json",
                    "annotation_group": group_name,
                    "annotation_field": field_name,
                    "annotation_key": f"{group_name}.{field_name}",
                }
            }

            if annotation_filename is not None:
                output_metadata["file"]["annotation_filename"] = Path(
                    annotation_filename
                ).name

            if include_global and global_metadata:
                output_metadata["global"] = deepcopy(global_metadata)

            output_metadata[group_name] = {
                **deepcopy(shared_group_metadata),
                field_name: raster_filename,
            }

            file_metadata[raster_filename] = output_metadata

    if not file_metadata:
        extensions_text = ", ".join(raster_extensions)
        raise ValueError(
            "No raster filenames were found in the annotation metadata. "
            f"Expected values ending in one of: {extensions_text}"
        )

    return file_metadata


def write_file_jsons(
    file_metadata,
    output_dir,
    indent=2,
    overwrite=False,
):
    """
    Write one JSON file per raster.

    Output naming is intentionally direct:

        raster.grd -> raster.grd.json

    This allows later processing steps to find the JSON with:

        Path(str(raster_path) + ".json")
    """

    if not isinstance(file_metadata, dict):
        raise TypeError(
            "file_metadata must be a dictionary, "
            f"not {type(file_metadata).__name__}"
        )

    if not file_metadata:
        raise ValueError("file_metadata is empty.")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_paths = []

    for raster_filename, metadata in file_metadata.items():
        output_path = output_dir / f"{Path(raster_filename).name}.json"

        if output_path.exists() and not overwrite:
            raise FileExistsError(
                f"Output JSON already exists: {output_path}. "
                "Use overwrite=True or --overwrite to replace it."
            )

        json_text = json.dumps(
            metadata,
            indent=indent,
            ensure_ascii=False,
        )

        output_path.write_text(
            json_text + "\n",
            encoding="utf-8",
        )

        output_paths.append(output_path)

    return output_paths


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Parse a UAVSAR .ann annotation file into nested JSON metadata. "
            "By default, one complete JSON document is printed or written. "
            "Use --split-by-file to write one JSON file per raster product."
        )
    )

    parser.add_argument(
        "annotation_file",
        help="Path to the UAVSAR .ann annotation file.",
    )

    output_group = parser.add_mutually_exclusive_group()

    output_group.add_argument(
        "-o",
        "--output",
        help=(
            "Optional output JSON file for the complete nested metadata. "
            "If omitted, the complete JSON is printed to the terminal."
        ),
    )

    output_group.add_argument(
        "--split-by-file",
        metavar="OUTPUT_DIR",
        help=(
            "Write one JSON file per raster referenced by the annotation. "
            "Files are named raster_filename.ext.json."
        ),
    )

    parser.add_argument(
        "--no-global",
        action="store_true",
        help=(
            "Exclude ungrouped acquisition metadata. "
            "Grouped layer metadata is still retained."
        ),
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
        help=(
            "Allow --split-by-file to overwrite existing JSON files."
        ),
    )

    args = parser.parse_args()

    annotation_path = Path(args.annotation_file)

    if not annotation_path.exists():
        raise FileNotFoundError(f"File not found: {annotation_path}")

    if not annotation_path.is_file():
        raise ValueError(
            f"Annotation path is not a file: {annotation_path}"
        )

    ann_text = annotation_path.read_text(encoding="utf-8")

    if args.split_by_file:
        file_metadata = annotation_to_file_json_dicts(
            ann_text,
            include_global=not args.no_global,
            annotation_filename=annotation_path.name,
        )

        output_paths = write_file_jsons(
            file_metadata,
            output_dir=args.split_by_file,
            indent=args.indent,
            overwrite=args.overwrite,
        )

        print(f"Wrote {len(output_paths)} file-specific JSON file(s):")

        for output_path in output_paths:
            print(f"  - {output_path}")

        return

    metadata = annotation_to_nested_json_dict(
        ann_text,
        include_global=not args.no_global,
    )

    json_text = json.dumps(
        metadata,
        indent=args.indent,
        ensure_ascii=False,
    )

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(
            json_text + "\n",
            encoding="utf-8",
        )
        print(f"Wrote parsed metadata to: {output_path}")

    else:
        print(json_text)


if __name__ == "__main__":
    main()
