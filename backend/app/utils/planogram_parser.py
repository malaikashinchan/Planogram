"""
Planogram upload parser utility.
Converts JSON, CSV, XLS, and XLSX uploads into a standard Canonical structure.
"""

import json
from typing import BinaryIO
import pandas as pd
from fastapi import UploadFile


class PlanogramParser:
    @staticmethod
    def parse_upload(upload: UploadFile) -> dict:
        """
        Parses an uploaded file into the canonical dictionary format.
        """
        ext = upload.filename.split(".")[-1].lower() if upload.filename else ""
        
        # Determine format by extension or content type
        if ext == "json" or upload.content_type == "application/json":
            return PlanogramParser._parse_json(upload.file)
        elif ext == "csv" or upload.content_type == "text/csv":
            return PlanogramParser._parse_csv(upload.file)
        elif ext in ["xls", "xlsx"] or "spreadsheet" in upload.content_type or "excel" in upload.content_type:
            return PlanogramParser._parse_excel(upload.file, ext)
        else:
            raise ValueError(f"Unsupported file format: {ext or upload.content_type}")

    @staticmethod
    def _parse_json(file_obj: BinaryIO) -> dict:
        try:
            raw = json.load(file_obj)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format.")
            
        required_keys = {"planogram_id", "shelves"}
        if not required_keys.issubset(raw.keys()):
            missing = required_keys - set(raw.keys())
            raise ValueError(f"JSON missing required keys: {sorted(missing)}")
            
        return PlanogramParser._build_canonical(
            planogram_code=raw.get("planogram_id"), # In canonical it's called planogram_id, but it maps to code
            store_id=raw.get("store_id"),
            shelves=raw.get("shelves", [])
        )

    @staticmethod
    def _parse_csv(file_obj: BinaryIO) -> dict:
        try:
            df = pd.read_csv(file_obj)
            return PlanogramParser._tabular_to_canonical(df)
        except Exception as e:
            raise ValueError(f"Failed to parse CSV: {str(e)}")

    @staticmethod
    def _parse_excel(file_obj: BinaryIO, ext: str) -> dict:
        try:
            engine = 'xlrd' if ext == 'xls' else 'openpyxl'
            df = pd.read_excel(file_obj, engine=engine)
            return PlanogramParser._tabular_to_canonical(df)
        except Exception as e:
            raise ValueError(f"Failed to parse Excel: {str(e)}")

    @staticmethod
    def _tabular_to_canonical(df: pd.DataFrame) -> dict:
        if df.empty:
            raise ValueError("Uploaded file is empty.")
            
        REQUIRED_COLUMNS = {
            "planogram_id",
            "shelf_id",
            "position",
            "sku_id"
        }
        
        missing_columns = REQUIRED_COLUMNS - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {sorted(missing_columns)}")
            
        planogram_code = df["planogram_id"].iloc[0]
        store_id = df.get("store_id", pd.Series([None] * len(df))).iloc[0]
        
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
        return PlanogramParser._build_canonical(planogram_code, store_id, shelves_list)

    @staticmethod
    def _build_canonical(planogram_code: str, store_id: str | None, shelves: list) -> dict:
        return {
            "planogram_code": str(planogram_code),
            "store_id": str(store_id) if store_id else None,
            "shelves": shelves
        }
