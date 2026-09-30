import os
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

def chunk_markdown_file(filepath: str):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    md_header_splits = markdown_splitter.split_text(content)
    
    # Further chunk large sections if needed
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=100
    )
    splits = text_splitter.split_documents(md_header_splits)
    
    filename = os.path.basename(filepath)
    
    chunks = []
    for split in splits:
        section = " > ".join(split.metadata.values()) if split.metadata else "General"
        chunks.append({
            "file": filename,
            "section": section,
            "text": split.page_content
        })
        
    return chunks
