"""
Planogram validator utility.
Ensures the parsed canonical format meets business logic requirements
before database insertion.
"""

from typing import Any
import uuid

class PlanogramValidator:
    @staticmethod
    def validate_canonical(canonical_data: dict[str, Any]) -> None:
        """
        Validates the structure and data types of the canonical planogram.
        Raises ValueError if validation fails.
        """
        code = canonical_data.get("planogram_code")
        if not code or not isinstance(code, str):
            raise ValueError("Invalid or missing 'planogram_id' (mapped to planogram_code).")
            
        shelves = canonical_data.get("shelves")
        if not shelves or not isinstance(shelves, list):
            raise ValueError("Planogram must contain a non-empty 'shelves' list.")
            
        shelf_ids = set()
        for shelf in shelves:
            sid = shelf.get("shelf_id")
            if not isinstance(sid, int) or sid <= 0:
                raise ValueError(f"Invalid shelf_id: {sid}. Must be a positive integer.")
            if sid in shelf_ids:
                raise ValueError(f"Duplicate shelf_id found: {sid}")
            shelf_ids.add(sid)
            
            products = shelf.get("products")
            if not isinstance(products, list):
                raise ValueError(f"Shelf {sid} must contain a 'products' list.")
                
            positions = set()
            for p in products:
                pos = p.get("position")
                sku = p.get("sku_id")
                
                if not isinstance(pos, int) or pos <= 0:
                    raise ValueError(f"Invalid position {pos} on shelf {sid}.")
                if pos in positions:
                    raise ValueError(f"Duplicate position {pos} on shelf {sid}.")
                positions.add(pos)
                
                if not sku or not isinstance(sku, str):
                    raise ValueError(f"Invalid sku_id at position {pos} on shelf {sid}.")
