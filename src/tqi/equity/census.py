"""Download and parse Statistics Canada census data at DA level."""

import io
import zipfile
from pathlib import Path

import pandas as pd
import requests

from tqi.config import CENSUS_DIR

# 2021 Census profile — DA level for BC
# This URL points to the Census Profile CSV for Dissemination Areas in BC
CENSUS_PROFILE_URL = (
    "https://www12.statcan.gc.ca/census-recensement/2021/dp-pd/prof/details/"
    "download-telecharger/comp/GetFile.cfm?Lang=E&FILETYPE=CSV&GEONO=059_BC"
)

# DA boundary file (cartographic) — all of Canada
DA_BOUNDARY_URL = (
    "https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/"
    "files-fichiers/lda_000b21a_e.zip"
)

# Census characteristics of interest (by name patterns for robustness)
CHARACTERISTICS = {
    "median_income": "Median total income of household in 2020 ($)",
    "median_after_tax_income": "Median after-tax income of household in 2020 ($)",
    "population": "Population, 2021",
    "low_income_pct": "Prevalence of low income based on the Low-income measure, after tax (LIM-AT) (%)",
}


def download_da_boundaries(dest_dir: Path = CENSUS_DIR) -> Path:
    """Download and extract DA boundary shapefile. Returns shapefile path."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    shp_dir = dest_dir / "da_boundaries"

    # Check if already downloaded
    shp_files = list(shp_dir.glob("*.shp")) if shp_dir.exists() else []
    if shp_files:
        print(f"DA boundaries already downloaded: {shp_files[0]}")
        return shp_files[0]

    print(f"Downloading DA boundary file (~150MB) ...")
    resp = requests.get(DA_BOUNDARY_URL, timeout=300)
    resp.raise_for_status()

    shp_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        zf.extractall(shp_dir)

    shp_files = list(shp_dir.glob("*.shp"))
    if not shp_files:
        raise FileNotFoundError("No .shp file found in boundary download")

    print(f"Boundaries extracted: {shp_files[0]}")
    return shp_files[0]


def download_census_profile(dest_dir: Path = CENSUS_DIR) -> Path:
    """Download census profile CSV for BC DAs. Returns CSV path."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    csv_path = dest_dir / "census_profile_bc_da.csv"

    if csv_path.exists():
        print(f"Census profile already downloaded: {csv_path}")
        return csv_path

    print("Downloading census profile for BC DAs ...")
    resp = requests.get(CENSUS_PROFILE_URL, timeout=300)
    resp.raise_for_status()

    # The download may be a zip or CSV directly
    if resp.content[:2] == b"PK":  # zip magic number
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
            if csv_names:
                with zf.open(csv_names[0]) as f:
                    csv_path.write_bytes(f.read())
    else:
        csv_path.write_bytes(resp.content)

    print(f"Census profile saved: {csv_path}")
    return csv_path


def parse_census_profile(csv_path: Path) -> pd.DataFrame:
    """Parse StatsCan census profile CSV to a wide-format DataFrame.

    Returns DataFrame indexed by DGUID with columns for each characteristic.
    """
    # StatsCan CSVs use various encodings
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            df = pd.read_csv(csv_path, dtype=str, encoding=encoding, low_memory=False)
            break
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    else:
        raise ValueError(f"Could not read {csv_path} with any supported encoding")

    # Identify key columns (names vary between releases)
    dguid_col = next((c for c in df.columns if "DGUID" in c.upper()), None)
    char_col = next(
        (c for c in df.columns if "CHARACTERISTIC" in c.upper() and "NAME" in c.upper()),
        None,
    )
    value_col = next(
        (c for c in df.columns if c.strip().upper() in ("C1_COUNT_TOTAL", "T_DATA_DONNEES")),
        None,
    )

    if not all([dguid_col, char_col, value_col]):
        # Fall back to positional identification
        print(f"Warning: Could not identify census columns by name. Columns: {list(df.columns[:10])}")
        return pd.DataFrame()

    # Filter to DA-level geographies (DGUID format: 2021A0005XXXXXXXX for DAs)
    da_mask = df[dguid_col].str.contains("A0005", na=False)
    df = df[da_mask]

    # Build wide-format table
    records = {}
    for char_key, char_pattern in CHARACTERISTICS.items():
        char_mask = df[char_col].str.contains(char_pattern[:30], case=False, na=False)
        subset = df[char_mask][[dguid_col, value_col]].copy()
        subset[value_col] = pd.to_numeric(subset[value_col].str.replace(",", ""), errors="coerce")
        for _, row in subset.iterrows():
            dguid = row[dguid_col]
            if dguid not in records:
                records[dguid] = {}
            records[dguid][char_key] = row[value_col]

    result = pd.DataFrame.from_dict(records, orient="index")
    result.index.name = "DGUID"
    return result
