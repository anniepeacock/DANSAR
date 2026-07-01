import argparse
import json


def infer_uavsar_paths(base_url, product_name):
    """
    Infer UAVSAR ASF URLs from a base URL and UAVSAR product name.

    Parameters
    ----------
    base_url : str
        Base UAVSAR ASF URL.

        Example:
            https://uavsar.asf.alaska.edu/

    product_name : str
        UAVSAR product base name from the annotation file.

        Example:
            PCanal_13503_26008_020_260506_L090_CX_01

    Returns
    -------
    dict
        Dictionary containing inferred URLs for:

            - annotation
            - grd_hhhh
            - grd_hvhv
            - grd_vvvv
            - inc
            - hgt
            - slope
    """

    if not isinstance(base_url, str):
        raise TypeError(f"base_url must be a string, not {type(base_url).__name__}")

    if not isinstance(product_name, str):
        raise TypeError(
            f"product_name must be a string, not {type(product_name).__name__}"
        )

    base_url = base_url.strip()
    product_name = product_name.strip()

    if not base_url:
        raise ValueError("base_url is empty or contains only whitespace.")

    if not product_name:
        raise ValueError("product_name is empty or contains only whitespace.")

    parts = product_name.split("_")

    if len(parts) < 8:
        raise ValueError(
            "Unexpected UAVSAR product name format. Expected something like: "
            "PCanal_13503_26008_020_260506_L090_CX_01"
        )

    base_lband = parts[5]

    if not base_lband.startswith("L"):
        raise ValueError(
            f"Could not find L-band token in product name: {base_lband}"
        )

    product_dir_name = f"UA_{product_name}"
    product_dir_url = f"{base_url.rstrip('/')}/{product_dir_name}"

    def make_grd_filename(polarization):
        grd_parts = parts.copy()
        grd_parts[5] = f"{base_lband}{polarization}"
        return f"{'_'.join(grd_parts)}.grd"

    annotation_filename = f"{product_name}.ann"
    grd_hhhh_filename = make_grd_filename("HHHH")
    grd_hvhv_filename = make_grd_filename("HVHV")
    grd_vvvv_filename = make_grd_filename("VVVV")
    inc_filename = f"{product_name}.inc"
    hgt_filename = f"{product_name}.hgt"
    slope_filename = f"{product_name}.slope"

    return {
        "product_name": product_name,
        "product_dir_name": product_dir_name,
        "product_dir_url": product_dir_url,

        "annotation_filename": annotation_filename,
        "annotation_url": f"{product_dir_url}/{annotation_filename}",

        "grd_hhhh_filename": grd_hhhh_filename,
        "grd_hhhh_url": f"{product_dir_url}/{grd_hhhh_filename}",

        "grd_hvhv_filename": grd_hvhv_filename,
        "grd_hvhv_url": f"{product_dir_url}/{grd_hvhv_filename}",

        "grd_vvvv_filename": grd_vvvv_filename,
        "grd_vvvv_url": f"{product_dir_url}/{grd_vvvv_filename}",

        "inc_filename": inc_filename,
        "inc_url": f"{product_dir_url}/{inc_filename}",

        "hgt_filename": hgt_filename,
        "hgt_url": f"{product_dir_url}/{hgt_filename}",

        "slope_filename": slope_filename,
        "slope_url": f"{product_dir_url}/{slope_filename}",
    }


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Infer UAVSAR ASF file URLs from a product name and base URL. "
            "This does not download or save files."
        )
    )

    parser.add_argument(
        "-product",
        "--product",
        required=True,
        help=(
            "UAVSAR product name from the annotation file. Example: "
            "PCanal_13503_26008_020_260506_L090_CX_01"
        ),
    )

    parser.add_argument(
        "-base_url",
        "--base-url",
        default="https://uavsar.asf.alaska.edu/",
        help=(
            "Base UAVSAR ASF URL. Default: "
            "https://uavsar.asf.alaska.edu/"
        ),
    )

    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation level. Default: 2.",
    )

    args = parser.parse_args()

    paths = infer_uavsar_paths(
        base_url=args.base_url,
        product_name=args.product,
    )

    print(json.dumps(paths, indent=args.indent))


if __name__ == "__main__":
    main()