import re

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