from paddleocr import PaddleOCR
import re
import fitz  # PyMuPDF

class DocumentExtractor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.ocr = PaddleOCR(use_angle_cls=True, lang='en')

    def extract_dl_numbers(self):
        """Extract Driving License numbers from the specified file."""
        return self._extract_numbers(r"^[A-Z]{2}[0-9]{14}|^[A-Z]{2}[0-9]{13}")

    def extract_pan_numbers(self):
        """Extract PAN numbers from the specified file."""
        return self._extract_numbers(r"^[A-Z0-9]{5}[0-9]{4}[A-Z0-9]{1}", pan_correction=True)

    def extract_epic_numbers(self):
        """Extract EPIC numbers from the specified file."""
        return self._extract_numbers(r"^[A-Za-z]{3}\d{7}$")

    def _extract_numbers(self, pattern, pan_correction=False):
        """Generic method to extract numbers based on a regex pattern."""
        filtered_numbers = []
        filename = self.file_path

        if filename.lower().endswith(('.jpg', '.png', '.jpeg')):
            result = self.ocr.ocr(filename)
            filtered_numbers = self._process_ocr_result(result, pattern)
        else:
            pages = self._convert_pdf_to_images(filename)
            for i, page in enumerate(pages):
                temp_filename = f"{filename.split('/')[-1].split('.')[0]}_temp_{i}.jpg"
                page.save(temp_filename, 'JPEG')
                result = self.ocr.ocr(temp_filename)
                filtered_numbers.extend(self._process_ocr_result(result, pattern))

        filtered_numbers = list(dict.fromkeys(filtered_numbers))  # Remove duplicates

        if pan_correction and filtered_numbers:
            filtered_numbers = [self.pan_correction(num) for num in filtered_numbers]

        if not filtered_numbers:
            print(f'No matches found for pattern: {pattern}')
            return []

        return filtered_numbers

    @staticmethod
    def pan_correction(pan):
        """Correct PAN number format by replacing '0' with 'O'."""
        if len(pan) >= 10:  # Ensure the pan is at least 10 characters long
            pan_new = pan[0:5].replace('0', 'O') + pan[5:9] + pan[9].replace('0', 'O')
            return pan_new
        else:
            print(f"Invalid PAN number: {pan}. Skipping correction.")
            return pan  # Return the original PAN if it's invalid

    @staticmethod
    def _process_ocr_result(result, pattern):
        """Process OCR results to find matches based on a regex pattern."""
        matches = []
        for res in result:
            for line in res:
                text = line[1][0]
                found_matches = re.findall(pattern, text)
                if found_matches:
                    matches.extend(found_matches)
        return matches

    def _convert_pdf_to_images(self, pdf_path):
        """Convert PDF pages to images using PyMuPDF (fitz)."""
        doc = fitz.open(pdf_path)
        images = []
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            # Render the page as a pixmap (image)
            pix = page.get_pixmap(dpi=300)
            image = fitz.Pixmap(pix)
            images.append(image)
        return images

if __name__ == "__main__":
    file_path = r"C:\Users\dwaip\OneDrive\Desktop\Aadhar_pan\card3.png" 

    extractor = DocumentExtractor(file_path)

    # Extract Driving License numbers
    dl_numbers = extractor.extract_dl_numbers()
    print("Driving License Numbers:", dl_numbers)


    pan_numbers = extractor.extract_pan_numbers()
    print("PAN Numbers:", pan_numbers)

    epic_numbers = extractor.extract_epic_numbers()
    print("EPIC Numbers:", epic_numbers)
