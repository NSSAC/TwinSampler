import pandas as pd
import numpy as np
import os

# County FIPS table, shipped inside the package.
_FIPS_CSV = "county_fips.csv"


def county_fips_path() -> str:
    """Absolute path to the bundled county FIPS table.

    Resolved through importlib.resources rather than by walking up from
    __file__. The old code did
        os.path.join(script_dir, "../../Data/county_fips.csv")
    which is the repo root in a checkout but `lib/pythonX.Y/Data/` once
    installed, because the package installs as site-packages/
    linelist_generation and the two `..` climb straight out of it. The table
    was never packaged either, so every non-editable install raised
    FileNotFoundError -- after loading the whole EpiHiper file.

    Public so a caller can check for the table before doing expensive work.
    """
    try:
        from importlib.resources import files

        cand = files("linelist_generation") / "data" / _FIPS_CSV
        if cand.is_file():
            return str(cand)
    except (ImportError, ModuleNotFoundError, TypeError, OSError):
        pass        # not importable as a package: running the files directly

    here = os.path.dirname(os.path.abspath(__file__))
    for rel in (("data", _FIPS_CSV),            # packaged location
                ("..", "..", "Data", _FIPS_CSV)):   # pre-move checkout
        cand = os.path.normpath(os.path.join(here, *rel))
        if os.path.isfile(cand):
            return cand

    raise FileNotFoundError(
        f"{_FIPS_CSV} not found. It ships inside the package at "
        f"linelist_generation/data/{_FIPS_CSV}; if this is an old checkout, "
        f"pull and reinstall TwinSampler.")


class DemographicsLoader:
    """
    A centralized loader for EpiHiper/synthetic population demographic files.
    Standardizes column names and categorical values for downstream tools.
    """
    
    # The Single Source of Truth for column mappings
    #
    # admin2 is deliberately NOT mapped here. The VA persontrait file already
    # has a `county` column holding names ("Accomack VA"), while the household
    # file has admin1..admin4. Renaming household.admin2 -> county made both
    # frames carry `county`, so the merge on hid produced county_x/county_y and
    # left no `county` at all -- which is why the county lookup in
    # process_epihiper has never worked on this input. county and county_fips
    # are now resolved explicitly there instead.
    COLUMN_MAPPINGS = {
        'home_latitude': 'latitude',
        'home_longitude': 'longitude',
        'gender': 'sex'
    }

    def __init__(self, filepath, use_pyarrow=True, skiprows=0, county_lookup=False):
        self.filepath = filepath
        self.df = self._load_and_standardize(use_pyarrow, skiprows)
        if county_lookup:
            fips_csv_path = county_fips_path()
            print(f"Loading FIPS mapping from {fips_csv_path}...")
            fips_mapping_df = pd.read_csv(fips_csv_path, dtype={'FIPS': str})
            self.fips_to_name_dict = dict(zip(fips_mapping_df['FIPS'], fips_mapping_df['county']))
        else:
            self.fips_to_name_dict = None

    @staticmethod
    def _header_on_first_line(filepath) -> bool:
        """True when line 1 is already the header, so nothing may be skipped.

        Callers pass skiprows=1 for files that open with a banner line. The VA
        persontrait file does not have one, and skipping its header is quietly
        destructive in two different ways depending on the engine: the C
        engine promotes the first data row to be the header, giving columns
        like ['361190001', '1', 'Accomake VA', ...]; pandas' pyarrow engine
        keeps the real header and drops the first *person* instead. The second
        is worse because nothing fails -- the run completes one record short.
        So detect rather than trust the flag.
        """
        import csv as _csv

        try:
            with open(filepath, "r", newline="") as fh:
                first = fh.readline()
        except (OSError, UnicodeDecodeError):
            return False
        if not first:
            return False
        fields = [f.strip().lower() for f in next(_csv.reader([first]), [])]
        # A header names identifiers; a data row carries their values.
        return bool({"pid", "hid", "admin1"} & set(fields))

    def _load_and_standardize(self, use_pyarrow, skiprows):
        """Loads the CSV and applies universal schema rules."""
        engine = "pyarrow" if use_pyarrow else "c"
        if skiprows and self._header_on_first_line(self.filepath):
            print(f"  (line 1 of {os.path.basename(self.filepath)} is already a "
                  f"header; ignoring skiprows={skiprows})")
            skiprows = 0
        try:
            df = pd.read_csv(self.filepath, engine=engine, skiprows=skiprows)
        except (ImportError, ValueError):
            print("Warning: pyarrow engine failed or not installed, falling back to default C engine.")
            df = pd.read_csv(self.filepath, skiprows=skiprows)

        # 1. Standardize Column Names (This fixes the 'county' missing issue!)
        df.rename(columns=self.COLUMN_MAPPINGS, inplace=True)

        # 2. Standardize Sex/Gender values (1 -> male, 2 -> female)
        if 'sex' in df.columns:
            # Safely map 1/2 to strings, leaving existing strings or NaNs alone
            sex_map = {1: 'male', 2: 'female', '1': 'male', '2': 'female'}
            df['sex'] = df['sex'].map(sex_map).fillna(df['sex'])

        # 3. Set Index for fast row-by-row lookups
        if 'pid' in df.columns:
            df['pid'] = df['pid'].astype(str) # Ensure pid is string for consistent indexing
            df.set_index('pid', inplace=True)

        # 4. Standardize smh_race
        if 'smh_race' in df.columns:
            smh_race_map = {'W': 'White', 'B': 'Black', 'A': 'Asian', 'L': 'Latino', 'O': 'Other'}
            df['smh_race'] = df['smh_race'].map(smh_race_map).fillna(df['smh_race'])

        # 5. Standardize hispanic to latino boolean
        if 'hispanic' in df.columns:
            df['latino'] = df['hispanic'].apply(lambda x: True if x in [2, '2'] else False)

        return df

    def get_dataframe(self):
        """
        Returns the fully standardized Pandas DataFrame.
        Best for vectorized operations (e.g., simulate_linelist.py).
        """
        return self.df

    def get_person_dict(self, pid, required_columns):
        """
        Returns a dictionary of traits for a single person, formatted as strings.
        Fills missing values with "NA".
        Best for row-by-row processing (e.g., genetic_painter.py).
        """
        res = {}
        
        try:
            # Fast index lookup
            person_series = self.df.loc[pid]
            person_exists = True
        except KeyError:
            person_series = None
            person_exists = False

        for col in required_columns:
            if col == 'pid':
                res[col] = str(pid)
            elif person_exists and col in person_series.index:
                val = person_series[col]
                res[col] = str(val) if not pd.isna(val) else "NA"
            else:
                res[col] = "NA"
                
        return res
