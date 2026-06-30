import argparse
import sys
from pathlib import Path


UAVSAR_TO_ENVI_DTYPE = {
    "BYTE": 1,
    "INTEGER*2": 2,
    "INT*2": 2,
    "INTEGER*4": 3,
    "INT*4": 3,
    "REAL*4": 4,
    "FLOAT": 4,
    "REAL*8": 5,
    "DOUBLE": 5,
    "COMPLEX": 6,
    "COMPLEX*8": 6,
    "COMPLEX_MAGNITUDE": 6,
    "COMPLEX_PHASE": 6,
    "COMPRESSED_STOKES": 4,
}


def get_envi_byte_order(metadata, group_metadata):
    """
    Get ENVI byte order code from UAVSAR metadata.

    ENVI byte order:
        0 = little endian
        1 = big endian
    """

    global_metadata = metadata.get("global", {})

    byte_order_text = (
        group_metadata.get("val_endi")
        or global_metadata.get("val_endi")
        or "LITTLE ENDIAN"
    )

    byte_order_text = byte_order_text.strip().upper()

    if "LITTLE ENDIAN" in byte_order_text:
        return 0

    if "BIG ENDIAN" in byte_order_text:
        return 1

    raise ValueError(
        f"Unsupported byte order: {byte_order_text}. "
        "Expected LITTLE ENDIAN or BIG ENDIAN."
    )


def ann2envi_header(
    ann_path,
    group,
    output_hdr,
):
    """
    Create an ENVI .hdr file directly from a UAVSAR .ann annotation file.

    Parameters
    ----------
    ann_path : str or pathlib.Path
        Path to UAVSAR .ann annotation file.

    group : str
        Metadata group to use from the parsed annotation.

        Common values:
            grd_pwr
            inc
            hgt
            slope
            mlc_pwr

    output_hdr : str or pathlib.Path
        Output ENVI header path.

    Returns
    -------
    pathlib.Path
        Path to written ENVI header file.
    """

    ann_path = Path(ann_path)
    output_hdr = Path(output_hdr)

    if not ann_path.exists():
        raise FileNotFoundError(f"Annotation file not found: {ann_path}")

    if not ann_path.is_file():
        raise ValueError(f"Annotation path is not a file: {ann_path}")

    if not isinstance(group, str):
        raise TypeError(f"group must be a string, not {type(group).__name__}")

    group = group.strip()

    if not group:
        raise ValueError("group is empty or contains only whitespace.")

    ann_text = ann_path.read_text()

    try:
        from annotation_to_nested_json_dict import annotation_to_nested_json_dict
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Could not import annotation_to_nested_json_dict. "
            "Make sure annotation_to_nested_json_dict.py is in the same folder "
            "as this script."
        ) from exc

    metadata = annotation_to_nested_json_dict(
        ann_text,
        include_global=True,
    )

    if group not in metadata:
        raise KeyError(
            f"Group '{group}' was not found in annotation metadata. "
            f"Available groups: {sorted(metadata.keys())}"
        )

    group_metadata = metadata[group]

    required_fields = [
        "set_rows",
        "set_cols",
        "set_proj",
        "row_addr",
        "col_addr",
        "row_mult",
        "col_mult",
        "val_frmt",
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in group_metadata
    ]

    if missing_fields:
        raise KeyError(
            f"Group '{group}' is missing required fields: {missing_fields}"
        )

    lines = int(float(group_metadata["set_rows"]))
    samples = int(float(group_metadata["set_cols"]))
    projection = group_metadata["set_proj"].strip()

    row_addr = float(group_metadata["row_addr"])
    col_addr = float(group_metadata["col_addr"])
    row_mult = float(group_metadata["row_mult"])
    col_mult = float(group_metadata["col_mult"])

    val_frmt = group_metadata["val_frmt"].strip().upper()

    if val_frmt not in UAVSAR_TO_ENVI_DTYPE:
        raise ValueError(
            f"Unsupported UAVSAR val_frmt: {val_frmt}. "
            f"Known formats: {sorted(UAVSAR_TO_ENVI_DTYPE.keys())}"
        )

    envi_dtype = UAVSAR_TO_ENVI_DTYPE[val_frmt]
    envi_byte_order = get_envi_byte_order(metadata, group_metadata)

    header_lines = [
        "ENVI",
        f"description = {{{ann_path.name} | group={group}}}",
        f"samples = {samples}",
        f"lines = {lines}",
        "bands = 1",
        "header offset = 0",
        "file type = ENVI Standard",
        f"data type = {envi_dtype}",
        "interleave = bsq",
        f"byte order = {envi_byte_order}",
    ]

    if projection.upper() == "EQA":
        pixel_size_x = abs(col_mult)
        pixel_size_y = abs(row_mult)

        map_info = (
            "map info = {Geographic Lat/Lon, "
            f"1.0, 1.0, {col_addr}, {row_addr}, "
            f"{pixel_size_x}, {pixel_size_y}, WGS-84"
            "}"
        )

        coordinate_system = (
            "coordinate system string = {"
            "GEOGCS[\"WGS 84\","
            "DATUM[\"WGS_1984\","
            "SPHEROID[\"WGS 84\",6378137,298.257223563]],"
            "PRIMEM[\"Greenwich\",0],"
            "UNIT[\"degree\",0.0174532925199433]]"
            "}"
        )

        header_lines.append(map_info)
        header_lines.append(coordinate_system)

    output_hdr.parent.mkdir(parents=True, exist_ok=True)
    output_hdr.write_text("\n".join(header_lines) + "\n")

    return output_hdr


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Create an ENVI .hdr file directly from a UAVSAR .ann annotation file. "
            "The annotation is parsed using annotation_to_nested_json_dict.py."
        )
    )

    parser.add_argument(
        "-ann",
        "--annotation",
        required=True,
        help="Path to UAVSAR .ann annotation file.",
    )

    parser.add_argument(
        "-group",
        "--group",
        required=True,
        help=(
            "Annotation metadata group to use. "
            "Examples: grd_pwr, inc, hgt, slope, mlc_pwr."
        ),
    )

    parser.add_argument(
        "-output_hdr",
        "--output-hdr",
        required=True,
        help="Output ENVI .hdr file path.",
    )

    args = parser.parse_args()

    try:
        hdr_path = ann2envi_header(
            ann_path=args.annotation,
            group=args.group,
            output_hdr=args.output_hdr,
        )

        print(f"Wrote ENVI header: {hdr_path}")
        return 0

    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())