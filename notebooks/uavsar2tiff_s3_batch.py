#!/usr/bin/env python3
import argparse
import csv
import os
import subprocess
from pathlib import Path

import numpy as np

from dansar.uavsar.ann2envi_header import ann2envi_header
from dansar.uavsar.make_tiff import make_tiff, make_inc_mask_tiffs
from dansar.utils.make_asf_session import make_asf_session


def setup_aws():
    _, creds = make_asf_session()
    os.environ["AWS_ACCESS_KEY_ID"] = creds["accessKeyId"]
    os.environ["AWS_SECRET_ACCESS_KEY"] = creds["secretAccessKey"]
    os.environ["AWS_SESSION_TOKEN"] = creds["sessionToken"]
    os.environ["AWS_DEFAULT_REGION"] = "us-west-2"


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


def process_product(product_id, out_dir):
    product_id = product_id.strip()
    prefix = product_id.replace("_CX_01", "")

    s3_prefix = (
        "s3://asf-cumulus-prod-products/"
        f"UAVSAR/UAVSAR_POLSAR/{product_id}"
    )

    subprocess.run(
        [
            "aws", "s3", "sync", s3_prefix, str(out_dir),
            "--exclude", "*",
            "--include", "*.ann",
            "--include", "*HHHH*.grd",
            "--include", "*HVHV*.grd",
            "--include", "*VVVV*.grd",
            "--include", "*.inc",
            "--only-show-errors",
        ],
        check=True,
    )

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

    for grd_path in grd_files:
        make_tiff(
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

    make_inc_mask_tiffs(
        inc_path=inc_path,
        header_path=Path(str(inc_path) + ".hdr"),
        output_dir=out_dir,
        overwrite=False,
    )

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
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    product_ids = [
        line.strip()
        for line in args.product_list.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    setup_aws()

    with args.log.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["product_id", "status", "message"])

        for product_id in product_ids:
            print(f"\n{product_id}")
            try:
                process_product(product_id, args.output_dir)
                writer.writerow([product_id, "SUCCESS", ""])
                print("SUCCESS")
            except Exception as exc:
                writer.writerow([product_id, "FAILED", str(exc)])
                print(f"FAILED: {exc}")
            f.flush()


if __name__ == "__main__":
    main()
