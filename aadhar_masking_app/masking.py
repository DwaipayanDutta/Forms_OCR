import os
import re
import io
import json
import base64
import fitz
from io import BytesIO
from PIL import Image, ImageDraw
from ollama import Ollama


Image.MAX_IMAGE_PIXELS = 1_000_000_000


class AadharMask:
    """Detect and mask Aadhaar numbers from PDFs or images using OCR via Llama Vision."""

    AADHAAR_PATTERN = re.compile(r"(?<!\d)\d{4} \d{4} \d{4}(?!\d)")
    POINTS_PER_INCH = 72

    MULTIPLICATION_TABLE = (
        (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
        (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
        (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
        (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
        (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
        (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
        (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
        (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
        (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
        (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
    )

    PERMUTATION_TABLE = (
        (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
        (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
        (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
        (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
        (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
        (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
        (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
        (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
    )

    def __init__(self):
        self.ollama = Ollama()
        self.model_name = "llama3.2-vision"

    def compute_checksum(self, number: str) -> int:
        """Compute Aadhaar checksum (Verhoeff algorithm)."""
        digits = [int(n) for n in str(number)[::-1]]
        checksum = 0
        for i, n in enumerate(digits):
            checksum = self.MULTIPLICATION_TABLE[checksum][self.PERMUTATION_TABLE[i & 7][n]]
        return checksum

    def analyze_read(self, input_path: str):
        """Run OCR via Llama Vision."""
        images = []

        if input_path.lower().endswith(".pdf"):
            doc = fitz.open(input_path)
            for page in doc:
                pix = page.get_pixmap(dpi=100)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images.append(img)
                del pix
            doc.close()
        else:
            images.append(Image.open(input_path))

        ocr_results = []
        for img in images:
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_b64 = base64.b64encode(buffered.getvalue()).decode()
            buffered.close()

            response = self.ollama.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "Extract text and positions as JSON."},
                    {"role": "user", "content": img_b64},
                ],
            )
            result = json.loads(response["choices"][0]["message"]["content"])
            ocr_results.append(result)
            img.close()

        return {"pages": ocr_results}

    def convert_img_to_b64(self, img) -> str:
        buf = BytesIO()
        img.save(buf, format="PNG")
        result = base64.b64encode(buf.getvalue()).decode()
        buf.close()
        return result

    def convert_pdf_to_b64(self, doc) -> str:
        pdf_bytes = doc.write()
        return base64.b64encode(pdf_bytes).decode("utf-8")

    def mask_aadhar_img(self, img, page):
        """Mask Aadhaar number regions in an image."""
        img_draw = ImageDraw.Draw(img)
        words = [w for w in getattr(page, "words", []) if any(c.isdigit() for c in w["content"])]
        text = "\n".join([line["content"] for line in page["lines"]])

        match = self.AADHAAR_PATTERN.search(text)
        comment = "No Aadhaar number detected"
        invalid_aadhar = 1

        if match:
            aadhar_number = re.sub(r"\s", "", match.group())
            if self.compute_checksum(aadhar_number) == 0:
                masked_words = match.group().strip().split()[:2]
                for word in words:
                    if word["content"].strip() in masked_words:
                        x_min, y_min, x_max, y_max = word["bbox"]
                        img_draw.rectangle((x_min, y_min, x_max, y_max), fill="orange")
                comment = "Aadhaar masked successfully"
                invalid_aadhar = 0
            else:
                comment = "Checksum failed, invalid Aadhaar detected"

        return img, comment, invalid_aadhar

    def mask_aadhar_final(self, input_path: str):
        """Main entry point for masking operation."""
        ocr_extract = self.analyze_read(input_path)
        all_comments = []
        invalid_count = 0

        if input_path.lower().endswith(".pdf"):
            doc = fitz.open(input_path)
            for idx, page in enumerate(ocr_extract["pages"]):
                text = " ".join([l["content"] for l in page["lines"]])
                matches = self.AADHAAR_PATTERN.findall(text)
                if not matches:
                    invalid_count += 1
                    all_comments.append("No Aadhaar number detected")
                    continue
                # Add masking logic for PDF if needed
            base64_output = self.convert_pdf_to_b64(doc)
            doc.close()
        else:
            img = Image.open(input_path)
            page = ocr_extract["pages"][0]
            masked_img, comment, invalid = self.mask_aadhar_img(img, page)
            invalid_count += invalid
            all_comments.append(comment)
            base64_output = self.convert_img_to_b64(masked_img)
            img.close()

        valid_flag = invalid_count == 0
        final_comment = "Aadhaar masking completed" if valid_flag else "Invalid or no Aadhaar detected"

        return {
            "base64_output": base64_output,
            "valid": valid_flag,
            "comments": all_comments,
            "summary": final_comment,
        }
