import asf_search as asf
from pathlib import PurePosixPath


def infer_uavsar_paths(product_name):
    """
    Find the S3 locations of UAVSAR files using ASF Search.

    Parameters
    ----------
    product_name : str
        UAVSAR scene/product ID, e.g.
        PanCan_20012_26007_004_260505_L090_CX_01

    Returns
    -------
    dict
        S3 URIs for the UAVSAR files needed by the processing workflow.
    """

    results = asf.search(
        granule_list=[product_name],
        platform=asf.PLATFORM.UAVSAR,
    )

    if not results:
        raise ValueError(f"No ASF product found for {product_name}")

    product = results[0]

    s3_urls = product.properties.get("s3Urls", [])

    if not s3_urls:
        raise ValueError(
            f"ASF returned no S3 URLs for {product_name}"
        )

    # Ignore browse bucket, etc.
    product_urls = [
        url for url in s3_urls
        if url.startswith("s3://asf-cumulus-prod-products/")
    ]

    def find_one(predicate):
        matches = [
            url for url in product_urls
            if predicate(PurePosixPath(url).name)
        ]

        if len(matches) != 1:
            raise ValueError(
                f"Expected exactly one match, found {len(matches)}:\n"
                + "\n".join(matches)
            )

        return matches[0]

    return {
        "annotation": find_one(
            lambda name: name.endswith(".ann")
        ),

        "grd_hhhh": find_one(
            lambda name:
                name.endswith(".grd")
                and "HHHH" in name
        ),

        "grd_hvhv": find_one(
            lambda name:
                name.endswith(".grd")
                and "HVHV" in name
        ),

        "grd_vvvv": find_one(
            lambda name:
                name.endswith(".grd")
                and "VVVV" in name
        ),

        "inc": find_one(
            lambda name: name.endswith(".inc")
        ),

        "hgt": find_one(
            lambda name: name.endswith(".hgt")
        ),

        "slope": find_one(
            lambda name: name.endswith(".slope")
        ),
    }
