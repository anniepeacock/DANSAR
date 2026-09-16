import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path


PRODUCT_UNITS = {
    "GRD": "Backscatter in linear power, unitless",
    "HGT": "Height in meters",
}

DATA_ACCESS = (
    "Original UAVSAR files courtesy of NASA/JPL-Caltech and available "
    "through CC0 license: "
    "https://www.earthdata.nasa.gov/engage/"
    "open-data-services-software-policies/data-use-guidance"
)


def expected_envi_header_path(raster_path):
    """Return the ENVI header path GDAL/rasterio expects."""
    raster_path = Path(raster_path)
    return raster_path.with_suffix(raster_path.suffix + ".hdr")


def expected_metadata_json_path(raster_path):
    """Return the sibling metadata path: raster.ext.json."""
    return Path(str(Path(raster_path)) + ".json")


def infer_output_tiff_path(
    raster_path,
    output_dir,
    suffix="_tif",
    extension=".tif",
):
    """Infer output GeoTIFF path."""
    raster_path = Path(raster_path)
    output_dir = Path(output_dir)

    if not extension.startswith("."):
        extension = "." + extension

    return output_dir / f"{raster_path.stem}{suffix}{extension}"


def prepare_explicit_envi_header(raster_path, header_path):
    """Temporarily place the explicit ENVI header where GDAL expects it."""
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
    """Read the file-specific JSON associated with a raster."""
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


def _required_mapping(metadata, key):
    """Return a required nested dictionary."""
    value = metadata.get(key)

    if not isinstance(value, dict):
        raise KeyError(
            f"Metadata JSON must contain a dictionary at '{key}'."
        )

    return value


def _required_value(mapping, key, parent):
    """Return a required non-empty metadata value."""
    if key not in mapping:
        raise KeyError(
            f"Metadata JSON is missing '{parent}.{key}'."
        )

    value = mapping[key]

    if value is None or str(value).strip() == "":
        raise ValueError(
            f"Metadata field '{parent}.{key}' is empty."
        )

    return value


def _acquisition_date(global_metadata):
    """
    Read acquisition date from normalized annotation metadata.

    No raster-filename parsing is used.
    """
    for key in (
        "date_of_acquisition",
        "acquisition_date",
        "date",
    ):
        value = global_metadata.get(key)

        if value is not None and str(value).strip():
            return str(value).strip()

    raise KeyError(
        "No acquisition date found in the JSON. Expected one of: "
        "global.date_of_acquisition, global.acquisition_date, global.date."
    )


def build_geotiff_tags(metadata):
    """
    Build compact publication metadata from the same JSON used for the HDR.
    """
    file_metadata = _required_mapping(metadata, "file")
    global_metadata = _required_mapping(metadata, "global")

    raster_filename = str(
        _required_value(
            file_metadata,
            "raster_filename",
            "file",
        )
    ).strip()

    group_name = str(
        _required_value(
            file_metadata,
            "annotation_group",
            "file",
        )
    ).strip()

    group_metadata = _required_mapping(
        metadata,
        group_name,
    )

    raster_name = Path(raster_filename)
    granule_id = raster_name.stem
    product_type = raster_name.suffix.lstrip(".").upper()

    if product_type not in PRODUCT_UNITS:
        raise ValueError(
            f"No units are defined for product type '{product_type}'. "
            f"Supported product types: {sorted(PRODUCT_UNITS)}"
        )

    rows = int(
        float(
            _required_value(
                group_metadata,
                "set_rows",
                group_name,
            )
        )
    )

    cols = int(
        float(
            _required_value(
                group_metadata,
                "set_cols",
                group_name,
            )
        )
    )

    row_addr = float(
        _required_value(
            group_metadata,
            "row_addr",
            group_name,
        )
    )

    col_addr = float(
        _required_value(
            group_metadata,
            "col_addr",
            group_name,
        )
    )

    row_mult = float(
        _required_value(
            group_metadata,
            "row_mult",
            group_name,
        )
    )

    col_mult = float(
        _required_value(
            group_metadata,
            "col_mult",
            group_name,
        )
    )

    center_latitude = (
        row_addr
        + row_mult * (rows - 1) / 2
    )

    center_longitude = (
        col_addr
        + col_mult * (cols - 1) / 2
    )

    return {
        "GRANULE_ID": granule_id,
        "PRODUCT_TYPE": product_type,
        "UNITS": PRODUCT_UNITS[product_type],
        "ACQUISITION_DATE": _acquisition_date(
            global_metadata
        ),
        "CENTER_LATITUDE": str(center_latitude),
        "CENTER_LONGITUDE": str(center_longitude),
        "ORIGINAL_PIXEL_POSTING_LATITUDE": str(
            abs(row_mult)
        ),
        "ORIGINAL_PIXEL_POSTING_LONGITUDE": str(
            abs(col_mult)
        ),
        "PIXEL_POSTING_UNITS": "degrees",
        "DATA_ACCESS": DATA_ACCESS,
    }


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
    overview_resampling="AVERAGE",
    metadata_json_path=None,
):
    """
    Convert a UAVSAR ENVI raster to a single-band Cloud Optimized GeoTIFF.

    The sibling JSON used to construct the ENVI header is also the sole
    source for the compact GeoTIFF publication metadata.
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
                f"Received clip_min={clip_min} and "
                f"invalid_min={invalid_min}."
            )

    if not raster_path.is_file():
        raise FileNotFoundError(
            f"Raster file not found: {raster_path}"
        )

    if not header_path.is_file():
        raise FileNotFoundError(
            f"Header file not found: {header_path}"
        )

    if not isinstance(block_size, int):
        raise TypeError(
            f"block_size must be an integer, "
            f"not {type(block_size).__name__}"
        )

    if block_size <= 0:
        raise ValueError(
            "block_size must be greater than zero."
        )

    overview_resampling = str(
        overview_resampling
    ).strip().upper()

    allowed_overview_resampling = {
        "NEAREST",
        "AVERAGE",
        "BILINEAR",
        "CUBIC",
        "CUBICSPLINE",
        "LANCZOS",
        "MODE",
        "RMS",
    }

    if overview_resampling not in allowed_overview_resampling:
        raise ValueError(
            "Unsupported overview resampling method: "
            f"{overview_resampling}. "
            f"Choose one of: {sorted(allowed_overview_resampling)}"
        )

    metadata, _ = read_metadata_json(
        raster_path=raster_path,
        metadata_json_path=metadata_json_path,
    )

    geotiff_tags = build_geotiff_tags(
        metadata
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

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

    if final_tiff.exists() and overwrite:
        final_tiff.unlink()

    temporary_header = None

    try:
        temporary_header = prepare_explicit_envi_header(
            raster_path=raster_path,
            header_path=header_path,
        )

        with rasterio.open(raster_path) as src:
            arr = src.read(1).astype(
                "float32",
                copy=True,
            )

            invalid = (
                ~np.isfinite(arr)
            ) | (
                arr <= invalid_min
            )

            if src.nodata is not None:
                if np.isfinite(src.nodata):
                    invalid |= arr == src.nodata
                else:
                    invalid |= ~np.isfinite(arr)

            if clip_min is not None:
                low_valid = (
                    ~invalid
                ) & (
                    arr < clip_min
                )

                arr[low_valid] = clip_min

            arr[invalid] = nodata

            profile = src.profile.copy()

            # Write the cleaned full-resolution raster to a temporary tiled
            # GeoTIFF. The final output is created by GDAL's COG driver so
            # the image data and overview IFDs are ordered for cloud access.
            profile.update(
                driver="GTiff",
                dtype="float32",
                count=1,
                nodata=nodata,
                tiled=True,
                blockxsize=block_size,
                blockysize=block_size,
                compress=compress,
                predictor=3,
                BIGTIFF="IF_SAFER",
            )

            with tempfile.TemporaryDirectory(
                dir=output_dir
            ) as temp_dir:
                temp_tiff = (
                    Path(temp_dir)
                    / f"{raster_path.stem}_fullres.tif"
                )

                with rasterio.open(
                    temp_tiff,
                    "w",
                    **profile,
                ) as dst:
                    dst.write(arr, 1)
                    dst.update_tags(
                        **geotiff_tags
                    )

                    if clip_min is not None:
                        dst.update_tags(
                            UAVSAR_VALID_DATA_CLIP_MIN=str(
                                clip_min
                            )
                        )

                from rasterio.shutil import copy as rio_copy

                rio_copy(
                    temp_tiff,
                    final_tiff,
                    driver="COG",
                    BLOCKSIZE=block_size,
                    COMPRESS=compress,
                    PREDICTOR="FLOATING_POINT",
                    BIGTIFF="IF_SAFER",
                    OVERVIEWS="IGNORE_EXISTING",
                    OVERVIEW_RESAMPLING=overview_resampling,
                    OVERVIEW_COMPRESS=compress,
                    OVERVIEW_PREDICTOR="FLOATING_POINT",
                    NUM_THREADS="ALL_CPUS",
                )

        return final_tiff

    finally:
        if temporary_header is not None:
            temporary_header.unlink(
                missing_ok=True
            )


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
    overview_resampling="AVERAGE",
):
    """Convert multiple raster/header pairs to Cloud Optimized GeoTIFF."""
    if not raster_header_pairs:
        raise ValueError(
            "No raster/header pairs were provided."
        )

    output_paths = []

    for raster_path, header_path in raster_header_pairs:
        output_paths.append(
            make_tiff(
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
                overview_resampling=overview_resampling,
            )
        )

    return output_paths


def _parse_nodata(value):
    """Parse the CLI nodata argument."""
    if value is None:
        return None

    value = str(value).strip()

    if value.lower() in {
        "nan",
        "none",
        "null",
    }:
        return None

    return float(value)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Convert UAVSAR ENVI rasters to Cloud Optimized GeoTIFFs with internal overviews. "
            "Each raster must have a sibling JSON named raster.ext.json."
        )
    )

    parser.add_argument(
        "-raster",
        "--raster",
        action="append",
        required=True,
    )

    parser.add_argument(
        "-hdr",
        "--hdr",
        action="append",
        required=True,
    )

    parser.add_argument(
        "-output_dir",
        "--output-dir",
        required=True,
    )

    parser.add_argument(
        "--nodata",
        default="nan",
    )

    parser.add_argument(
        "--invalid-min",
        type=float,
        default=0.0,
    )

    parser.add_argument(
        "--clip-min",
        type=float,
        default=None,
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
    )

    parser.add_argument(
        "--suffix",
        default="_tif",
    )

    parser.add_argument(
        "--extension",
        default=".tif",
        choices=[
            ".tif",
            "tif",
            ".tiff",
            "tiff",
        ],
    )

    parser.add_argument(
        "--compress",
        default="DEFLATE",
    )

    parser.add_argument(
        "--block-size",
        type=int,
        default=512,
    )

    parser.add_argument(
        "--overview-resampling",
        default="AVERAGE",
        choices=[
            "NEAREST",
            "AVERAGE",
            "BILINEAR",
            "CUBIC",
            "CUBICSPLINE",
            "LANCZOS",
            "MODE",
            "RMS",
        ],
        help=(
            "Resampling used to build internal COG overviews. "
            "Default: AVERAGE."
        ),
    )

    args = parser.parse_args()

    try:
        if len(args.raster) != len(args.hdr):
            raise ValueError(
                "The number of --raster inputs must match "
                "the number of --hdr inputs."
            )

        output_paths = make_tiffs(
            raster_header_pairs=list(
                zip(
                    args.raster,
                    args.hdr,
                )
            ),
            output_dir=args.output_dir,
            nodata=_parse_nodata(
                args.nodata
            ),
            invalid_min=args.invalid_min,
            clip_min=args.clip_min,
            overwrite=args.overwrite,
            suffix=args.suffix,
            extension=args.extension,
            compress=args.compress,
            block_size=args.block_size,
            overview_resampling=args.overview_resampling,
        )

        print(
            "Wrote GeoTIFF file(s):"
        )

        for output_path in output_paths:
            print(
                f"  - {output_path}"
            )

        return 0

    except Exception as exc:
        print(
            f"\nERROR: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
