import cv2
import pytesseract
import re

# Load the image from file
image_path = 'path_to_your_image.jpg'  # Replace with your image path
image = cv2.imread(image_path)

# Preprocess the image (convert to gray scale)
gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# Apply thresholding to get a binary image
_, binary_image = cv2.threshold(gray_image, 150, 255, cv2.THRESH_BINARY_INV)

# Use Tesseract to extract text
custom_config = r'--oem 3 --psm 6'
extracted_text = pytesseract.image_to_string(binary_image, config=custom_config)

# Function to extract required details using regex
def extract_details(text):
    details = {}

    # Extracting date (format: DD/MM/YYYY)
    date_pattern = r'\b\d{1,2}/\d{1,2}/\d{4}\b'
    dates = re.findall(date_pattern, text)
    details['dates'] = dates

    # Extracting bank details (assuming bank account number is a sequence of digits)
    bank_details_pattern = r'\b\d{9,18}\b' 
    bank_details = re.findall(bank_details_pattern, text)
    details['bank_account_numbers'] = bank_details

    # Extracting bank name (assuming it follows a specific keyword)
    bank_name_pattern = r'Bank Name of Bank\s*([A-Za-z\s]+)'
    bank_name_match = re.search(bank_name_pattern, text)
    details['bank_name'] = bank_name_match.group(1).strip() if bank_name_match else None

    # Extracting amount (assuming it follows a currency format)
    amount_pattern = r'(\d+(?:,\d{3})*(?:\.\d{2})?)'
    amounts = re.findall(amount_pattern, text)
    details['amounts'] = amounts

    # Extracting email ID
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text)
    details['emails'] = emails

    # Extracting phone number (assuming Indian format)
    phone_pattern = r'\b\d{10}\b'  # Adjust based on expected phone number format
    phones = re.findall(phone_pattern, text)
    details['phone_numbers'] = phones

    return details

# Extract the details from the extracted text
details_extracted = extract_details(extracted_text)

# Print the extracted details
print("Extracted Details:")
for key, value in details_extracted.items():
    print(f"{key}: {value}")