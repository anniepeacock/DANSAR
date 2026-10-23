"""
make_gee_asset.py

Group five single-band UAVSAR COGs from one PolSAR acquisition into
one 5-band ingested Earth Engine image asset.

Expected bands:

    HH
    HV
    VV
    INC
    MASK

GRD and INC are components of the same UAVSAR PolSAR product.
MASK is derived from INC.

Workflow:

    local COG directory
        -> upload each COG to GCS
        -> build one 5-band EE manifest per acquisition
        -> earthengine upload image --manifest ...

Authentication is intentionally external to this script.

Typical Colab usage after authentication:

    from dansar.utils.make_gee_asset import make_gee_assets

    make_gee_assets(
        input_dir=OUTPUT_DIR,
        bucket=GCS_BUCKET,
        asset_parent=ASSET_PARENT,
    )
"""

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import rasterio
from google.cloud import storage


POLARIZATION_MAP = {
    "HHHH": "HH",
    "HVHV": "HV",
    "VVVV": "VV",
}


EXPECTED_BANDS = (
    "HH",
    "HV",
    "VV",
    "INC",
    "MASK",
)


# ---------------------------------------------------------------------
# File discovery and metadata
# ---------------------------------------------------------------------

def find_cogs(input_dir):
    """
    Return TIFF files in input_dir, sorted by filename.
    """

    input_dir = Path(input_dir)

    if not input_dir.is_dir():
        raise NotADirectoryError(
            f"Input directory does not exist: {input_dir}"
        )

    cogs = sorted(
        path
        for path in input_dir.iterdir()
        if path.is_file()
        and path.suffix.lower() in {".tif", ".tiff"}
    )

    if not cogs:
        raise FileNotFoundError(
            f"No TIFF files found in: {input_dir}"
        )

    return cogs


def read_tags(tiff_path):
    """
    Read dataset-level GeoTIFF tags.
    """

    with rasterio.open(tiff_path) as src:
        return src.tags()


def require_tag(tags, key, tiff_path):
    """
    Return a required GeoTIFF tag.
    """

    value = tags.get(key)

    if value is None or str(value).strip() == "":
        raise KeyError(
            f"Missing GeoTIFF tag '{key}' in {tiff_path}"
        )

    return str(value).strip()


# ---------------------------------------------------------------------
# Acquisition date handling
# ---------------------------------------------------------------------

def to_iso8601(value):
    """
    Convert acquisition date string to ISO 8601 UTC.
    """

    value = str(value).strip()

    formats = (
        "%d-%b-%Y %H:%M:%S UTC",
        "%d-%B-%Y %H:%M:%S UTC",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
    )

    for fmt in formats:
        try:
            dt = datetime.strptime(
                value,
                fmt,
            )

            dt = dt.replace(
                tzinfo=timezone.utc
            )

            return dt.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

        except ValueError:
            pass

    raise ValueError(
        f"Could not parse ACQUISITION_DATE: {value!r}"
    )


# ---------------------------------------------------------------------
# UAVSAR naming helpers
# ---------------------------------------------------------------------

def infer_polarization(granule_id):
    """
    Infer UAVSAR polarization token and two-letter band ID
    from a polarization-specific GRD granule ID.

    Example:

        Amaleb_..._L090HHHH_CX_01
            -> ("HHHH", "HH")
    """

    for token, band_id in POLARIZATION_MAP.items():
        if token in granule_id:
            return token, band_id

    raise ValueError(
        "Could not infer polarization from granule_id: "
        f"{granule_id}"
    )


def acquisition_granule_id(granule_id):
    """
    Remove polarization token from a polarization-specific
    GRD granule ID.

    Example:

        Amaleb_..._L090HHHH_CX_01
            ->
        Amaleb_..._L090_CX_01
    """

    token, _ = infer_polarization(
        granule_id
    )

    return granule_id.replace(
        token,
        "",
        1,
    )


def infer_band_and_acquisition(
    tiff_path,
    tags,
):
    """
    Determine the Earth Engine band ID and acquisition-level
    UAVSAR PolSAR granule ID for one COG.

    GRD polarization TIFFs:
        band = HH / HV / VV
        acquisition ID is obtained by removing HHHH/HVHV/VVVV
        from the polarization-specific GRANULE_ID.

    INC:
        band = INC
        GRANULE_ID is already the acquisition-level PolSAR ID.

    MASK:
        band = MASK
        derived from INC and uses the same acquisition-level ID.

    Returns
    -------
    tuple
        (band_id, acquisition_id, source_granule_id)
    """

    granule_id = require_tag(
        tags,
        "GRANULE_ID",
        tiff_path,
    )

    product_type = str(
        tags.get(
            "PRODUCT_TYPE",
            "",
        )
    ).strip().upper()

    # ---------------------------------------------------------
    # Ancillary / QA products
    # ---------------------------------------------------------

    if product_type == "INC":
        return (
            "INC",
            granule_id,
            granule_id,
        )

    if product_type == "MASK":
        return (
            "MASK",
            granule_id,
            granule_id,
        )

    # ---------------------------------------------------------
    # Polarimetric GRD products
    # ---------------------------------------------------------

    _, band_id = infer_polarization(
        granule_id
    )

    acquisition_id = acquisition_granule_id(
        granule_id
    )

    return (
        band_id,
        acquisition_id,
        granule_id,
    )


# ---------------------------------------------------------------------
# Group COGs by UAVSAR acquisition
# ---------------------------------------------------------------------

def group_cogs_by_acquisition(cog_paths):
    """
    Group UAVSAR COGs by PolSAR acquisition.

    Expected bands for every acquisition:

        HH
        HV
        VV
        INC
        MASK

    Returns
    -------
    dict

        {
            acquisition_granule_id: {
                "HH": {
                    "path": Path,
                    "tags": dict,
                    "source_granule_id": str,
                },
                "HV": {...},
                "VV": {...},
                "INC": {...},
                "MASK": {...},
            }
        }
    """

    groups = {}

    for tiff_path in cog_paths:

        tags = read_tags(
            tiff_path
        )

        (
            band_id,
            acquisition_id,
            source_granule_id,
        ) = infer_band_and_acquisition(
            tiff_path=tiff_path,
            tags=tags,
        )

        groups.setdefault(
            acquisition_id,
            {},
        )

        if band_id in groups[acquisition_id]:
            raise ValueError(
                f"Duplicate band {band_id} for acquisition "
                f"{acquisition_id}: {tiff_path}"
            )

        groups[acquisition_id][band_id] = {
            "path": tiff_path,
            "tags": tags,
            "source_granule_id": source_granule_id,
        }

    required = set(
        EXPECTED_BANDS
    )

    for acquisition_id, members in groups.items():

        member_ids = set(
            members
        )

        missing = (
            required
            - member_ids
        )

        extra = (
            member_ids
            - required
        )

        if missing:
            raise ValueError(
                f"Acquisition {acquisition_id} "
                f"is missing band(s): "
                f"{sorted(missing)}"
            )

        if extra:
            raise ValueError(
                f"Acquisition {acquisition_id} "
                f"has unexpected band(s): "
                f"{sorted(extra)}"
            )

    return groups


# ---------------------------------------------------------------------
# Google Cloud Storage upload
# ---------------------------------------------------------------------

def upload_to_gcs(
    client,
    bucket_name,
    local_path,
    object_name,
    overwrite=False,
):
    """
    Upload one local COG to Google Cloud Storage.
    """

    bucket = client.bucket(
        bucket_name
    )

    blob = bucket.blob(
        object_name
    )

    if blob.exists(
        client=client
    ):

        if not overwrite:
            print(
                "GCS exists, keeping:",
                f"gs://{bucket_name}/{object_name}",
            )

            return (
                f"gs://{bucket_name}/{object_name}"
            )

        print(
            "Replacing GCS object:",
            f"gs://{bucket_name}/{object_name}",
        )

    else:
        print(
            "Uploading:",
            local_path.name,
        )

    blob.upload_from_filename(
        str(local_path)
    )

    return (
        f"gs://{bucket_name}/{object_name}"
    )


# ---------------------------------------------------------------------
# Earth Engine manifest
# ---------------------------------------------------------------------

def build_manifest(
    acquisition_id,
    group,
    gcs_uris,
    asset_parent,
):
    """
    Build one 5-band Earth Engine ImageManifest from five
    separate UAVSAR COGs.

    Bands
    -----
    HH
        Co-polarized HH backscatter.

    HV
        Cross-polarized HV backscatter.

    VV
        Co-polarized VV backscatter.

    INC
        UAVSAR local incidence angle, converted from radians
        to whole degrees.

        uint8
        255 = NoData

    MASK
        Derived QA layer.

        1 = valid
        2 = invalid incidence angle
        3 = no data

    The GeoTIFFs remain the source of truth for projection,
    transform, pixel type, and NoData.
    """

    representative_tags = (
        group["HH"]["tags"]
    )

    inc_tags = (
        group["INC"]["tags"]
    )

    mask_tags = (
        group["MASK"]["tags"]
    )

    acquisition_date = require_tag(
        representative_tags,
        "ACQUISITION_DATE",
        group["HH"]["path"],
    )

    # ---------------------------------------------------------
    # Common image-level metadata
    # ---------------------------------------------------------

    property_map = {
        "PRODUCT_TYPE": "product_type",
        "UNITS": "units",
        "CENTER_LATITUDE": "center_latitude",
        "CENTER_LONGITUDE": "center_longitude",
        "ORIGINAL_PIXEL_POSTING_LATITUDE": (
            "pixel_posting_latitude"
        ),
        "ORIGINAL_PIXEL_POSTING_LONGITUDE": (
            "pixel_posting_longitude"
        ),
        "PIXEL_POSTING_UNITS": (
            "pixel_posting_units"
        ),
        "DATA_ACCESS": "data_access",
    }

    properties = {
        ee_key: representative_tags[tiff_key]
        for tiff_key, ee_key
        in property_map.items()
        if tiff_key in representative_tags
    }

    # ---------------------------------------------------------
    # Product identification
    # ---------------------------------------------------------

    properties["granule_id"] = (
        acquisition_id
    )

    properties["polarizations"] = (
        "HH,HV,VV"
    )

    properties["bands"] = (
        "HH,HV,VV,INC,MASK"
    )

    properties["description"] = (
        "UAVSAR PolSAR ground-range backscatter "
        "with local incidence angle and derived "
        "per-pixel quality mask."
    )

    # ---------------------------------------------------------
    # GRD provenance
    # ---------------------------------------------------------

    properties["hh_granule_id"] = (
        group["HH"]["source_granule_id"]
    )

    properties["hv_granule_id"] = (
        group["HV"]["source_granule_id"]
    )

    properties["vv_granule_id"] = (
        group["VV"]["source_granule_id"]
    )

    # ---------------------------------------------------------
    # INC metadata
    # ---------------------------------------------------------

    properties["inc_source"] = (
        "UAVSAR PolSAR INC"
    )

    properties["inc_units"] = (
        "degrees"
    )

    properties["inc_storage_type"] = (
        "uint8"
    )

    properties["inc_nodata"] = (
        255
    )

    properties["inc_description"] = (
        "Local incidence angle converted from "
        "UAVSAR INC radians to degrees and rounded "
        "to the nearest whole degree."
    )

    if "UNITS" in inc_tags:
        properties["inc_geotiff_units"] = (
            inc_tags["UNITS"]
        )

    # ---------------------------------------------------------
    # MASK metadata
    # ---------------------------------------------------------

    properties["mask_source"] = (
        "derived from INC"
    )

    properties["mask_storage_type"] = (
        "uint8"
    )

    properties["mask_value_1"] = (
        "valid"
    )

    properties["mask_value_2"] = (
        "invalid_incidence_angle"
    )

    properties["mask_value_3"] = (
        "no_data"
    )

    if (
        "VALID_INC_MIN_DEGREES"
        in mask_tags
    ):
        properties[
            "valid_inc_min_degrees"
        ] = float(
            mask_tags[
                "VALID_INC_MIN_DEGREES"
            ]
        )

    else:
        properties[
            "valid_inc_min_degrees"
        ] = 20.0

    if (
        "VALID_INC_MAX_DEGREES"
        in mask_tags
    ):
        properties[
            "valid_inc_max_degrees"
        ] = float(
            mask_tags[
                "VALID_INC_MAX_DEGREES"
            ]
        )

    else:
        properties[
            "valid_inc_max_degrees"
        ] = 70.0

    # ---------------------------------------------------------
    # Manifest
    # ---------------------------------------------------------

    return {

        "name": (
            f"{str(asset_parent).rstrip('/')}/"
            f"{acquisition_id}"
        ),

        "tilesets": [

            {
                "id": "HH",
                "sources": [
                    {
                        "uris": [
                            gcs_uris["HH"]
                        ]
                    }
                ],
            },

            {
                "id": "HV",
                "sources": [
                    {
                        "uris": [
                            gcs_uris["HV"]
                        ]
                    }
                ],
            },

            {
                "id": "VV",
                "sources": [
                    {
                        "uris": [
                            gcs_uris["VV"]
                        ]
                    }
                ],
            },

            {
                "id": "INC",
                "sources": [
                    {
                        "uris": [
                            gcs_uris["INC"]
                        ]
                    }
                ],
            },

            {
                "id": "MASK",
                "sources": [
                    {
                        "uris": [
                            gcs_uris["MASK"]
                        ]
                    }
                ],
            },
        ],

        "bands": [

            {
                "id": "HH",
                "tilesetId": "HH",
                "tilesetBandIndex": 0,
                "pyramidingPolicy": "MEAN",
            },

            {
                "id": "HV",
                "tilesetId": "HV",
                "tilesetBandIndex": 0,
                "pyramidingPolicy": "MEAN",
            },

            {
                "id": "VV",
                "tilesetId": "VV",
                "tilesetBandIndex": 0,
                "pyramidingPolicy": "MEAN",
            },

            {
                "id": "INC",
                "tilesetId": "INC",
                "tilesetBandIndex": 0,
                "pyramidingPolicy": "MEAN",
            },

            {
                "id": "MASK",
                "tilesetId": "MASK",
                "tilesetBandIndex": 0,

                # Earth Engine recommends SAMPLE for
                # QA / bitmask / other non-continuous
                # ancillary fields.
                "pyramidingPolicy": "SAMPLE",
            },
        ],

        "properties": properties,

        "startTime": to_iso8601(
            acquisition_date
        ),
    }


# ---------------------------------------------------------------------
# Manifest file
# ---------------------------------------------------------------------

def write_manifest(
    manifest,
    manifest_dir,
):
    """
    Write one manifest JSON to disk.
    """

    manifest_dir = Path(
        manifest_dir
    )

    manifest_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    granule_id = (
        manifest["properties"][
            "granule_id"
        ]
    )

    path = (
        manifest_dir
        / f"{granule_id}.manifest.json"
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as dst:

        json.dump(
            manifest,
            dst,
            indent=2,
        )

        dst.write(
            "\n"
        )

    return path


# ---------------------------------------------------------------------
# Earth Engine CLI
# ---------------------------------------------------------------------

def create_ee_asset(
    manifest_path,
):
    """
    Create one ingested Earth Engine image asset.
    """

    earthengine = shutil.which(
        "earthengine"
    )

    if earthengine is None:
        raise FileNotFoundError(
            "earthengine CLI not found. "
            "Install earthengine-api."
        )

    subprocess.run(
        [
            earthengine,
            "upload",
            "image",
            "--manifest",
            str(manifest_path),
        ],
        check=True,
    )


# ---------------------------------------------------------------------
# Main workflow
# ---------------------------------------------------------------------

def make_gee_assets(
    input_dir,
    bucket,
    asset_parent,
    gcs_prefix="",
    manifest_dir=None,
    overwrite_gcs=False,
    dry_run=False,
):
    """
    Create one 5-band ingested Earth Engine image per UAVSAR
    PolSAR acquisition.

    Required COGs:

        HH
        HV
        VV
        INC
        MASK
    """

    input_dir = Path(
        input_dir
    )

    if manifest_dir is None:
        manifest_dir = (
            input_dir
            / "gee_manifests"
        )

    cogs = find_cogs(
        input_dir
    )

    groups = group_cogs_by_acquisition(
        cogs
    )

    client = storage.Client()

    bucket_info = client.get_bucket(
        bucket
    )

    print(
        "Bucket:",
        bucket_info.name,
    )

    print(
        "  location:",
        bucket_info.location,
    )

    print(
        "  storage class:",
        bucket_info.storage_class,
    )

    print(
        "Acquisitions found:",
        len(groups),
    )

    results = []

    for (
        acquisition_id,
        group,
    ) in sorted(
        groups.items()
    ):

        print()
        print(
            "Acquisition:",
            acquisition_id,
        )

        prefix = str(
            gcs_prefix
        ).strip("/")

        gcs_uris = {}

        for band_id in EXPECTED_BANDS:

            tiff_path = (
                group[band_id]["path"]
            )

            object_name = (
                f"{prefix}/{tiff_path.name}"
                if prefix
                else tiff_path.name
            )

            gcs_uri = (
                f"gs://{bucket}/"
                f"{object_name}"
            )

            if dry_run:

                print(
                    "Would use:",
                    band_id,
                    "->",
                    gcs_uri,
                )

            else:

                gcs_uri = upload_to_gcs(
                    client=client,
                    bucket_name=bucket,
                    local_path=tiff_path,
                    object_name=object_name,
                    overwrite=overwrite_gcs,
                )

            gcs_uris[
                band_id
            ] = gcs_uri

        manifest = build_manifest(
            acquisition_id=acquisition_id,
            group=group,
            gcs_uris=gcs_uris,
            asset_parent=asset_parent,
        )

        manifest_path = write_manifest(
            manifest=manifest,
            manifest_dir=manifest_dir,
        )

        print(
            "Manifest:",
            manifest_path.name,
        )

        if dry_run:

            print(
                "Dry run:",
                manifest["name"],
            )

        else:

            print(
                "Creating Earth Engine asset:",
                manifest["name"],
            )

            create_ee_asset(
                manifest_path
            )

        results.append(
            manifest["name"]
        )

    return results


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Upload a local directory of UAVSAR PolSAR "
            "HH/HV/VV/INC/MASK COGs to GCS and create "
            "one 5-band Earth Engine image asset "
            "per acquisition."
        )
    )

    parser.add_argument(
        "input_dir",
        help=(
            "Directory containing UAVSAR "
            "HH/HV/VV/INC/MASK COG "
            ".tif/.tiff files."
        ),
    )

    parser.add_argument(
        "--bucket",
        required=True,
        help=(
            "GCS bucket name, without gs://."
        ),
    )

    parser.add_argument(
        "--asset-parent",
        required=True,
        help=(
            "Earth Engine parent path, e.g. "
            "projects/MY_PROJECT/assets/uavsar"
        ),
    )

    parser.add_argument(
        "--gcs-prefix",
        default="",
        help=(
            "Optional path inside the bucket."
        ),
    )

    parser.add_argument(
        "--manifest-dir",
        default=None,
        help=(
            "Where to save manifests. "
            "Default: INPUT_DIR/gee_manifests"
        ),
    )

    parser.add_argument(
        "--overwrite-gcs",
        action="store_true",
        help=(
            "Replace existing GCS objects."
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Write manifests only; "
            "do not upload or create assets."
        ),
    )

    args = parser.parse_args()

    try:

        assets = make_gee_assets(
            input_dir=args.input_dir,
            bucket=args.bucket,
            asset_parent=args.asset_parent,
            gcs_prefix=args.gcs_prefix,
            manifest_dir=args.manifest_dir,
            overwrite_gcs=args.overwrite_gcs,
            dry_run=args.dry_run,
        )

        print()

        print(
            f"Processed {len(assets)} asset(s)."
        )

        return 0

    except Exception as exc:

        print(
            f"ERROR: {exc}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
