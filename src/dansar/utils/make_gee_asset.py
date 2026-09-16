"""
make_gee_asset.py

Group three single-band UAVSAR COGs (HH, HV, VV) from one acquisition into
one 3-band ingested Earth Engine image asset.

Workflow:
    local COG directory
        -> upload each COG to GCS
        -> build one 3-band EE manifest per acquisition
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


def find_cogs(input_dir):
    """Return TIFF files in input_dir, sorted by filename."""
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
    """Read dataset-level GeoTIFF tags."""
    with rasterio.open(tiff_path) as src:
        return src.tags()


def require_tag(tags, key, tiff_path):
    """Return a required GeoTIFF tag."""
    value = tags.get(key)

    if value is None or str(value).strip() == "":
        raise KeyError(
            f"Missing GeoTIFF tag '{key}' in {tiff_path}"
        )

    return str(value).strip()


def to_iso8601(value):
    """Convert acquisition date string to ISO 8601 UTC."""
    value = str(value).strip()

    formats = (
        "%d-%b-%Y %H:%M:%S UTC",
        "%d-%B-%Y %H:%M:%S UTC",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
    )

    for fmt in formats:
        try:
            dt = datetime.strptime(value, fmt)
            dt = dt.replace(tzinfo=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            pass

    raise ValueError(
        f"Could not parse ACQUISITION_DATE: {value!r}"
    )


def infer_polarization(granule_id):
    """Infer polarization token and 2-letter band id from granule id."""
    for token, band_id in POLARIZATION_MAP.items():
        if token in granule_id:
            return token, band_id

    raise ValueError(
        "Could not infer polarization from granule_id: "
        f"{granule_id}"
    )


def acquisition_granule_id(granule_id):
    """Remove the polarization token from a single-band granule id."""
    token, _ = infer_polarization(granule_id)
    return granule_id.replace(token, "", 1)


def group_cogs_by_acquisition(cog_paths):
    """
    Group TIFFs by acquisition, expecting one HH, one HV, and one VV COG.

    Returns:
        dict[base_granule_id] -> {
            "HH": {"path": Path, "tags": dict, "source_granule_id": str},
            "HV": {...},
            "VV": {...},
        }
    """
    groups = {}

    for tiff_path in cog_paths:
        tags = read_tags(tiff_path)
        granule_id = require_tag(
            tags,
            "GRANULE_ID",
            tiff_path,
        )

        _, band_id = infer_polarization(granule_id)
        base_id = acquisition_granule_id(granule_id)

        groups.setdefault(base_id, {})

        if band_id in groups[base_id]:
            raise ValueError(
                f"Duplicate polarization {band_id} for acquisition "
                f"{base_id}: {tiff_path}"
            )

        groups[base_id][band_id] = {
            "path": tiff_path,
            "tags": tags,
            "source_granule_id": granule_id,
        }

    required = {"HH", "HV", "VV"}

    for base_id, members in groups.items():
        missing = required - set(members)
        extra = set(members) - required

        if missing:
            raise ValueError(
                f"Acquisition {base_id} is missing polarization(s): "
                f"{sorted(missing)}"
            )

        if extra:
            raise ValueError(
                f"Acquisition {base_id} has unexpected polarization(s): "
                f"{sorted(extra)}"
            )

    return groups


def upload_to_gcs(
    client,
    bucket_name,
    local_path,
    object_name,
    overwrite=False,
):
    """Upload one local COG to Google Cloud Storage."""
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)

    if blob.exists(client=client):
        if not overwrite:
            print(
                "GCS exists, keeping:",
                f"gs://{bucket_name}/{object_name}",
            )
            return f"gs://{bucket_name}/{object_name}"

        print(
            "Replacing GCS object:",
            f"gs://{bucket_name}/{object_name}",
        )
    else:
        print("Uploading:", local_path.name)

    blob.upload_from_filename(str(local_path))
    return f"gs://{bucket_name}/{object_name}"


def build_manifest(
    acquisition_id,
    group,
    gcs_uris,
    asset_parent,
):
    """
    Build one 3-band Earth Engine ImageManifest from 3 separate COGs.

    The GeoTIFF header remains the source of truth.
    """
    representative_tags = group["HH"]["tags"]

    acquisition_date = require_tag(
        representative_tags,
        "ACQUISITION_DATE",
        group["HH"]["path"],
    )

    property_map = {
        "PRODUCT_TYPE": "product_type",
        "UNITS": "units",
        "CENTER_LATITUDE": "center_latitude",
        "CENTER_LONGITUDE": "center_longitude",
        "ORIGINAL_PIXEL_POSTING_LATITUDE": "pixel_posting_latitude",
        "ORIGINAL_PIXEL_POSTING_LONGITUDE": "pixel_posting_longitude",
        "PIXEL_POSTING_UNITS": "pixel_posting_units",
        "DATA_ACCESS": "data_access",
    }

    properties = {
        ee_key: representative_tags[tiff_key]
        for tiff_key, ee_key in property_map.items()
        if tiff_key in representative_tags
    }

    product_type = representative_tags.get("PRODUCT_TYPE", "UAVSAR raster")
    units = representative_tags.get("UNITS")

    description = f"UAVSAR {product_type} image with bands HH, HV, VV"
    if units:
        description += f"; units: {units}"
    description += "."

    properties["granule_id"] = acquisition_id
    properties["polarizations"] = "HH,HV,VV"
    properties["description"] = description
    properties["hh_granule_id"] = group["HH"]["source_granule_id"]
    properties["hv_granule_id"] = group["HV"]["source_granule_id"]
    properties["vv_granule_id"] = group["VV"]["source_granule_id"]

    return {
        "name": (
            f"{str(asset_parent).rstrip('/')}/"
            f"{acquisition_id}"
        ),
        "tilesets": [
            {
                "id": "HH",
                "sources": [
                    {"uris": [gcs_uris["HH"]]}
                ],
            },
            {
                "id": "HV",
                "sources": [
                    {"uris": [gcs_uris["HV"]]}
                ],
            },
            {
                "id": "VV",
                "sources": [
                    {"uris": [gcs_uris["VV"]]}
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
        ],
        "properties": properties,
        "startTime": to_iso8601(acquisition_date),
    }


def write_manifest(manifest, manifest_dir):
    """Write one manifest JSON to disk."""
    manifest_dir = Path(manifest_dir)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    granule_id = manifest["properties"]["granule_id"]
    path = manifest_dir / f"{granule_id}.manifest.json"

    with path.open("w", encoding="utf-8") as dst:
        json.dump(manifest, dst, indent=2)
        dst.write("\n")

    return path


def create_ee_asset(manifest_path):
    """Create one ingested Earth Engine image asset."""
    earthengine = shutil.which("earthengine")

    if earthengine is None:
        raise FileNotFoundError(
            "earthengine CLI not found. Install earthengine-api."
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
    Create one 3-band ingested EE image per acquisition from HH/HV/VV COGs.
    """
    input_dir = Path(input_dir)

    if manifest_dir is None:
        manifest_dir = input_dir / "gee_manifests"

    cogs = find_cogs(input_dir)
    groups = group_cogs_by_acquisition(cogs)

    client = storage.Client()
    bucket_info = client.get_bucket(bucket)

    print("Bucket:", bucket_info.name)
    print("  location:", bucket_info.location)
    print("  storage class:", bucket_info.storage_class)
    print("Acquisitions found:", len(groups))

    results = []

    for acquisition_id, group in sorted(groups.items()):
        prefix = str(gcs_prefix).strip("/")
        gcs_uris = {}

        for band_id in ("HH", "HV", "VV"):
            tiff_path = group[band_id]["path"]

            object_name = (
                f"{prefix}/{tiff_path.name}"
                if prefix
                else tiff_path.name
            )

            gcs_uri = f"gs://{bucket}/{object_name}"

            if not dry_run:
                gcs_uri = upload_to_gcs(
                    client=client,
                    bucket_name=bucket,
                    local_path=tiff_path,
                    object_name=object_name,
                    overwrite=overwrite_gcs,
                )

            gcs_uris[band_id] = gcs_uri

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

        print("Manifest:", manifest_path.name)

        if dry_run:
            print("Dry run:", manifest["name"])
        else:
            print("Creating Earth Engine asset:", manifest["name"])
            create_ee_asset(manifest_path)

        results.append(manifest["name"])

    return results


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Upload a local directory of UAVSAR COGs to GCS and create "
            "one 3-band ingested Earth Engine image asset per acquisition."
        )
    )

    parser.add_argument(
        "input_dir",
        help="Directory containing HH/HV/VV COG .tif/.tiff files.",
    )

    parser.add_argument(
        "--bucket",
        required=True,
        help="GCS bucket name, without gs://.",
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
        help="Optional path inside the bucket.",
    )

    parser.add_argument(
        "--manifest-dir",
        default=None,
        help=(
            "Where to save manifests. Default: INPUT_DIR/gee_manifests"
        ),
    )

    parser.add_argument(
        "--overwrite-gcs",
        action="store_true",
        help="Replace existing GCS objects.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write manifests only; do not upload or create assets.",
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
        print(f"Processed {len(assets)} asset(s).")
        return 0

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
