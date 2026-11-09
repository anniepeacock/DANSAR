#!/usr/bin/env python3
import argparse
import csv
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter

import numpy as np

from dansar.uavsar.ann2envi_header import ann2envi_header
from dansar.uavsar.make_tiff import make_tiff, make_inc_mask_tiffs
from dansar.utils.make_asf_session import make_asf_session


class AsfS3Credentials:
    def __init__(self):
        self.session, self.credentials = make_asf_session()

    def refresh(self):
        response = self.session.get(
            "https://cumulus.asf.alaska.edu/s3credentials", timeout=30
        )
        response.raise_for_status()
        self.credentials = response.json()

    def sync(self, command):
        expires_at = datetime.fromisoformat(
            self.credentials["expiration"].replace("Z", "+00:00")
        )
        if expires_at <= datetime.now(timezone.utc) + timedelta(minutes=5):
            self.refresh()

        for attempt in range(2):
            result = subprocess.run(
                command,
                env={
                    **os.environ,
                    "AWS_ACCESS_KEY_ID": self.credentials["accessKeyId"],
                    "AWS_SECRET_ACCESS_KEY": self.credentials["secretAccessKey"],
                    "AWS_SESSION_TOKEN": self.credentials["sessionToken"],
                    "AWS_DEFAULT_REGION": "us-west-2",
                },
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode == 0:
                return

            error = result.stderr.strip()
            if attempt == 0 and (
                "expiredtoken" in error.lower() or "token has expired" in error.lower()
            ):
                self.refresh()
                continue
            raise RuntimeError(
                f"aws s3 sync failed (exit {result.returncode}): {error}"
            )


def cleanup(product_id, out_dir):
    prefix = product_id.replace("_CX_01", "")
    patterns = [
        f"{product_id}.ann",
        f"{product_id}.inc",
        f"{product_id}.inc.hdr",
        f"{prefix}*.grd",
        f"{prefix}*.grd.hdr",
    ]
    for pattern in patterns:
        for path in out_dir.glob(pattern):
            path.unlink(missing_ok=True)


def upload_tiffs(tiff_paths, destination):
    # The ASF credentials apply only to the download subprocess.
    for path in tiff_paths:
        result = subprocess.run(
            [
                "aws", "s3", "cp", str(path), f"{destination}/{path.name}",
                "--region", "us-west-2", "--only-show-errors",
            ],
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Upload failed for {path.name}: {result.stderr.strip()}")


def process_product(product_id, out_dir, s3_credentials, *, tiff_s3_uri=None):
    product_id = product_id.strip()
    prefix = product_id.replace("_CX_01", "")

    s3_prefix = (
        "s3://asf-cumulus-prod-products/"
        f"UAVSAR/UAVSAR_POLSAR/{product_id}"
    )

    download_start = perf_counter()
    s3_credentials.sync(
        [
            "aws", "s3", "sync", s3_prefix, str(out_dir),
            "--exclude", "*",
            "--include", "*.ann",
            "--include", "*HHHH*.grd",
            "--include", "*HVHV*.grd",
            "--include", "*VVVV*.grd",
            "--include", "*.inc",
            "--only-show-errors",
        ]
    )
    print(f"ASF sync: {perf_counter() - download_start:.1f}s")

    conversion_start = perf_counter()
    ann_path = out_dir / f"{product_id}.ann"
    if not ann_path.exists():
        raise FileNotFoundError(f"Missing annotation: {ann_path}")

    inc_path = out_dir / f"{product_id}.inc"
    if not inc_path.is_file():
        raise FileNotFoundError(f"Missing incidence-angle raster: {inc_path}")

    grd_files = []
    for pol in ("HHHH", "HVHV", "VVVV"):
        matches = sorted(out_dir.glob(f"{prefix}{pol}_*.grd"))
        if len(matches) != 1:
            raise FileNotFoundError(
                f"Expected one {pol} GRD, found {len(matches)}"
            )
        grd_files.append(matches[0])

    ann2envi_header(
        ann_path=ann_path,
        group="grd_pwr",
        output_dir=out_dir,
        save_json=True,
        overwrite=True,
    )

    ann2envi_header(
        ann_path=ann_path,
        group="inc",
        output_dir=out_dir,
        save_json=True,
        overwrite=True,
        infer_inc_from_grd=True,
    )

    tiff_paths = []
    for grd_path in grd_files:
        tiff_path = make_tiff(
            raster_path=grd_path,
            header_path=Path(str(grd_path) + ".hdr"),
            output_dir=out_dir,
            nodata=np.nan,
            invalid_min=0.0,
            clip_min=1e-4,
            overwrite=True,
            suffix="_cog",
            extension=".tif",
        )
        tiff_paths.append(tiff_path)

    inc_tiff, mask_tiff = make_inc_mask_tiffs(
        inc_path=inc_path,
        header_path=Path(str(inc_path) + ".hdr"),
        output_dir=out_dir,
        overwrite=tiff_s3_uri is not None,
    )
    print(f"GeoTIFF conversion: {perf_counter() - conversion_start:.1f}s")

    if tiff_s3_uri:
        tiff_paths.extend([inc_tiff, mask_tiff])
        destination = f"{tiff_s3_uri}/{product_id}"
        print(f"Uploading GeoTIFFs to {destination}/")
        upload_start = perf_counter()
        upload_tiffs(tiff_paths, destination)
        print(f"S3 upload: {perf_counter() - upload_start:.1f}s")
        for path in tiff_paths:
            path.unlink(missing_ok=True)

    cleanup(product_id, out_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Batch UAVSAR S3 download -> GeoTIFF."
    )
    parser.add_argument("product_list", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--log", type=Path, default=Path("uavsar_download_log.csv")
    )
    parser.add_argument(
        "--tiff-s3-uri", metavar="s3://BUCKET[/PREFIX]",
        help="Upload GeoTIFFs to a per-product S3 prefix, then delete local TIFFs and raw inputs.",
    )
    args = parser.parse_args()
    if args.tiff_s3_uri is not None:
        scheme, _, location = args.tiff_s3_uri.partition("://")
        if scheme != "s3" or not location.split("/", 1)[0]:
            parser.error("--tiff-s3-uri must be s3://BUCKET or s3://BUCKET/PREFIX")
        args.tiff_s3_uri = args.tiff_s3_uri.rstrip("/")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    product_ids = [
        line.strip()
        for line in args.product_list.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    s3_credentials = AsfS3Credentials()

    with args.log.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["product_id", "status", "message"])

        for product_id in product_ids:
            print(f"\n{product_id}")
            try:
                process_product(
                    product_id, args.output_dir, s3_credentials,
                    tiff_s3_uri=args.tiff_s3_uri,
                )
                writer.writerow([product_id, "SUCCESS", ""])
                print("SUCCESS")
            except Exception as exc:
                writer.writerow([product_id, "FAILED", str(exc)])
                print(f"FAILED: {exc}")
            f.flush()


if __name__ == "__main__":
    main()
