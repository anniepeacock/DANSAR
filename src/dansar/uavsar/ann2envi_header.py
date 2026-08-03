import argparse
import json
import re
import sys
from copy import deepcopy
from pathlib import Path

from dansar.uavsar.annotation_to_nested_json_dict import (
    annotation_to_file_json_dicts,
)


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


GROUP_PRODUCTS = {
    "grd_pwr": {
        "polarizations": ("HHHH", "HVHV", "VVVV"),
        "extension": ".grd",
    },
    "grd_mag": {
        "polarizations": ("HHHV", "HHVV", "HVVV"),
        "extension": ".grd",
    },
    "grd_phase": {
        "polarizations": ("HHHV", "HHVV", "HVVV"),
        "extension": ".grd",
    },
    "mlc_pwr": {
        "polarizations": ("HHHH", "HVHV", "VVVV"),
        "extension": ".mlc",
    },
    "mlc_mag": {
        "polarizations": ("HHHV", "HHVV", "HVVV"),
        "extension": ".mlc",
    },
    "mlc_phase": {
        "polarizations": ("HHHV", "HHVV", "HVVV"),
        "extension": ".mlc",
    },
}


def get_envi_byte_order(metadata, group_metadata):
    """
    Get ENVI byte order code.

    ENVI:
        0 = little endian
        1 = big endian
    """

    global_metadata = metadata.get("global", {})

    byte_order_text = (
        group_metadata.get("val_endi")
        or global_metadata.get("val_endi")
        or "LITTLE ENDIAN"
    )

    byte_order_text = str(byte_order_text).strip().upper()

    if "LITTLE ENDIAN" in byte_order_text:
        return 0

    if "BIG ENDIAN" in byte_order_text:
        return 1

    raise ValueError(
        f"Unsupported byte order: {byte_order_text}"
    )


def _product_stem_from_annotation(ann_path):
    """
    Return the UAVSAR product stem from an annotation filename.

    Example:
        PanCan_..._L090_CX_01.ann
        ->
        PanCan_..._L090_CX_01
    """

    ann_path = Path(ann_path)
    return ann_path.stem


def _insert_polarization(product_stem, polarization):
    """
    Insert polarization before the _CX_ product marker.

    Example:
        product_L090_CX_01 + HHHH
        ->
        product_L090HHHH_CX_01
    """

    match = re.search(r"_CX_", product_stem)

    if not match:
        raise ValueError(
            "Could not derive raster filename from annotation "
            f"name because '_CX_' was not found: {product_stem}"
        )

    insert_at = match.start()

    return (
        product_stem[:insert_at]
        + polarization
        + product_stem[insert_at:]
    )


def _derive_raster_names(ann_path, group):
    """
    Derive raster filenames for a supported annotation group.
    """

    if group not in GROUP_PRODUCTS:
        raise ValueError(
            f"Unsupported group '{group}'. "
            f"Supported groups: {sorted(GROUP_PRODUCTS)}"
        )

    product_stem = _product_stem_from_annotation(ann_path)
    product_info = GROUP_PRODUCTS[group]

    return [
        (
            polarization,
            _insert_polarization(
                product_stem,
                polarization,
            )
            + product_info["extension"],
        )
        for polarization in product_info["polarizations"]
    ]


def _build_header_lines(
    ann_path,
    group,
    metadata,
    group_metadata,
):
    """
    Build one ENVI header from the selected metadata group.
    """

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
            f"Group '{group}' is missing required fields: "
            f"{missing_fields}"
        )

    lines = int(float(group_metadata["set_rows"]))
    samples = int(float(group_metadata["set_cols"]))

    projection = str(
        group_metadata["set_proj"]
    ).strip()

    row_addr = float(group_metadata["row_addr"])
    col_addr = float(group_metadata["col_addr"])
    row_mult = float(group_metadata["row_mult"])
    col_mult = float(group_metadata["col_mult"])

    val_frmt = str(
        group_metadata["val_frmt"]
    ).strip().upper()

    if val_frmt not in UAVSAR_TO_ENVI_DTYPE:
        raise ValueError(
            f"Unsupported UAVSAR val_frmt: {val_frmt}. "
            f"Known formats: "
            f"{sorted(UAVSAR_TO_ENVI_DTYPE)}"
        )

    envi_dtype = UAVSAR_TO_ENVI_DTYPE[val_frmt]
    envi_byte_order = get_envi_byte_order(
        metadata,
        group_metadata,
    )

    header_lines = [
        "ENVI",
        f"description = {{{Path(ann_path).name} | group={group}}}",
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

        header_lines.append(
            "map info = {Geographic Lat/Lon, "
            f"1.0, 1.0, {col_addr}, {row_addr}, "
            f"{pixel_size_x}, {pixel_size_y}, WGS-84"
            "}"
        )

        header_lines.append(
            "coordinate system string = {"
            "GEOGCS[\"WGS 84\","
            "DATUM[\"WGS_1984\","
            "SPHEROID[\"WGS 84\",6378137,"
            "298.257223563]],"
            "PRIMEM[\"Greenwich\",0],"
            "UNIT[\"degree\",0.0174532925199433]]"
            "}"
        )

    return header_lines


def ann2envi_header(
    ann_path,
    group,
    output_dir,
    save_json=True,
    overwrite=False,
):
    """
    Create one ENVI header and optional JSON per raster in a group.

    For group="grd_pwr", this writes:

        product_HHHH.grd.hdr
        product_HHHH.grd.json
        product_HVHV.grd.hdr
        product_HVHV.grd.json
        product_VVVV.grd.hdr
        product_VVVV.grd.json

    The annotation is parsed once into one complete in-memory dictionary.
    The selected group is then reused for all rasters in that group.
    """

    ann_path = Path(ann_path)
    output_dir = Path(output_dir)

    if not ann_path.exists():
        raise FileNotFoundError(
            f"Annotation file not found: {ann_path}"
        )

    if not ann_path.is_file():
        raise ValueError(
            f"Annotation path is not a file: {ann_path}"
        )

    group = str(group).strip()

    if not group:
        raise ValueError(
            "group is empty or contains only whitespace."
        )

    ann_text = ann_path.read_text(
        encoding="utf-8"
    )

    metadata = annotation_to_file_json_dicts(
        ann_text,
        include_global=True,
        annotation_filename=ann_path.name,
    )

    if group not in metadata:
        raise KeyError(
            f"Group '{group}' was not found. "
            f"Available groups: {sorted(metadata)}"
        )

    group_metadata = metadata[group]

    if not isinstance(group_metadata, dict):
        raise TypeError(
            f"Metadata group '{group}' must be a dictionary."
        )

    raster_names = _derive_raster_names(
        ann_path,
        group,
    )

    header_lines = _build_header_lines(
        ann_path=ann_path,
        group=group,
        metadata=metadata,
        group_metadata=group_metadata,
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    results = []

    for polarization, raster_filename in raster_names:
        header_path = (
            output_dir
            / f"{raster_filename}.hdr"
        )

        json_path = (
            output_dir
            / f"{raster_filename}.json"
        )

        output_paths = [header_path]

        if save_json:
            output_paths.append(json_path)

        existing = [
            path
            for path in output_paths
            if path.exists()
        ]

        if existing and not overwrite:
            raise FileExistsError(
                "Output file(s) already exist: "
                + ", ".join(str(path) for path in existing)
                + ". Use overwrite=True to replace them."
            )

        header_path.write_text(
            "\n".join(header_lines) + "\n",
            encoding="utf-8",
        )

        written_json = None

        if save_json:
            file_metadata = deepcopy(metadata)

            file_metadata["file"] = {
                "raster_filename": raster_filename,
                "header_filename": header_path.name,
                "json_filename": json_path.name,
                "annotation_filename": ann_path.name,
                "annotation_group": group,
                "polarization": polarization,
            }

            json_path.write_text(
                json.dumps(
                    file_metadata,
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            written_json = json_path

        results.append(
            {
                "polarization": polarization,
                "raster_path": (
                    output_dir
                    / raster_filename
                ),
                "header_path": header_path,
                "json_path": written_json,
            }
        )

    return results


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Create one ENVI header and optional JSON per "
            "raster in a UAVSAR annotation group."
        )
    )

    parser.add_argument(
        "-ann",
        "--annotation",
        required=True,
        help="Path to the UAVSAR .ann file.",
    )

    parser.add_argument(
        "-group",
        "--group",
        required=True,
        help="Annotation group, for example grd_pwr.",
    )

    parser.add_argument(
        "-output_dir",
        "--output-dir",
        required=True,
        help="Directory for generated .hdr and .json files.",
    )

    parser.add_argument(
        "--no-json",
        action="store_true",
        help="Do not save file-specific JSON files.",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files.",
    )

    args = parser.parse_args()

    try:
        results = ann2envi_header(
            ann_path=args.annotation,
            group=args.group,
            output_dir=args.output_dir,
            save_json=not args.no_json,
            overwrite=args.overwrite,
        )

        print(
            f"Wrote metadata files for "
            f"{len(results)} raster(s):"
        )

        for result in results:
            print(
                f"  HDR:  {result['header_path']}"
            )

            if result["json_path"] is not None:
                print(
                    f"  JSON: {result['json_path']}"
                )

        return 0

    except Exception as exc:
        print(
            f"\nERROR: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
