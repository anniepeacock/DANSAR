import argparse
import json
import sys
from pathlib import Path

from dansar.uavsar.annotation_to_nested_json_dict import (
    annotation_to_file_json_dicts,
    annotation_to_nested_json_dict,
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


def get_envi_byte_order(metadata, group_metadata):
    """Return ENVI byte-order code: 0=little endian, 1=big endian."""
    global_metadata = metadata.get("global", {})
    text = (
        group_metadata.get("val_endi")
        or global_metadata.get("val_endi")
        or "LITTLE ENDIAN"
    ).strip().upper()

    if "LITTLE ENDIAN" in text:
        return 0
    if "BIG ENDIAN" in text:
        return 1

    raise ValueError(
        f"Unsupported byte order: {text}. "
        "Expected LITTLE ENDIAN or BIG ENDIAN."
    )


def _build_header_text(ann_path, group, metadata, group_metadata):
    """Build the ENVI header text shared by all rasters in one group."""
    required = [
        "set_rows",
        "set_cols",
        "set_proj",
        "row_addr",
        "col_addr",
        "row_mult",
        "col_mult",
        "val_frmt",
    ]
    missing = [field for field in required if field not in group_metadata]
    if missing:
        raise KeyError(
            f"Group '{group}' is missing required fields: {missing}"
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
            f"Known formats: {sorted(UAVSAR_TO_ENVI_DTYPE)}"
        )

    header_lines = [
        "ENVI",
        f"description = {{{ann_path.name} | group={group}}}",
        f"samples = {samples}",
        f"lines = {lines}",
        "bands = 1",
        "header offset = 0",
        "file type = ENVI Standard",
        f"data type = {UAVSAR_TO_ENVI_DTYPE[val_frmt]}",
        "interleave = bsq",
        f"byte order = {get_envi_byte_order(metadata, group_metadata)}",
    ]

    if projection.upper() == "EQA":
        header_lines.append(
            "map info = {Geographic Lat/Lon, "
            f"1.0, 1.0, {col_addr}, {row_addr}, "
            f"{abs(col_mult)}, {abs(row_mult)}, WGS-84}}"
        )
        header_lines.append(
            'coordinate system string = {'
            'GEOGCS["WGS 84",'
            'DATUM["WGS_1984",'
            'SPHEROID["WGS 84",6378137,298.257223563]],'
            'PRIMEM["Greenwich",0],'
            'UNIT["degree",0.0174532925199433]]'
            '}'
        )

    return "\n".join(header_lines) + "\n"


def ann2envi_header(
    ann_path,
    group,
    output_dir,
    save_json=True,
    overwrite=False,
):
    """
    Create one .hdr and, optionally, one .json per raster in a group.

    Example for group='grd_pwr':
        product_HHHH.grd.hdr
        product_HHHH.grd.json
        product_HVHV.grd.hdr
        product_HVHV.grd.json
        product_VVVV.grd.hdr
        product_VVVV.grd.json
    """
    ann_path = Path(ann_path)
    output_dir = Path(output_dir)

    if not ann_path.is_file():
        raise FileNotFoundError(f"Annotation file not found: {ann_path}")

    group = str(group).strip()
    if not group:
        raise ValueError("group is empty")

    ann_text = ann_path.read_text(encoding="utf-8")
    metadata = annotation_to_nested_json_dict(
        ann_text,
        include_global=True,
    )

    if group not in metadata:
        raise KeyError(
            f"Group '{group}' not found. "
            f"Available groups: {sorted(metadata)}"
        )

    file_metadata = annotation_to_file_json_dicts(
        ann_text,
        include_global=True,
        annotation_filename=ann_path.name,
    )

    group_files = {
        raster_name: item
        for raster_name, item in file_metadata.items()
        if item.get("file", {}).get("annotation_group") == group
    }

    if not group_files:
        raise ValueError(
            f"No raster files were found for annotation group '{group}'."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    header_text = _build_header_text(
        ann_path=ann_path,
        group=group,
        metadata=metadata,
        group_metadata=metadata[group],
    )

    results = []

    for raster_name, raster_metadata in group_files.items():
        raster_name = Path(raster_name).name
        header_path = output_dir / f"{raster_name}.hdr"
        json_path = output_dir / f"{raster_name}.json"

        outputs = [header_path]
        if save_json:
            outputs.append(json_path)

        existing = [path for path in outputs if path.exists()]
        if existing and not overwrite:
            raise FileExistsError(
                "Output file(s) already exist: "
                + ", ".join(str(path) for path in existing)
                + ". Use overwrite=True."
            )

        header_path.write_text(header_text, encoding="utf-8")

        written_json = None
        if save_json:
            json_path.write_text(
                json.dumps(
                    raster_metadata,
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            written_json = json_path

        results.append(
            {
                "raster_name": raster_name,
                "header_path": header_path,
                "json_path": written_json,
            }
        )

    return results


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Create one ENVI header and optional JSON per raster in a "
            "UAVSAR annotation group."
        )
    )
    parser.add_argument("-ann", "--annotation", required=True)
    parser.add_argument("-group", "--group", required=True)
    parser.add_argument("-output_dir", "--output-dir", required=True)
    parser.add_argument("--no-json", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    try:
        results = ann2envi_header(
            ann_path=args.annotation,
            group=args.group,
            output_dir=args.output_dir,
            save_json=not args.no_json,
            overwrite=args.overwrite,
        )

        for result in results:
            print(f"HDR:  {result['header_path']}")
            if result["json_path"] is not None:
                print(f"JSON: {result['json_path']}")

        return 0
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
