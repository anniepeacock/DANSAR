"""
make_gee_asset.py

Minimal workflow:
local COG directory -> Google Cloud Storage -> Earth Engine COG-backed assets

Authentication is intentionally external to this script.

Typical local setup:
    gcloud auth application-default login
    earthengine authenticate --auth_mode=gcloud

Requirements:
    pip install rasterio google-cloud-storage earthengine-api
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


def find_cogs(input_dir):
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
    with rasterio.open(tiff_path) as src:
        return src.tags()


def require_tag(tags, key, tiff_path):
    value = tags.get(key)

    if value is None or str(value).strip() == "":
        raise KeyError(
            f"Missing GeoTIFF tag '{key}' in {tiff_path}"
        )

    return str(value).strip()


def to_iso8601(value):
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


def upload_to_gcs(
    client,
    bucket_name,
    local_path,
    object_name,
    overwrite=False,
):
    bucket = client.bucket(
        bucket_name
    )

    blob = bucket.blob(
        object_name
    )

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
        print(
            "Uploading:",
            local_path.name,
        )

    blob.upload_from_filename(
        str(local_path)
    )

    return f"gs://{bucket_name}/{object_name}"


def build_manifest(
    tiff_path,
    gcs_uri,
    asset_parent,
):
    tags = read_tags(
        tiff_path
    )

    granule_id = require_tag(
        tags,
        "GRANULE_ID",
        tiff_path,
    )

    acquisition_date = require_tag(
        tags,
        "ACQUISITION_DATE",
        tiff_path,
    )

    property_keys = (
        "GRANULE_ID",
        "PRODUCT_TYPE",
        "UNITS",
        "CENTER_LATITUDE",
        "CENTER_LONGITUDE",
        "ORIGINAL_PIXEL_POSTING_LATITUDE",
        "ORIGINAL_PIXEL_POSTING_LONGITUDE",
        "PIXEL_POSTING_UNITS",
        "DATA_ACCESS",
    )

    properties = {
        key: tags[key]
        for key in property_keys
        if key in tags
    }

    return {
        "name": (
            f"{str(asset_parent).rstrip('/')}/"
            f"{granule_id}"
        ),
        "tilesets": [
            {
                "id": "source",
                "sources": [
                    {
                        "uris": [
                            gcs_uri
                        ]
                    }
                ],
            }
        ],
        "properties": properties,
        "startTime": to_iso8601(
            acquisition_date
        ),
    }


def write_manifest(
    manifest,
    manifest_dir,
):
    manifest_dir = Path(
        manifest_dir
    )

    manifest_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    granule_id = manifest[
        "properties"
    ][
        "GRANULE_ID"
    ]

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

        dst.write("\n")

    return path


def create_ee_asset(
    manifest_path,
):
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
            "external_image",
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
        "COGs found:",
        len(cogs),
    )

    results = []

    for tiff_path in cogs:
        tags = read_tags(
            tiff_path
        )

        granule_id = require_tag(
            tags,
            "GRANULE_ID",
            tiff_path,
        )

        prefix = str(
            gcs_prefix
        ).strip("/")

        object_name = (
            f"{prefix}/{tiff_path.name}"
            if prefix
            else tiff_path.name
        )

        gcs_uri = (
            f"gs://{bucket}/{object_name}"
        )

        if not dry_run:
            gcs_uri = upload_to_gcs(
                client=client,
                bucket_name=bucket,
                local_path=tiff_path,
                object_name=object_name,
                overwrite=overwrite_gcs,
            )

        manifest = build_manifest(
            tiff_path=tiff_path,
            gcs_uri=gcs_uri,
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


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Upload a local directory of COGs to GCS and "
            "create Earth Engine COG-backed assets."
        )
    )

    parser.add_argument(
        "input_dir",
        help="Directory containing COG .tif/.tiff files.",
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
            "Where to save manifests. "
            "Default: INPUT_DIR/gee_manifests"
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
