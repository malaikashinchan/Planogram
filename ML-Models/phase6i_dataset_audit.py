import json
import pandas as pd
from pathlib import Path

base_dir = Path('/Users/as-mac-1311/Downloads/Planogram/Dataset')

print('=== Products-10K ===')
p10k_test = base_dir / 'product_10k/test.csv'
if p10k_test.exists():
    df = pd.read_csv(p10k_test)
    print(f'test.csv rows: {len(df)}')
    print(f'Unique classes in test: {df["class"].nunique()}')
    print('Head:')
    print(df.head())
else:
    print('test.csv not found')

p10k_train_csv = base_dir / 'product_10k/train.csv'
if p10k_train_csv.exists():
    df = pd.read_csv(p10k_train_csv)
    print(f'\ntrain.csv rows: {len(df)}')
    print(f'Unique classes in train: {df["class"].nunique()}')
    print('Head:')
    print(df.head())
else:
    print('\ntrain.csv not found')

print('\n=== RPC ===')
rpc_train = base_dir / 'RPC/retail_product_checkout/instances_train2019.json'
if rpc_train.exists():
    with open(rpc_train, 'r') as f:
        data = json.load(f)
    print(f'instances_train2019.json keys: {data.keys()}')
    if 'categories' in data:
        print(f'Number of categories: {len(data["categories"])}')
        print(f'Sample category: {data["categories"][0]}')
    if 'images' in data:
        print(f'Number of images: {len(data["images"])}')
    if 'annotations' in data:
        print(f'Number of annotations: {len(data["annotations"])}')
        print(f'Sample annotation keys: {list(data["annotations"][0].keys())}')
        print(f'Sample annotation: {data["annotations"][0]}')
else:
    print('instances_train2019.json not found')
