import ollama
from PIL import Image
import base64
import io
from pdf2image import convert_from_path

def document_to_base64(document_path):
    if document_path.lower().endswith('.pdf'):
        return encode_pdf_to_base64(document_path)
    else:
        return encode_image_to_base64(document_path)

def encode_pdf_to_base64(pdf_path):
    images = convert_from_path(pdf_path)
    base64_encoded_images = []

    for img in images:
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        base64_encoded_images.append(img_base64)

    return base64_encoded_images

def encode_image_to_base64(image_path):
    with Image.open(image_path) as img:
        buffered = io.BytesIO()
        img.save(buffered, format=img.format)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

def extract_pan_details(base64_image):
    """
    Uses Ollama to extract details from a PAN card image.

    Args:
        base64_image (str): The base64-encoded image of the PAN card.

    Returns:
        dict: A dictionary containing the PAN card details.
    """
    response = ollama.chat(
        model="llama3.2-vision:latest",
        messages=[{
            "role": "user",
            "content": "The image is an Indian PAN Card. Output should be in this format - <Name of the PAN Card Holder>, <Father's Name>, <PAN Number>, <Date of Birth>. Do not output anything else.",
            "images": [base64_image]
        }],
    )
    
    response_text = response['message']['content'].strip()
    
    pan_details = response_text.split(',')
    
    return {
        "Name": pan_details[0].strip(),
        "Father's Name": pan_details[1].strip(),
        "PAN NO": pan_details[2].strip(),
        "DOB": pan_details[3].strip()
    }

# Main execution
if __name__ == "__main__":
    image_path = 'Downloads/2.jpg'  # Replace with your image path
    base64_image = document_to_base64(image_path)
    
    pan_dict = extract_pan_details(base64_image)
    
    print(pan_dict)
