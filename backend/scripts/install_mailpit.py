import hashlib
import io
import platform
import shutil
import tarfile
import tempfile
from pathlib import Path
from urllib.request import urlopen

VERSION = "v1.31.5"
CHECKSUMS = {
    "linux-amd64": "5924ace84f38c83c29f941a644a2d7be6c11f339eb4a9a12ab526414897ceed1",
    "linux-arm64": "ff9b03dd4a01e9680d89837d391296942c0529d545d160a98ed62882eec0e628",
    "darwin-amd64": "81dfda3824ec47cfa6dd7be6d70959bb588660c95633142cbd1f7aed62d98292",
    "darwin-arm64": "ddb042e3a9b1f36dadb20ec4d7424c417903adef692e59f50dce0075a747e8e2",
}


def main() -> None:
    architecture = {"x86_64": "amd64", "aarch64": "arm64", "arm64": "arm64"}.get(
        platform.machine().lower()
    )
    target = f"{platform.system().lower()}-{architecture}"
    if target not in CHECKSUMS:
        raise SystemExit(f"Unsupported Mailpit platform: {target}")
    destination = Path(__file__).resolve().parents[1] / ".tools" / "mailpit" / VERSION
    binary = destination / "mailpit"
    if binary.is_file():
        return
    url = (
        f"https://github.com/axllent/mailpit/releases/download/{VERSION}/"
        f"mailpit-{target}.tar.gz"
    )
    with urlopen(url, timeout=60) as response:
        archive = response.read()
    if hashlib.sha256(archive).hexdigest() != CHECKSUMS[target]:
        raise SystemExit("Mailpit checksum verification failed.")
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination) as temporary:
        extracted = Path(temporary) / "mailpit"
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
            source = bundle.extractfile("mailpit")
            if source is None:
                raise SystemExit("Mailpit binary is missing from the archive.")
            with source, extracted.open("wb") as output:
                shutil.copyfileobj(source, output)
        extracted.chmod(0o755)
        extracted.replace(binary)
    print(f"Installed Mailpit {VERSION}.")


if __name__ == "__main__":
    main()
