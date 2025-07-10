from pdfminer.layout import LTTextBoxHorizontal
import re

def mine_text(page_layout):
    """
    Extracts text from a PDF page layout by ordering the text boxes.
    This provides a more accurate reading order than iterating through
    all text containers.
    """
    text_boxes = [elem for elem in page_layout if isinstance(elem, LTTextBoxHorizontal)]

    text_boxes.sort(key=lambda x: (-x.y1, x.x0))

    page_text = "\n".join([box.get_text() for box in text_boxes])
    
    return page_text.strip()

# def mine_images(page_layout):
#     images = []
#     for element in page_layout:
#         if isinstance(element, LTImage):
#             images.append(element)
#     return images

# def mine_tables(page_layout):
#     tables = []
#     for element in page_layout:
#         if isinstance(element, LTTable):
#             tables.append(element)
#     return tables