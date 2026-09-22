"""
Phase 7C: Planogram Format Parsers
==================================
This module ingests retailer planograms in various formats (JSON, CSV, XLS, XLSX)
and normalizes them into a single Canonical JSON format.

The downstream compliance engine only processes the Canonical Planogram,
making it completely agnostic to the original input format.

Usage:
    python Shelf_Reconstruction/phase7c_parsers.py
"""

import json
import pandas as pd
from pathlib import Path
import os

class PlanogramParser:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def parse(self, input_path: Path):
        ext = input_path.suffix.lower()
        
        if ext == '.json':
            canonical_data = self._parse_json(input_path)
        elif ext == '.csv':
            canonical_data = self._parse_csv(input_path)
        elif ext in ['.xls', '.xlsx']:
            canonical_data = self._parse_excel(input_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
            
        return self._save_canonical(canonical_data, input_path.stem)
        
    def _parse_json(self, filepath: Path) -> dict:
        """
        Validates basic structure to reject malformed JSON.
        """
        with open(filepath, 'r') as f:
            raw = json.load(f)
            
        required_keys = {"planogram_id", "version", "shelves"}
        if not required_keys.issubset(raw.keys()):
            missing = required_keys - set(raw.keys())
            raise ValueError(f"JSON missing required keys: {sorted(missing)}")
            
        return self._build_canonical(
            planogram_id=raw.get("planogram_id"),
            version=raw.get("version"),
            store_id=raw.get("store_id", "STORE_001"),
            shelves=raw.get("shelves", [])
        )
        
    def _parse_csv(self, filepath: Path) -> dict:
        df = pd.read_csv(filepath)
        return self._tabular_to_canonical(df)
        
    def _parse_excel(self, filepath: Path) -> dict:
        if filepath.suffix.lower() == '.xls':
            df = pd.read_excel(filepath, engine='xlrd')
        else:
            df = pd.read_excel(filepath, engine='openpyxl')
        return self._tabular_to_canonical(df)
        
    def _tabular_to_canonical(self, df: pd.DataFrame) -> dict:
        """
        Converts flat tabular data (planogram_id, version, store_id, shelf_id, position, sku_id)
        into the nested canonical schema.
        """
        if df.empty:
            return {}
            
        REQUIRED_COLUMNS = {
            "planogram_id",
            "version",
            "shelf_id",
            "position",
            "sku_id"
        }
        
        missing_columns = REQUIRED_COLUMNS - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {sorted(missing_columns)}")
            
        p_id = df["planogram_id"].iloc[0]
        version = df["version"].iloc[0]
        store_id = df.get("store_id", pd.Series(["STORE_001"] * len(df))).iloc[0] # Fallback if missing
        
        shelves_dict = {}
        for _, row in df.iterrows():
            sid = int(row["shelf_id"])
            if sid not in shelves_dict:
                shelves_dict[sid] = {"shelf_id": sid, "products": []}
                
            shelves_dict[sid]["products"].append({
                "position": int(row["position"]),
                "sku_id": str(row["sku_id"])
            })
            
        shelves_list = [shelves_dict[k] for k in sorted(shelves_dict.keys())]
        
        return self._build_canonical(p_id, version, store_id, shelves_list)

    def _build_canonical(self, planogram_id, version, store_id, shelves) -> dict:
        """Enforces the strict Canonical Schema"""
        return {
            "planogram_id": str(planogram_id),
            "version": int(version) if version else 1,
            "store_id": str(store_id),
            "shelves": shelves
        }

    def _save_canonical(self, data: dict, stem: str) -> Path:
        out_path = self.output_dir / f"{stem}_canonical.json"
        with open(out_path, 'w') as f:
            json.dump(data, f, indent=2)
        return out_path


if __name__ == "__main__":
    print("=" * 60)
    print(" PHASE 7C: RUNNING PLANOGRAM FORMAT PARSERS")
    print("=" * 60)
    
    BASE_DIR = Path(__file__).parent.parent
    IDEAL_DIR = BASE_DIR / "Dataset" / "ideal_planograms"
    CANONICAL_DIR = IDEAL_DIR / "canonical"
    
    parser = PlanogramParser(output_dir=CANONICAL_DIR)
    
    files_to_test = [
        IDEAL_DIR / "json" / "P001.json",
        IDEAL_DIR / "csv" / "P001.csv",
        IDEAL_DIR / "xls" / "P001.xls",
        IDEAL_DIR / "xlsx" / "P001.xlsx"
    ]
    
    for f in files_to_test:
        if f.exists():
            out_f = parser.parse(f)
            print(f"✅ Parsed {f.name:<15} -> {out_f.name}")
        else:
            print(f"❌ File not found: {f}")
            
    print("\n✅ Canonical parsing complete!")
