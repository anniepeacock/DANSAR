#!/usr/bin/env python3

import argparse
import subprocess
from pathlib import Path

import numpy as np

from dansar.uavsar.ann2envi_header import ann2envi_header
from dansar.uavsar.make_tiff import make_tiff


# ------------------------------------------------------------
# Hardcoded processing settings
# ------------------------------------------------------------

OVERWRITE = False
NODATA = np.nan
INVALID_MIN = 0.0
CLIP_MIN = 1e-4

POLARIZATIONS = ("HHHH", "HVHV", "VVVV")


def process_scene(ann_path: Path, input_dir: Path, output_dir: Path):
    """Process one UAVSAR GRD scene."""

    product_name = ann_path.stem
    product_prefix = product_name.replace("_CX_01", "")

    print()
    print("=" * 70)
    print(f"Processing: {product_name}")
    print("=" * 70)

    # --------------------------------------------------------
    # Find the three GRD power products
    # --------------------------------------------------------

    grd_files = []

    for polarization in POLARIZATIONS:
        matches = sorted(
            input_dir.glob(
                f"{product_prefix}{polarization}_*.grd"
            )
        )

        if len(matches) != 1:
            raise FileNotFoundError(
                f"Expected exactly one {polarization} GRD for "
                f"{product_name}, found {len(matches)}: {matches}"
            )

        grd_files.append(matches[0])

    # --------------------------------------------------------
    # Generate HDR + JSON files for all three polarizations
    # --------------------------------------------------------

    metadata_outputs = ann2envi_header(
        ann_path=ann_path,
        group="grd_pwr",
        output_dir=output_dir,
        save_json=True,
        overwrite=OVERWRITE,
    )

    for item in metadata_outputs:
        print(f"HDR ready:  {item['header_path'].name}")

        if item["json_path"] is not None:
            print(f"JSON ready: {item['json_path'].name}")

    # --------------------------------------------------------
    # Make COGs
    # --------------------------------------------------------

    cog_files = []

    for source_grd in grd_files:

        # ann2envi_header created these in output_dir
        hdr_path = output_dir / f"{source_grd.name}.hdr"
        json_path = output_dir / f"{source_grd.name}.json"

        if not hdr_path.exists():
            raise FileNotFoundError(
                f"Missing header: {hdr_path}"
            )

        if not json_path.exists():
            raise FileNotFoundError(
                f"Missing metadata JSON: {json_path}"
            )

        tif_path = (
            output_dir
            / f"{source_grd.stem}_cog.tif"
        )

        if tif_path.exists() and not OVERWRITE:
            print(f"TIFF exists: {tif_path.name}")
            cog_files.append(tif_path)
            continue

        print(f"Making TIFF: {tif_path.name}")

        written_tif = make_tiff(
            raster_path=source_grd,
            header_path=hdr_path,
            output_dir=output_dir,
            nodata=NODATA,
            invalid_min=INVALID_MIN,
            clip_min=CLIP_MIN,
            overwrite=True,
            suffix="_cog",
            extension=".tif",
            metadata_json_path=json_path,
        )

        print(f"TIFF ready: {written_tif.name}")

        cog_files.append(written_tif)

    # --------------------------------------------------------
    # Make 3-band VRT: HH, HV, VV
    # --------------------------------------------------------

    vrt_path = (
        output_dir
        / f"{product_name}_grd_pwr_stack.vrt"
    )

    if vrt_path.exists() and OVERWRITE:
        vrt_path.unlink()

    if vrt_path.exists():
        print(f"VRT exists: {vrt_path.name}")
    else:
        print(f"Making VRT: {vrt_path.name}")

        subprocess.run(
            [
                "gdalbuildvrt",
                "-separate",
                str(vrt_path),
                str(cog_files[0]),
                str(cog_files[1]),
                str(cog_files[2]),
            ],
            check=True,
        )

        print(f"VRT ready: {vrt_path.name}")


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Convert all UAVSAR GRD power products in a folder "
            "to Cloud Optimized GeoTIFFs and 3-band VRTs."
        )
    )

    parser.add_argument(
        "input_dir",
        type=Path,
        help="Folder containing UAVSAR .ann and .grd files.",
    )

    parser.add_argument(
        "output_dir",
        type=Path,
        help="Folder where COGs, metadata, and VRTs will be written.",
    )

    args = parser.parse_args()

    input_dir = args.input_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()

    if not input_dir.is_dir():
        raise NotADirectoryError(
            f"Input directory does not exist: {input_dir}"
        )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    ann_files = sorted(
        input_dir.glob("*.ann")
    )

    if not ann_files:
        raise FileNotFoundError(
            f"No .ann files found in {input_dir}"
        )

    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Scenes found: {len(ann_files)}")

    failures = []

    for ann_path in ann_files:
        try:
            process_scene(
                ann_path=ann_path,
                input_dir=input_dir,
                output_dir=output_dir,
            )

        except Exception as exc:
            print()
            print(f"ERROR processing {ann_path.name}:")
            print(f"  {exc}")

            failures.append(
                (ann_path.name, str(exc))
            )

    print()
    print("=" * 70)
    print("Processing complete.")
    print(
        f"Successful: {len(ann_files) - len(failures)}"
    )
    print(f"Failed:     {len(failures)}")

    if failures:
        print()
        print("Failures:")

        for scene, error in failures:
            print(f"  {scene}")
            print(f"    {error}")


if __name__ == "__main__":
    main()
