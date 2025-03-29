import fitz
import os

def resize_pdf_to_coco_standard(input_pdf_path, output_pdf_path, preserve_aspect_ratio=True):
    """
    Resize a PDF document to COCO standard dimensions (1025x1025).
    
    Args:
        input_pdf_path (str): Path to the input PDF file
        output_pdf_path (str): Path to save the resized PDF file
        preserve_aspect_ratio (bool, optional): Whether to preserve the aspect ratio. 
                                               Defaults to True.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if input file exists
        if not os.path.isfile(input_pdf_path):
            print(f"Error: Input file '{input_pdf_path}' does not exist.")
            return False
            
        # Open source document
        src_doc = fitz.open(input_pdf_path)
        target_doc = fitz.open()

        coco_width = 1025
        coco_height = 1025

        for page_num in range(len(src_doc)):
            page = src_doc[page_num]
            src_width, src_height = page.rect.width, page.rect.height
            
            # Create new page with target dimensions
            target_page = target_doc.new_page(width=coco_width, height=coco_height)
            
            if preserve_aspect_ratio:
                # Calculate scaling factors
                scale_x = coco_width / src_width
                scale_y = coco_height / src_height
                scale = min(scale_x, scale_y)
                
                # Calculate dimensions after scaling
                scaled_width = src_width * scale
                scaled_height = src_height * scale
                
                # Calculate position to center the content
                x_offset = (coco_width - scaled_width) / 2
                y_offset = (coco_height - scaled_height) / 2
                
                # Create transformation matrix that both scales and translates
                matrix = fitz.Matrix(scale, scale)
                
                # We need to transform the source page first to scale it
                # Then specify where to place it on the target page
                target_rect = fitz.Rect(
                    x_offset, y_offset, 
                    x_offset + scaled_width, 
                    y_offset + scaled_height
                )
                
                # The key is using the correct source rectangle - the entire source page
                src_rect = page.rect
                
                # Draw the source page onto the target page with proper scaling
                target_page.show_pdf_page(
                    target_rect,  # Where to place it on target
                    src_doc,      # Source document
                    page_num,     # Source page number
                    clip=src_rect # Use the entire source page
                )
            else:
                # For non-preserved aspect ratio, we directly stretch to fit
                target_page.show_pdf_page(
                    target_page.rect,  # Fill the entire target page
                    src_doc,           # Source document
                    page_num,          # Source page number
                    clip=page.rect     # Use the entire source page
                )
        
        # Save and close documents
        target_doc.save(output_pdf_path)
        target_doc.close()
        src_doc.close()
        print(f"Resized PDF saved to: {output_pdf_path}")
        return True
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    input_pdf = "sample_input.pdf"
    output_pdf = "sample_input_coco_standard.pdf"
    resize_pdf_to_coco_standard(input_pdf, output_pdf)