import os
import re
import argparse
import urllib3
from packaging import version
import shutil

def clean_downloads():
    """Clean the downloads directory"""
    if os.path.exists("downloads"):
        shutil.rmtree("downloads")
        print("Downloads directory cleaned.")

def get_latest_patch_version(version_prefix, available_versions):
    """Find the latest patch version for a given major.minor version"""
    matching_versions = [v for v in available_versions if v.startswith(version_prefix)]
    return max(matching_versions, key=version.parse, default=None)

# Argument parsing
parser = argparse.ArgumentParser(description="Download Python versions based on specified criteria.")
parser.add_argument("--version", type=str, help="Version filter or fixed versions (e.g., '>=3.9,<=3.12', '==3.9.10', '3.9.10,3.12.0')")
parser.add_argument("--clean", action="store_true", help="Clean downloads directory before downloading")
parser.add_argument("--extension", type=str, help="Filter by file extension (e.g., 'tar.xz', 'exe')")
args = parser.parse_args()

if args.clean:
    clean_downloads()

# Create downloads directory if it doesn't exist
os.makedirs("downloads", exist_ok=True)

http = urllib3.PoolManager()

resp = http.request("GET", "https://www.python.org/ftp/python")
versions = re.findall(r"href=\"([0-9][.0-9]*[0-9])/\"", resp.data.decode())

# Parse version argument
version_specifier = None
fixed_versions = set()
if args.version:
    if ',' in args.version:
        for v in args.version.split(','):
            v = v.strip()
            if any(op in v for op in ['<', '>', '=', '!']):
                version_specifier = version_specifier or version.SpecifierSet()
                version_specifier &= version.SpecifierSet(v)
            else:
                # Si c'est une version partielle (ex: "3.9"), on cherche la dernière version patch
                if v.count('.') == 1:
                    latest = get_latest_patch_version(v + '.', versions)
                    if latest:
                        fixed_versions.add(latest)
                else:
                    fixed_versions.add(v)
    else:
        if any(op in args.version for op in ['<', '>', '=', '!']):
            version_specifier = version.SpecifierSet(args.version)
        else:
            if args.version.count('.') == 1:
                latest = get_latest_patch_version(args.version + '.', versions)
                if latest:
                    fixed_versions.add(latest)
            else:
                fixed_versions.add(args.version)

for version_str in versions:
    split_version = tuple(map(int, version_str.split(".")))
    ver = version.parse(version_str)

    # Apply version filter if specified
    if version_specifier and not ver in version_specifier:
        continue

    # Apply fixed versions filter if specified
    if fixed_versions and version_str not in fixed_versions:
        continue

    if split_version < (3, 7, 14):
        continue
    print(f"Downloading {version_str}...")

    resp = http.request("GET", f"https://www.python.org/ftp/python/{version_str}")
    assert resp.status == 200
    data = resp.data.decode("utf-8")
    
    # Base pattern for Python files
    base_pattern = r"\"([pP]ython-.+\."
    
    if args.extension:
        # Si une extension est spécifiée, chercher cette extension et son .sigstore
        pattern = base_pattern + re.escape(args.extension) + r"(?:\.sigstore)?)\""
    else:
        # Pattern original si pas d'extension spécifiée
        pattern = r"\"([pP]ython-.+(?:\.tar\.xz|\.tgz|\.pkg|\.exe|\.zip)(?:\.sigstore)?)\""
    
    urls = re.findall(pattern, data)
    
    for url in urls:
        if os.path.isfile(f"downloads/{url}"):
            continue
        # wget is faster than Python
        os.system(
            f"wget https://www.python.org/ftp/python/{version_str}/{url} --verbose -P downloads/"
        )
