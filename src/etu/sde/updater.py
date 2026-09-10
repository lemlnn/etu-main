"""sde updater. it downloads into a temporary directory, extracts only what etu uses, then hands it to the importer"""

import json
import shutil
import tempfile
import zipfile
from pathlib import Path

import requests

from etu.sde.database import get_sde_build
from etu.sde.importer import import_sde


LATEST_SDE_URL = (
    "https://developers.eveonline.com/"
    "static-data/tranquility/latest.jsonl"
)

SDE_DOWNLOAD_URL = (
    "https://developers.eveonline.com/"
    "static-data/tranquility/"
    "eve-online-static-data-{build}-jsonl.zip"
)

REQUIRED_SDE_FILES = {
    "categories.jsonl",
    "groups.jsonl",
    "types.jsonl",
    "mapRegions.jsonl",
    "mapConstellations.jsonl",
    "mapSolarSystems.jsonl",
    "mapStargates.jsonl",
}


def get_latest_sde_build() -> int:
    response = requests.get(
        LATEST_SDE_URL,
        timeout=15,
    )

    response.raise_for_status()

    for line in response.text.splitlines():
        if not line.strip():
            continue

        record = json.loads(line)

        if record.get("_key") != "sde":
            continue

        if "buildNumber" in record:
            return int(record["buildNumber"])

        if "_value" in record:
            value = record["_value"]

            if isinstance(value, dict):
                return int(value["buildNumber"])

            return int(value)

    raise RuntimeError(
        "Could not find the SDE build number."
    )

def _download_sde(
    build: int,
    destination: Path,
):
    url = SDE_DOWNLOAD_URL.format(build=build)

    response = requests.get(
        url,
        stream=True,
        timeout=(10, 120),
    )

    response.raise_for_status()

    downloaded = 0

    with open(destination, "wb") as file:
        for chunk in response.iter_content(
            chunk_size=1024 * 1024
        ):
            if not chunk:
                continue

            file.write(chunk)

            downloaded += len(chunk)

            print(
                f"\rDownloaded: "
                f"{downloaded / 1024 / 1024:.1f} MiB",
                end="",
            )

    print()

def update_sde():
    print("Checking for SDE updates...")

    latest_build = get_latest_sde_build()
    installed_build = get_sde_build()

    print(
        f"Installed SDE: "
        f"{installed_build or 'unknown'}"
    )
    print(f"Latest SDE:    {latest_build}")

    if installed_build == latest_build:
        print("SDE is already up to date.")
        return

    # downloads stay temporary so a failed update does not leave random archives around the project
    with tempfile.TemporaryDirectory(
        prefix="etu-sde-"
    ) as temp:
        temp_dir = Path(temp)

        zip_path = temp_dir / "sde.zip"
        extracted_dir = temp_dir / "sde"

        print()
        print("Downloading SDE...")

        _download_sde(
            latest_build,
            zip_path,
        )

        print("Extracting required files...")

        _extract_required_files(
            zip_path,
            extracted_dir,
        )

        print("Importing SDE...")

        import_sde(
            sde_dir=extracted_dir,
            build=latest_build,
        )

    print(
        f"SDE updated to build "
        f"{latest_build}."
    )

def _extract_required_files(
    zip_path: Path,
    destination: Path,
):
    destination.mkdir(
        parents=True,
        exist_ok=True,
    )

    found = set()

    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            filename = Path(member.filename).name

            # the full sde has a lot etu does not use yet, so only the files the importer understands are extracted
            if filename not in REQUIRED_SDE_FILES:
                continue

            target = destination / filename

            with archive.open(member) as source:
                with open(target, "wb") as output:
                    shutil.copyfileobj(source, output)

            found.add(filename)

    missing = REQUIRED_SDE_FILES - found

    if missing:
        missing_text = ", ".join(sorted(missing))

        raise RuntimeError(
            f"SDE archive is missing: {missing_text}"
        )
