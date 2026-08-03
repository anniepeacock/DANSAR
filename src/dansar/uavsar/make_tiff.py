import argparse
import json
import shutil
import sys
from pathlib import Path


def expected_envi_header_path(raster_path):
    """Return the ENVI header path that GDAL/rasterio expects."""
    raster_path = Path(raster_path)
    return raster_path.with_suffix(raster_path.suffix + ".hdr")


def expected_metadata_json_path(raster_path):
    """Return the file-specific JSON path: raster.ext.json."""
    return Path(str(Path(raster_path)) + ".json")


def infer_output_tiff_path(raster_path, output_dir, suffix="_tif", extension=".tif"):
    """Infer output GeoTIFF path from input raster filename."""
    raster_path = Path(raster_path)
    output_dir = Path(output_dir)

    if not extension.startswith("."):
        extension = "." + extension

    return output_dir / f"{raster_path.stem}{suffix}{extension}"


def prepare_explicit_envi_header(raster_path, header_path):
    """
    Make sure GDAL/rasterio can find the ENVI header.

    If the provided header has a different name from the name expected by
    GDAL, copy it temporarily beside the raster.
    """
    raster_path = Path(raster_path)
    header_path = Path(header_path)
    expected_header = expected_envi_header_path(raster_path)

    if expected_header.resolve() == header_path.resolve():
        return None

    if expected_header.exists():
        raise FileExistsError(
            "GDAL expected header already exists, but it is not the header "
            "provided by the user:\n"
            f"  expected: {expected_header}\n"
            f"  provided: {header_path}\n"
            "Refusing to overwrite it."
        )

    shutil.copyfile(header_path, expected_header)
    return expected_header


def read_metadata_json(raster_path, metadata_json_path=None):
    """
    Read the file-specific JSON associated with a raster.

    By default:
        image.grd -> image.grd.json
    """
    raster_path = Path(raster_path)

    if metadata_json_path is None:
        metadata_json_path = expected_metadata_json_path(raster_path)
    else:
        metadata_json_path = Path(metadata_json_path)

    if not metadata_json_path.exists():
        raise FileNotFoundError(
            "File-specific metadata JSON not found:\n"
            f"  raster: {raster_path}\n"
            f"  expected JSON: {metadata_json_path}"
        )

    if not metadata_json_path.is_file():
        raise ValueError(
            f"Metadata JSON path is not a file: {metadata_json_path}"
        )

    try:
        with metadata_json_path.open("r", encoding="utf-8") as src:
            metadata = json.load(src)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON metadata file: {metadata_json_path}"
        ) from exc

    if not isinstance(metadata, dict):
        raise TypeError(
            "The metadata JSON root must be a dictionary, "
            f"not {type(metadata).__name__}."
        )

    return metadata, metadata_json_path


def make_tiff(
    raster_path,
    header_path,
    output_dir,
    nodata=None,
    invalid_min=0.0,
    clip_min=None,
    overwrite=False,
    suffix="_tif",
    extension=".tif",
    compress="DEFLATE",
    block_size=512,
    metadata_json_path=None,
):
    """
    Convert a UAVSAR ENVI raster to a single-band tiled/compressed GeoTIFF.

    This writes:
      - one band only
      - float32 data
      - invalid pixels as NaN
      - nodata metadata as NaN
      - no alpha band
      - no internal mask
      - no overviews
      - file-specific annotation JSON in the GeoTIFF metadata

    Invalid pixels are NaN, Inf, or values <= invalid_min.

    Valid values below clip_min are raised to clip_min. This preserves them as
    valid pixels rather than turning them into nodata.

    Parameters
    ----------
    raster_path : str or pathlib.Path
        Input UAVSAR raster binary.

    header_path : str or pathlib.Path
        Explicit ENVI header file.

    output_dir : str or pathlib.Path
        Output directory.

    nodata : None or float
        Output nodata value. Default: NaN.

    invalid_min : float
        Values <= this threshold become nodata. Default: 0.0.

    clip_min : None or float
        Optional floor for valid values. Default: None.

    overwrite : bool
        Overwrite existing output when True.

    metadata_json_path : None, str, or pathlib.Path
        Optional explicit JSON path. When omitted, use raster.ext.json.

    Returns
    -------
    pathlib.Path
        Written GeoTIFF path.
    """
    try:
        import numpy as np
        import rasterio
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "make_tiff requires numpy and rasterio."
        ) from exc

    raster_path = Path(raster_path)
    header_path = Path(header_path)
    output_dir = Path(output_dir)

    if nodata is None:
        nodata = np.nan
    else:
        nodata = float(nodata)

    invalid_min = float(invalid_min)

    if clip_min is not None:
        clip_min = float(clip_min)

        if clip_min <= invalid_min:
            raise ValueError(
                "clip_min must be greater than invalid_min. "
                f"Received clip_min={clip_min} and invalid_min={invalid_min}."
            )

    if not raster_path.exists():
        raise FileNotFoundError(f"Raster file not found: {raster_path}")

    if not header_path.exists():
        raise FileNotFoundError(f"Header file not found: {header_path}")

    if not raster_path.is_file():
        raise ValueError(f"Raster path is not a file: {raster_path}")

    if not header_path.is_file():
        raise ValueError(f"Header path is not a file: {header_path}")

    if not isinstance(block_size, int):
        raise TypeError(
            f"block_size must be an integer, not {type(block_size).__name__}"
        )

    if block_size <= 0:
        raise ValueError("block_size must be greater than zero.")

    metadata, metadata_json_path = read_metadata_json(
        raster_path=raster_path,
        metadata_json_path=metadata_json_path,
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    final_tiff = infer_output_tiff_path(
        raster_path=raster_path,
        output_dir=output_dir,
        suffix=suffix,
        extension=extension,
    )

    if final_tiff.exists() and not overwrite:
        raise FileExistsError(
            f"Output file already exists: {final_tiff}. "
            "Use --overwrite to replace it."
        )

    temporary_header = None

    try:
        temporary_header = prepare_explicit_envi_header(
            raster_path=raster_path,
            header_path=header_path,
        )

        with rasterio.open(raster_path) as src:
            arr = src.read(1).astype("float32", copy=True)

            invalid = (~np.isfinite(arr)) | (arr <= invalid_min)

            if src.nodata is not None:
                if np.isfinite(src.nodata):
                    invalid |= arr == src.nodata
                else:
                    invalid |= ~np.isfinite(arr)

            if clip_min is not None:
                low_valid = (~invalid) & (arr < clip_min)
                arr[low_valid] = clip_min

            arr[invalid] = nodata

            profile = src.profile.copy()
            profile.update(
                driver="GTiff",
                dtype="float32",
                count=1,
                nodata=nodata,
                tiled=True,
                blockxsize=block_size,
                blockysize=block_size,
                compress=compress,
                predictor=2,
                BIGTIFF="IF_SAFER",
            )

            # Important:
            # No overviews.
            # No internal mask.
            # No alpha band.
            # One output band only.
            with rasterio.open(final_tiff, "w", **profile) as dst:
                dst.write(arr, 1)

                dst.update_tags(
                    UAVSAR_ANNOTATION_JSON=json.dumps(
                        metadata,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                    UAVSAR_METADATA_JSON_FILE=metadata_json_path.name,
                )

                if clip_min is not None:
                    dst.update_tags(
                        UAVSAR_VALID_DATA_CLIP_MIN=str(clip_min)
                    )

        return final_tiff

    finally:
        if temporary_header is not None:
            temporary_header.unlink(missing_ok=True)


def make_tiffs(
    raster_header_pairs,
    output_dir,
    nodata=None,
    invalid_min=0.0,
    clip_min=None,
    overwrite=False,
    suffix="_tif",
    extension=".tif",
    compress="DEFLATE",
    block_size=512,
):
    """
    Convert multiple raster/header pairs to GeoTIFF.

    Each raster must have a sibling JSON named raster.ext.json.
    """
    if not raster_header_pairs:
        raise ValueError("No raster/header pairs were provided.")

    output_paths = []

    for raster_path, header_path in raster_header_pairs:
        output_tiff = make_tiff(
            raster_path=raster_path,
            header_path=header_path,
            output_dir=output_dir,
            nodata=nodata,
            invalid_min=invalid_min,
            clip_min=clip_min,
            overwrite=overwrite,
            suffix=suffix,
            extension=extension,
            compress=compress,
            block_size=block_size,
        )

        output_paths.append(output_tiff)

    return output_paths


def _parse_nodata(value):
    """Parse nodata argument from CLI."""
    if value is None:
        return None

    value = str(value).strip()

    if value.lower() in {"nan", "none", "null"}:
        return None

    return float(value)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Convert UAVSAR ENVI rasters to single-band tiled/compressed "
            "GeoTIFFs. Each raster must have a sibling JSON named "
            "raster.ext.json. The JSON is embedded in the TIFF metadata."
        )
    )

    parser.add_argument(
        "-raster",
        "--raster",
        action="append",
        required=True,
        help=(
            "Input raster binary. Can be passed multiple times. "
            "Must be paired with --hdr."
        ),
    )

    parser.add_argument(
        "-hdr",
        "--hdr",
        action="append",
        required=True,
        help=(
            "Input ENVI header. Can be passed multiple times. "
            "Must be paired with --raster in the same order."
        ),
    )

    parser.add_argument(
        "-output_dir",
        "--output-dir",
        required=True,
        help="Directory where output GeoTIFFs will be saved.",
    )

    parser.add_argument(
        "--nodata",
        default="nan",
        help="Output nodata value. Default: nan.",
    )

    parser.add_argument(
        "--invalid-min",
        type=float,
        default=0.0,
        help=(
            "Values <= this threshold become nodata/NaN. Default: 0.0."
        ),
    )

    parser.add_argument(
        "--clip-min",
        type=float,
        default=None,
        help=(
            "Optional floor for valid values. For example: --clip-min 1e-4."
        ),
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite output file if it already exists.",
    )

    parser.add_argument(
        "--suffix",
        default="_tif",
        help='Suffix added to output filename stem. Default: "_tif".',
    )

    parser.add_argument(
        "--extension",
        default=".tif",
        choices=[".tif", "tif", ".tiff", "tiff"],
        help="Output file extension. Default: .tif.",
    )

    parser.add_argument(
        "--compress",
        default="DEFLATE",
        help="GeoTIFF compression method. Default: DEFLATE.",
    )

    parser.add_argument(
        "--block-size",
        type=int,
        default=512,
        help="Internal GeoTIFF tile size. Default: 512.",
    )

    args = parser.parse_args()

    try:
        if len(args.raster) != len(args.hdr):
            raise ValueError(
                "The number of --raster inputs must match "
                "the number of --hdr inputs."
            )

        raster_header_pairs = list(zip(args.raster, args.hdr))

        output_paths = make_tiffs(
            raster_header_pairs=raster_header_pairs,
            output_dir=args.output_dir,
            nodata=_parse_nodata(args.nodata),
            invalid_min=args.invalid_min,
            clip_min=args.clip_min,
            overwrite=args.overwrite,
            suffix=args.suffix,
            extension=args.extension,
            compress=args.compress,
            block_size=args.block_size,
        )

        print("Wrote GeoTIFF file(s):")

        for output_path in output_paths:
            print(f"  - {output_path}")

        return 0

    except Exception as exc:
        print(f"\\nERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
