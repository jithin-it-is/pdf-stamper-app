import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
import io
import os
from PIL import Image
import math

def create_text_stamp(text, font_size=20, text_color=(1, 0, 0), opacity=1.0, rotation=0):
    """Create a PDF stamp with text"""
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    
    # Set opacity
    can.setFillAlpha(opacity)
    can.setStrokeAlpha(opacity)
    
    # Set text properties
    can.setFillColorRGB(*text_color)
    can.setFont("Helvetica", font_size)
    
    # Apply rotation
    if rotation != 0:
        can.rotate(rotation)
    
    can.drawString(10, 10, text)
    can.save()
    packet.seek(0)
    return PdfReader(packet)

def stamp_pdf(input_pdf, stamp_content, position, x_offset=0, y_offset=0, every_page=True, is_image=False, opacity=1.0, rotation=0, stamp_width=None, stamp_height=None):
    """Stamp a PDF with the given content at the specified position"""
    output = PdfWriter()
    
    # Standard letter size dimensions (612x792 points)
    page_width = 612
    page_height = 792
    
    # If stamp dimensions aren't provided, use defaults
    if stamp_width is None:
        stamp_width = 100
    if stamp_height is None:
        stamp_height = 100
    
    # Calculate position coordinates
    if position == "Top Left":
        x, y = 10 + x_offset, page_height - stamp_height - 10 - y_offset
    elif position == "Top Right":
        x, y = page_width - stamp_width - 10 - x_offset, page_height - stamp_height - 10 - y_offset
    elif position == "Bottom Left":
        x, y = 10 + x_offset, 10 + y_offset
    elif position == "Bottom Right":
        x, y = page_width - stamp_width - 10 - x_offset, 10 + y_offset
    elif position == "Center":
        x = (page_width - stamp_width) / 2 + x_offset
        y = (page_height - stamp_height) / 2 + y_offset
    
    for i in range(len(input_pdf.pages)):
        page = input_pdf.pages[i]
        
        if every_page or i == 0:
            # Create new stamp for each page
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=letter)
            
            # Set opacity
            can.setFillAlpha(opacity)
            can.setStrokeAlpha(opacity)
            
            if is_image:
                # Draw image stamp - we use the original image and let ReportLab handle scaling
                img = stamp_content['image']
                scale = stamp_content['scale']
                original_width, original_height = stamp_content['original_dimensions']
                
                # Calculate final dimensions
                width = int(original_width * scale)
                height = int(original_height * scale)
                
                # Apply rotation to the canvas
                if rotation != 0:
                    # Calculate center of the stamp
                    center_x = x + width / 2
                    center_y = y + height / 2
                    
                    # Translate to center, rotate, then translate back
                    can.translate(center_x, center_y)
                    can.rotate(rotation)
                    can.translate(-center_x, -center_y)
                
                # Use the original image and let ReportLab handle the scaling
                img_reader = ImageReader(img)
                can.drawImage(img_reader, x, y, width=width, height=height, mask='auto', preserveAspectRatio=True)
            else:
                # Apply rotation to the canvas for text
                if rotation != 0:
                    # Calculate center of the text (approximate)
                    text_width = len(stamp_content) * 10  # Rough estimate
                    center_x = x + text_width / 2
                    center_y = y + 10  # Font size/2 would be better
                    
                    can.translate(center_x, center_y)
                    can.rotate(rotation)
                    can.translate(-center_x, -center_y)
                
                # Draw text stamp
                can.setFillColorRGB(1, 0, 0)
                can.setFont("Helvetica", 20)
                can.drawString(x, y, stamp_content)
            
            can.save()
            packet.seek(0)
            temp_stamp = PdfReader(packet)
            page.merge_page(temp_stamp.pages[0])
        
        output.add_page(page)
    
    return output

def main():
    st.title("PDF Stamping Application")
    
    uploaded_file = st.file_uploader("Upload PDF to stamp", type="pdf")
    stamp_type = st.radio("Stamp Type", ["Text", "Image"])
    
    if stamp_type == "Text":
        stamp_text = st.text_input("Stamp Text", "CONFIDENTIAL")
        text_color = st.color_picker("Text Color", "#FF0000")
        font_size = st.slider("Font Size", 10, 72, 20)
    else:
        stamp_image = st.file_uploader("Upload Stamp Image", type=["png", "jpg", "jpeg"])
        if stamp_image is not None:
            img = Image.open(stamp_image)
            original_width, original_height = img.size
            
            # Display original dimensions
            st.write(f"Original image dimensions: {original_width} x {original_height} pixels")
            
            # Single slider for scaling (default 1.0 = original size)
            scale = st.slider("Stamp Scale", 0.1, 5.0, 1.0, 0.1,
                            help="1.0 = original size, 0.5 = half size, 2.0 = double size")
            
            # Calculate and display preview dimensions
            preview_width = int(original_width * scale)
            preview_height = int(original_height * scale)
            st.write(f"Preview dimensions: {preview_width} x {preview_height} pixels")
            
            # Show preview of the stamp
            st.image(img, caption="Original Stamp Preview", use_column_width=True)
    
    position_options = ["Top Left", "Top Right", "Bottom Left", "Bottom Right", "Center"]
    position = st.selectbox("Stamp Position", position_options)
    
    st.markdown("**Advanced Options**")
    col1, col2 = st.columns(2)
    with col1:
        x_offset = st.slider("X Offset (left/right)", -100, 100, 0)
    with col2:
        y_offset = st.slider("Y Offset (up/down)", -100, 100, 0)
    
    col3, col4 = st.columns(2)
    with col3:
        opacity = st.slider("Opacity", 0.1, 1.0, 1.0, 0.1)
    with col4:
        rotation = st.slider("Rotation (degrees)", -180, 180, 0)
    
    every_page = st.checkbox("Stamp every page", True)
    
    if st.button("Apply Stamp") and uploaded_file is not None:
        with st.spinner("Processing PDF..."):
            input_pdf = PdfReader(uploaded_file)
            
            if stamp_type == "Text":
                rgb_color = tuple(int(text_color.lstrip('#')[i:i+2], 16)/255 for i in (0, 2, 4))
                output_pdf = stamp_pdf(
                    input_pdf, 
                    stamp_text, 
                    position, 
                    x_offset, 
                    y_offset, 
                    every_page, 
                    is_image=False,
                    opacity=opacity,
                    rotation=rotation
                )
            else:
                if stamp_image is not None:
                    img = Image.open(stamp_image).convert("RGBA")
                    
                    # Prepare stamp content with original dimensions and scale
                    stamp_content = {
                        'image': img,
                        'original_dimensions': (original_width, original_height),
                        'scale': scale
                    }
                    
                    output_pdf = stamp_pdf(
                        input_pdf, 
                        stamp_content, 
                        position, 
                        x_offset, 
                        y_offset, 
                        every_page, 
                        is_image=True,
                        opacity=opacity,
                        rotation=rotation,
                        stamp_width=int(original_width * scale),
                        stamp_height=int(original_height * scale)
                    )
                else:
                    st.warning("Please upload an image for the stamp")
                    return
            
            output_stream = io.BytesIO()
            output_pdf.write(output_stream)
            output_stream.seek(0)
            
            st.success("PDF Stamped Successfully!")
            st.download_button(
                label="Download Stamped PDF",
                data=output_stream,
                file_name="stamped_document.pdf",
                mime="application/pdf"
            )

if __name__ == "__main__":
    main()