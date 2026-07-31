import json
import re
from pathlib import Path


def _metadata_key(value):
    """
    Convert a metadata path into a GeoTIFF-safe uppercase tag name.

    Example
    -------
    grd_pwr.set_rows -> UAVSAR_GRD_PWR_SET_ROWS
    """
    value = re.sub(r"[^A-Za-z0-9]+", "_", str(value))
    value = re.sub(r"_+", "_", value)
    return value.strip("_").upper()


def _flatten_metadata(data, prefix=""):
    """
    Flatten a nested metadata dictionary into string-valued GeoTIFF tags.

    Example
    -------
    {
        "grd_pwr": {
            "set_rows": "13275"
        }
    }

    becomes:

    {
        "UAVSAR_GRD_PWR_SET_ROWS": "13275"
    }
    """
    flattened = {}

    for key, value in data.items():
        path = f"{prefix}_{key}" if prefix else str(key)

        if isinstance(value, dict):
            flattened.update(
                _flatten_metadata(value, prefix=path)
            )

        elif value is not None:
            tag_name = f"UAVSAR_{_metadata_key(path)}"

            if isinstance(value, (list, tuple)):
                tag_value = json.dumps(
                    value,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            else:
                tag_value = str(value)

            flattened[tag_name] = tag_value

    return flattened


def _infer_polarization(filename):
    """
    Infer UAVSAR polarization from the raster filename.
    """
    match = re.search(
        r"(HHHH|HVHV|VVVV|HHHV|HHVV|HVVV)",
        str(filename).upper(),
    )

    return match.group(1) if match else None


def make_tiff(
    raster_path,
    header_path,
    output_dir,
    nodata=None,
    invalid_min=0.0,
    overwrite=False,
    suffix="_tif",
    extension=".tif",
    compress="DEFLATE",
    block_size=512,
    metadata=None,
):
    """
    Convert a UAVSAR ENVI raster to a single-band tiled/compressed GeoTIFF.

    The output contains:

      - one float32 band
      - invalid pixels written as nodata
      - tiled and compressed storage
      - no alpha band
      - no internal mask
      - UAVSAR annotation metadata embedded as GeoTIFF tags

    Metadata behavior
    -----------------
    If ``metadata`` is supplied, the complete nested dictionary is stored
    in the ``UAVSAR_ANNOTATION_JSON`` tag.

    Scalar metadata fields are also flattened into individual tags such as:

        UAVSAR_GLOBAL_SITE_DESCRIPTION
        UAVSAR_GRD_PWR_SET_ROWS

    Parameters
    ----------
    raster_path : str or pathlib.Path
        Input UAVSAR raster binary, for example .grd, .inc, .hgt, or .slope.

    header_path : str or pathlib.Path
        Explicit ENVI header file.

    output_dir : str or pathlib.Path
        Directory where the GeoTIFF will be written.

    nodata : None or float
        Output nodata value. None means NaN.

    invalid_min : float
        Values less than or equal to this are replaced by nodata.

    overwrite : bool
        If True, replace an existing output file.

    suffix : str
        Suffix added to the raster stem.

    extension : str
        Output extension.

    compress : str
        GeoTIFF compression method.

    block_size : int
        Internal tile size.

    metadata : dict or None
        Nested UAVSAR metadata dictionary, normally created by
        ``annotation_to_nested_json_dict``.

    Returns
    -------
    pathlib.Path
        Path to the written GeoTIFF.
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

    if metadata is not None and not isinstance(metadata, dict):
        raise TypeError(
            "metadata must be a dictionary or None, "
            f"not {type(metadata).__name__}"
        )

    if nodata is None:
        nodata = np.nan
    else:
        nodata = float(nodata)

    invalid_min = float(invalid_min)

    if not raster_path.exists():
        raise FileNotFoundError(
            f"Raster file not found: {raster_path}"
        )

    if not header_path.exists():
        raise FileNotFoundError(
            f"Header file not found: {header_path}"
        )

    if not raster_path.is_file():
        raise ValueError(
            f"Raster path is not a file: {raster_path}"
        )

    if not header_path.is_file():
        raise ValueError(
            f"Header path is not a file: {header_path}"
        )

    if not isinstance(block_size, int):
        raise TypeError(
            "block_size must be an integer, "
            f"not {type(block_size).__name__}"
        )

    if block_size <= 0:
        raise ValueError(
            "block_size must be greater than zero."
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
            "Use overwrite=True to replace it."
        )

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

            polarization = _infer_polarization(
                raster_path.name
            )

            dataset_tags = {
                "MISSION": "UAVSAR",
                "SENSOR": "UAVSAR",
                "PRODUCT_TYPE": "GRD",
                "SOURCE_RASTER": raster_path.name,
                "SOURCE_HEADER": header_path.name,
                "DATA_TYPE": "FLOAT32",
                "DATA_UNITS": "LINEAR_POWER",
                "PROCESSING_SOFTWARE": "DANSAR",
            }

            if polarization is not None:
                dataset_tags["POLARIZATION"] = polarization

            if metadata is not None:
                # Complete lossless representation of the parsed annotation.
                dataset_tags["UAVSAR_ANNOTATION_JSON"] = json.dumps(
                    metadata,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )

                # Individual searchable fields.
                dataset_tags.update(
                    _flatten_metadata(metadata)
                )

            with rasterio.open(
                final_tiff,
                "w",
                **profile,
            ) as dst:
                dst.write(arr, 1)

                # Dataset-level metadata.
                dst.update_tags(**dataset_tags)

                # Band-level semantic metadata.
                band_description = (
                    polarization
                    if polarization is not None
                    else raster_path.stem
                )

                dst.set_band_description(
                    1,
                    band_description,
                )

                dst.update_tags(
                    1,
                    POLARIZATION=(
                        polarization or "UNKNOWN"
                    ),
                    DATA_UNITS="LINEAR_POWER",
                    LONG_NAME=(
                        "UAVSAR calibrated ground-range "
                        "backscatter power"
                    ),
                )

        return final_tiff

    finally:
        if temporary_header is not None:
            temporary_header.unlink(
                missing_ok=True
            )
