def scale_box_to_pdf(jpg_box, jpg_size, pdf_size):
    x1, y1, x2, y2 = jpg_box
    
    # Scale the coordinates
    pdf_x1 = x1 * pdf_size[0] / jpg_size[0]
    pdf_y1 = y1 * pdf_size[1] / jpg_size[1]
    pdf_x2 = x2 * pdf_size[0] / jpg_size[0]
    pdf_y2 = y2 * pdf_size[1] / jpg_size[1]
    
    return pdf_x1, pdf_y1, pdf_x2, pdf_y2