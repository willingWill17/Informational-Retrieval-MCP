import os
import json
import re
import io
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from tools.mining_data import mine_text
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTRect

# Try to import multiple PDF extraction libraries
extraction_methods = []

try:
    import fitz  # PyMuPDF - better for slides
    extraction_methods.append("pymupdf")
except ImportError:
    pass

try:
    from pdfminer.high_level import extract_text
    extraction_methods.append("pdfminer")
except ImportError:
    pass

try:
    import pytesseract
    from PIL import Image
    import fitz  # Also needed for OCR method
    extraction_methods.append("ocr")
except ImportError:
    pass

print(f"Available extraction methods: {extraction_methods}")

# Create an MCP server
mcp = FastMCP(
    name="Knowledge Base",
    host="0.0.0.0",
    port=8050,
)

def calculate_relevance_score(page_text: str, query_keywords: list[str]) -> int:
    """Calculates a relevance score based on the number of unique keyword matches."""
    score = 0
    page_text_lower = page_text.lower()
    # Using a set for query_keywords ensures we count each keyword only once
    for keyword in set(query_keywords):
        if keyword in page_text_lower:
            score += 1
    return score

def extract_relevant_excerpts(text: str, keywords: list, excerpt_length: int = 200) -> list:
    """Extract relevant excerpts from text based on keywords."""
    excerpts = []
    text_lower = text.lower()
    
    for keyword in keywords:
        keyword_lower = keyword.lower()
        start_pos = 0
        
        while True:
            pos = text_lower.find(keyword_lower, start_pos)
            if pos == -1:
                break
            
            start_excerpt = max(0, pos - excerpt_length // 2)
            end_excerpt = min(len(text), pos + len(keyword) + excerpt_length // 2)
            
            excerpt = text[start_excerpt:end_excerpt].strip()
            
            # Highlight the keyword
            excerpt = re.sub(
                re.escape(keyword), 
                f"**{keyword}**", 
                excerpt, 
                flags=re.IGNORECASE
            )
            
            if excerpt not in excerpts:
                excerpts.append(excerpt)
            
            start_pos = pos + 1
    
    return excerpts

@mcp.tool()
def get_knowledge_base(query: str = ""):
    """Retrieve relevant knowledge from PDF files based on query keywords."""
    try:
        notes_folder = Path("study_notes")
        output_folder = Path("mcp_images")
        output_folder.mkdir(exist_ok=True)
        
        if not notes_folder.exists():
            return "Error: Study notes folder not found"
        
        query_keywords = [keyword.lower().strip() for keyword in query.split()] if query else []
        if not query_keywords:
            return "Please provide a query to search the knowledge base."
            
        print(f"Query keywords: {query_keywords}")
        
        relevant_pages = []
        RELEVANCE_THRESHOLD = 1  # Consider pages with at least one keyword match
        
        for note_file in notes_folder.iterdir():
            if note_file.is_file() and note_file.suffix == ".pdf":
                for page_num, page_layout in enumerate(extract_pages(note_file), 1):
                    page_text = mine_text(page_layout)
                    if page_text:
                        score = calculate_relevance_score(page_text, query_keywords)
                        if score >= RELEVANCE_THRESHOLD:
                            relevant_pages.append((score, note_file.name, page_num))
        
        if not relevant_pages:
            return "No relevant information found for your query."
            
        # Sort pages by relevance score in descending order
        relevant_pages.sort(key=lambda x: x[0], reverse=True)
        
        # Convert the top 5 most relevant pages to PNG images
        output_image_paths = []
        for score, file_name, page_num in relevant_pages[:5]:
            pdf_path = notes_folder / file_name
            output_image_name = f"{Path(file_name).stem}_page_{page_num}.png"
            output_image_path = output_folder / output_image_name

            try:
                doc = fitz.open(pdf_path)
                page = doc.load_page(page_num - 1)  # page_num is 1-based, load_page is 0-based
                pix = page.get_pixmap(dpi=150)  # Adjust DPI for quality
                pix.save(str(output_image_path))
                doc.close()
                output_image_paths.append({
                    "path": str(output_image_path),
                    "source": file_name,
                    "page": page_num,
                    "score": score
                })
                print(output_image_paths)
            except Exception as e:
                print(f"Could not convert page {page_num} of {file_name} to image. Error: {e}")

        return json.dumps({"relevant_images": output_image_paths})
        
    except Exception as e:
        print(f"An error occurred in get_knowledge_base: {e}")
        import traceback
        traceback.print_exc()
        return "An error occurred while retrieving knowledge."

# Run the server
if __name__ == "__main__":
    print('Running MCP server on SSE')
    mcp.run(transport="sse")