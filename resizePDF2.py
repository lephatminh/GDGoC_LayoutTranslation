import os
from PyPDF2 import PdfReader, PdfWriter, Transformation
import copy

def scale_pdf_properly(input_path, output_path, target_width=1025, target_height=1025):
    """
    Scale a PDF to the target dimensions ensuring both page size and content are scaled.

    Args:
        input_path (str): Path to the input PDF file
        output_path (str): Path where the scaled PDF will be saved
        target_width (int): Target width in pixels (default: 1025)
        target_height (int): Target height in pixels (default: 1025)
    """
    # Read the original PDF
    reader = PdfReader(input_path)
    writer = PdfWriter()

    # Convert target dimensions from pixels to points (72 points = 1 inch)
    # Assuming 72 DPI resolution
    target_width_pts = target_width
    target_height_pts = target_height

    # Process each page
    for page_num in range(len(reader.pages)):
        # Get the original page
        original_page = reader.pages[page_num]

        # Get original page dimensions
        mediabox = original_page.mediabox
        orig_width = float(mediabox.width)
        orig_height = float(mediabox.height)

        # Calculate scaling factors
        width_scale = target_width_pts / orig_width
        height_scale = target_height_pts / orig_height

        # Create a copy of the page to work with
        page = copy.deepcopy(original_page)

        # Apply scaling transformation to the content
        transform = Transformation().scale(width_scale, height_scale)
        page.add_transformation(transform)

        # Update the mediabox to the new dimensions
        # PyPDF2 uses a coordinate system with (0,0) at the bottom left
        page.mediabox.lower_left = (0, 0)
        page.mediabox.upper_right = (target_width_pts, target_height_pts)

        # Also update cropbox and trimbox if they exist
        if "/CropBox" in page:
            page.cropbox.lower_left = (0, 0)
            page.cropbox.upper_right = (target_width_pts, target_height_pts)

        if "/TrimBox" in page:
            page.trimbox.lower_left = (0, 0)
            page.trimbox.upper_right = (target_width_pts, target_height_pts)

        if "/ArtBox" in page:
            page.artbox.lower_left = (0, 0)
            page.artbox.upper_right = (target_width_pts, target_height_pts)

        if "/BleedBox" in page:
            page.bleedbox.lower_left = (0, 0)
            page.bleedbox.upper_right = (target_width_pts, target_height_pts)

        # Add the scaled page to the output PDF
        writer.add_page(page)

    # Write the result to the output file
    with open(output_path, "wb") as output_file:
        writer.write(output_file)

    print(f"PDF scaled successfully to {target_width}x{target_height}.")
    print(f"Both page dimensions and content have been scaled. Saved to {output_path}")

# Example usage
if __name__ == "__main__":
    input_file = "sample_input.pdf"  # Replace with your input file path
    output_file = "sample_input_coco_standard.pdf"  # Replace with your desired output file path

    scale_pdf_properly(input_file, output_file, 1025, 1025)