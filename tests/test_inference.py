import asyncio
from pathlib import Path
from backend.app.ml.reconstruction import ShelfReconstructor
from backend.app.core.config import settings

async def main():
    reconstructor = ShelfReconstructor(
        yolo_model_path=settings.YOLO_MODEL_PATH,
        resnet_model_path=settings.RESNET_MODEL_PATH,
        ref_embeddings_path=settings.REFERENCE_EMBEDDINGS_PATH,
        ref_labels_path=settings.REFERENCE_LABELS_PATH,
        eps_ratio=settings.YOLO_CLUSTER_EPS_RATIO
    )
    
    # Test P01 image
    img_path = "./Dataset/GroceryDataset_part1/ShelfImages/C1_P01_N1_S3_1.JPG"
    print(f"Running inference on {img_path}...")
    shelf_data = reconstructor.reconstruct_shelf(img_path)
    print("Detected for P01 image:")
    for shelf in shelf_data:
        print(f"Shelf {shelf['shelf_id']}:")
        for p in shelf['products']:
            print(f"  Pos {p['position']}: {p['sku_id']}")

if __name__ == "__main__":
    asyncio.run(main())
