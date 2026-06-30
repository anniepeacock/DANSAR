import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse


def filename_from_url(url):
    """
    Infer a local filename from a URL.
    """

    if not isinstance(url, str):
        raise TypeError(f"url must be a string, not {type(url).__name__}")

    url = url.strip()

    if not url:
        raise ValueError("url is empty or contains only whitespace.")

    parsed = urlparse(url)
    filename = Path(parsed.path).name

    if not filename:
        raise ValueError(f"Could not infer filename from URL: {url}")

    return filename


def extract_urls(urls):
    """
    Normalize URL input into a list of URL strings.

    Accepted inputs
    ---------------
    str
        A single URL.

    list[str]
        A list of URLs.

    dict
        A dictionary containing URL values. Only keys ending in '_url'
        are used. This matches the output of infer_uavsar_paths().
    """

    if isinstance(urls, str):
        url_list = [urls]

    elif isinstance(urls, list):
        url_list = urls

    elif isinstance(urls, dict):
        url_list = [
            value
            for key, value in urls.items()
            if key.endswith("_url")
        ]

    else:
        raise TypeError(
            "urls must be a string, a list of strings, or a dictionary "
            "containing URL values."
        )

    if not url_list:
        raise ValueError("No URLs were found.")

    for url in url_list:
        if not isinstance(url, str):
            raise TypeError(
                f"All URLs must be strings. Found {type(url).__name__}."
            )

        if not url.strip():
            raise ValueError("One of the URLs is empty or whitespace only.")

    return url_list


def load_urls_from_json(json_path):
    """
    Load URLs from a JSON file.

    The JSON may contain either:

        - a list of URLs
        - a dictionary with keys ending in '_url'
    """

    json_path = Path(json_path)

    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")

    if not json_path.is_file():
        raise ValueError(f"JSON path is not a file: {json_path}")

    try:
        with open(json_path, "r") as src:
            data = json.load(src)

    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON file: {json_path}") from exc

    return data


def download_uavsar_file(
    url,
    output_path,
    session,
    chunk_size=1024 * 1024,
    overwrite=False,
):
    """
    Download one UAVSAR file using an authenticated ASF/Earthdata session.

    Works for both text and binary UAVSAR files, including:

        .ann
        .grd
        .inc
        .hgt
        .slope

    Parameters
    ----------
    url : str
        UAVSAR file URL.

    output_path : str or pathlib.Path
        Local path where the file should be saved.

    session : requests.Session-like object
        Authenticated ASF session.

    chunk_size : int, optional
        Download chunk size in bytes. Default is 1 MB.

    overwrite : bool, optional
        If True, overwrite an existing output file.

    Returns
    -------
    pathlib.Path
        Path to the downloaded file.
    """

    if not isinstance(url, str):
        raise TypeError(f"url must be a string, not {type(url).__name__}")

    url = url.strip()

    if not url:
        raise ValueError("url is empty or contains only whitespace.")

    if session is None:
        raise ValueError("session cannot be None.")

    if not hasattr(session, "get"):
        raise TypeError(
            "session must be a requests-like object with a .get() method."
        )

    if not isinstance(chunk_size, int):
        raise TypeError(
            f"chunk_size must be an integer, not {type(chunk_size).__name__}"
        )

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    output_path = Path(output_path)

    if output_path.exists() and not overwrite:
        raise FileExistsError(
            f"Output file already exists: {output_path}. "
            "Use overwrite=True or pass --overwrite from the terminal."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with session.get(url, stream=True, allow_redirects=True) as response:
            response.raise_for_status()

            final_url = response.url
            content_type = response.headers.get("Content-Type", "").lower()

            if "text/html" in content_type:
                raise RuntimeError(
                    "Got HTML instead of a UAVSAR data file. "
                    "Authentication may have failed, the file may not exist, "
                    "or the URL redirected to a login page. "
                    f"Final URL was: {final_url}"
                )

            bytes_written = 0

            with open(output_path, "wb") as dst:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        dst.write(chunk)
                        bytes_written += len(chunk)

            if bytes_written == 0:
                raise RuntimeError(
                    f"Downloaded zero bytes from: {url}. "
                    f"Final URL was: {final_url}"
                )

    except Exception:
        if output_path.exists() and output_path.stat().st_size == 0:
            output_path.unlink()

        raise

    return output_path


def download_uavsar(
    urls,
    output_dir,
    session,
    chunk_size=1024 * 1024,
    overwrite=False,
):
    """
    Download one or more UAVSAR files from URLs.

    Parameters
    ----------
    urls : str, list[str], or dict
        URL input.

        Accepted forms:

            "https://.../file.ann"

            [
                "https://.../file.ann",
                "https://.../file.grd"
            ]

            {
                "annotation_url": "https://.../file.ann",
                "grd_hhhh_url": "https://.../file.grd"
            }

        If a dictionary is provided, only values whose keys end in '_url'
        are downloaded.

    output_dir : str or pathlib.Path
        Local output directory.

    session : requests.Session-like object
        Authenticated ASF session.

    chunk_size : int, optional
        Download chunk size in bytes. Default is 1 MB.

    overwrite : bool, optional
        If True, overwrite existing files.

    Returns
    -------
    list[pathlib.Path]
        Paths to downloaded files.
    """

    url_list = extract_urls(urls)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    downloaded_paths = []

    for url in url_list:
        filename = filename_from_url(url)
        output_path = output_dir / filename

        downloaded_path = download_uavsar_file(
            url=url,
            output_path=output_path,
            session=session,
            chunk_size=chunk_size,
            overwrite=overwrite,
        )

        downloaded_paths.append(downloaded_path)

    return downloaded_paths


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Download UAVSAR files from one or more URLs using an authenticated "
            "ASF/Earthdata session. This script does not infer URLs."
        )
    )

    input_group = parser.add_mutually_exclusive_group(required=True)

    input_group.add_argument(
        "-url",
        "--url",
        action="append",
        help=(
            "UAVSAR file URL to download. "
            "Can be passed multiple times."
        ),
    )

    input_group.add_argument(
        "-urls_json",
        "--urls-json",
        help=(
            "Path to a JSON file containing either a list of URLs or a "
            "dictionary with keys ending in '_url', such as the output of "
            "infer_uavsar_paths.py."
        ),
    )

    parser.add_argument(
        "-output_dir",
        "--output-dir",
        required=True,
        help="Directory where downloaded files will be saved.",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite files if they already exist.",
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1024 * 1024,
        help="Download chunk size in bytes. Default: 1048576.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print files that would be downloaded, but do not download.",
    )

    args = parser.parse_args()

    try:
        if args.urls_json:
            urls = load_urls_from_json(args.urls_json)
        else:
            urls = args.url

        url_list = extract_urls(urls)

        print("Selected UAVSAR URLs:")

        for url in url_list:
            output_path = Path(args.output_dir) / filename_from_url(url)
            print(f"  - {url}")
            print(f"    -> {output_path}")

        if args.dry_run:
            print("\nDry run complete. No files downloaded.")
            return 0

        try:
            from make_asf_session import make_asf_session
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "Could not import make_asf_session. "
                "Make sure make_asf_session.py is in the same folder as "
                "download_uavsar.py."
            ) from exc

        session = make_asf_session()

        downloaded_paths = download_uavsar(
            urls=url_list,
            output_dir=args.output_dir,
            session=session,
            chunk_size=args.chunk_size,
            overwrite=args.overwrite,
        )

        print("\nDownloaded files:")

        for path in downloaded_paths:
            print(f"  - {path}")

        return 0

    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())