import os
import re
import gc
import json
import base64
import asyncio
import concurrent.futures
from io import BytesIO
from PIL import Image, ImageDraw
import fitz
import pandas as pd

from azure.ai.formrecognizer.aio import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from exceptions import *


class aadhar_mask:
    def __init__(self):
        self.multiplication_table = (
            (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
            (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
            (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
            (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
            (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
            (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
            (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
            (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
            (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
            (9, 8, 7, 6, 5, 4, 3, 2, 1, 0)
        )
        self.permutation_table = (
            (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
            (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
            (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
            (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
            (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
            (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
            (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
            (7, 0, 4, 6, 9, 1, 3, 2, 5, 8)
        )
        self.KEY = os.environ["azure_di_key"]
        self.ENDPOINT = os.environ["azure_di_endpoint"]

    def compute_checksum(self, number):
        number = tuple(int(n) for n in reversed(str(number)))
        checksum = 0
        for i, n in enumerate(number):
            checksum = self.multiplication_table[checksum][self.permutation_table[i % 8][n]]
        return checksum

    async def async_analyze_read(self, img_path):
        try:
            async with DocumentAnalysisClient(
                endpoint=self.ENDPOINT, credential=AzureKeyCredential(self.KEY)
            ) as client:
                with open(img_path, "rb") as f:
                    poller = await client.begin_analyze_document(
                        "prebuilt-read", document=f, locale='en-US'
                    )
                    result = await poller.result()
        except Exception as Err:
            raise DocumentIntelligenceException('OCR failed at Azure Cognitive services. Error: ' + str(Err))
        return result

    async def async_get_azure_extract_multi(self, img_path_list, request_id, logger):
        tasks = [self.async_analyze_read(img_path) for img_path in img_path_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        extract_list = []
        for idx, res in enumerate(results):
            if isinstance(res, Exception):
                logger.error(f'OCR failed for {img_path_list[idx]}: {str(res)}')
                raise DocumentIntelligenceException(f'OCR failed for {img_path_list[idx]}: {str(res)}')
            extract_list.append(res)
        return extract_list

    def get_azure_extract(self, img_path, request_id, logger):
        file_name = img_path.split('/')[-1].split('.')[0].replace(f'_{request_id}', '') + '_prebuilt-read'
        extract_exists = None  # Replace with DB lookup if needed
        if extract_exists:
            extract_exists = pd.DataFrame(extract_exists)
            extract_file_list = extract_exists['fileName'].unique().tolist()
        else:
            extract_file_list = []
        if file_name not in extract_file_list:
            logger.info(f'[{request_id}] > Reading extract from Azure for {file_name}')
            return self.analyze_read(f"./uploaded_images_maskdoc/{img_path}")
        else:
            result = extract_exists.loc[extract_exists['fileName'] == file_name, 'azureExtract'].copy()
            result = json.loads(result.iloc[0])
        return result

    def analyze_read(self, img_path):
        try:
            document_analysis_client = DocumentAnalysisClient(
                endpoint=self.ENDPOINT, credential=AzureKeyCredential(self.KEY)
            )
            with open(img_path, "rb") as f:
                poller = document_analysis_client.begin_analyze_document(
                    "prebuilt-read", document=f, locale='en-US'
                )
                result = poller.result()
        except Exception as Err:
            raise DocumentIntelligenceException('OCR failed at Azure Cognitive services. Error: ' + str(Err))
        return result

    def resize_image(self, img, max_width=1000):
        orig_width, orig_height = img.width, img.height
        if img.width > max_width:
            aspect_ratio = img.height / img.width
            new_height = int(max_width * aspect_ratio)
            img = img.resize((max_width, new_height), Image.LANCZOS)
        return img, (orig_width, orig_height)

    def convert_img_highres(self, img, orig_width, orig_height):
        return img.resize((orig_width, orig_height))

    def get_images(self, input_file, max_width=1500):
        img_list = []
        img_size = []

        def should_resize(path_or_bytes):
            if isinstance(path_or_bytes, str):
                size_kb = os.path.getsize(path_or_bytes) / 1024
            elif isinstance(path_or_bytes, bytes):
                size_kb = len(path_or_bytes) / 1024
            else:
                return True
            return size_kb > 500

        if input_file.lower().endswith('.pdf'):
            pdf = fitz.open(input_file)
            if pdf.page_count > 3:
                raise DocumentPageLimitExceeded('More than 3 pages detected')
            for i in range(min(3, pdf.page_count)):
                page = pdf.load_page(i)
                pix = page.get_pixmap(matrix=fitz.Matrix(5, 5))
                img_bytes = pix.tobytes("png")
                img = Image.open(BytesIO(img_bytes))
                if should_resize(img_bytes):
                    img, size = self.resize_image(img, max_width)
                else:
                    size = (img.width, img.height)
                img_list.append(img)
                img_size.append(size)
        else:
            if should_resize(input_file):
                img = Image.open(input_file)
                img, size = self.resize_image(img, max_width)
            else:
                img = Image.open(input_file)
                size = (img.width, img.height)
            img_list.append(img)
            img_size.append(size)
        return img_list, img_size

    def get_text_bb(self, img_ocr_extract):
        img_ocr_extract = img_ocr_extract if isinstance(img_ocr_extract, dict) else img_ocr_extract.to_dict()
        text_pages = img_ocr_extract.get('pages')
        text_content, bounding_boxes, units = {}, {}, {}
        for i, page in enumerate(text_pages):
            text_content2 = ""
            bounding_boxes2 = []
            for word in page.get('words'):
                text_content2 += " " + word.get('content').strip()
                bounding_boxes2.append({'text': word.get('content').strip(), 'bounding_box': word.get('polygon')})
            text_content[i] = text_content2
            bounding_boxes[i] = bounding_boxes2
            units[i] = page.get('unit')
        return text_content, bounding_boxes, units

    def mask_aadhar_img(self, img, text_content, bounding_boxes, unit, img_size):
        img = self.convert_img_highres(img.copy(), img_size[0], img_size[1])
        img_draw = ImageDraw.Draw(img)
        mult_val = 72 * 5 if unit.lower().strip() == 'inch' else 1
        aadhaar_number_pattern = r"\s\d{4}\s\d{4}\s\d{4}\s?\b"
        aadhaar_number_match = re.search(aadhaar_number_pattern, text_content)
        invalid_aadhar = 0
        comment = ''
        if aadhaar_number_match:
            aadhar_number = re.sub(r'\s', '', aadhaar_number_match.group())
            if self.compute_checksum(aadhar_number) == 0:
                comment = 'aadhar number is valid'
                adr_split = aadhaar_number_match.group().strip().split(' ')
                adr_8digit = adr_split[:2]
                for bb in bounding_boxes:
                    if bb['text'] in adr_8digit:
                        polygon = bb['bounding_box']
                        x_min = min(p['x'] for p in polygon)
                        y_min = min(p['y'] for p in polygon)
                        x_max = max(p['x'] for p in polygon)
                        y_max = max(p['y'] for p in polygon)
                        rect = (int(x_min * mult_val), int(y_min * mult_val),
                                int(x_max * mult_val), int(y_max * mult_val))
                        img_draw.rectangle(rect, fill="orange", outline="orange", width=3)
                        gc.collect()
            else:
                comment = 'checksum failed, invalid aadhar detected'
                invalid_aadhar = 1
        else:
            comment = 'no aadhar number detected'
            invalid_aadhar = 1
        return img, comment, invalid_aadhar

    # Optimization: Convert image to JPEG bytes for faster base64 encoding
    def img_to_jpeg_bytes(self, img, quality=75):
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=quality)
        return buffer.getvalue()

    # Optimization: Parallel base64 encoding of images using threads
    def encode_img_base64_parallel(self, images):
        results = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(lambda im: base64.b64encode(self.img_to_jpeg_bytes(im)).decode('utf-8'), img) for img in images]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        return results

    # Optimization: Save images as compressed PDF (converted to RGB)
    def convert_img_to_b64(self, masked_img_list):
        pdf_buffer = BytesIO()
        images_rgb = [im.convert('RGB') for im in masked_img_list]
        images_rgb[0].save(pdf_buffer, format='PDF', save_all=True, append_images=images_rgb[1:], quality=75)
        pdf_base64 = base64.b64encode(pdf_buffer.getvalue()).decode('utf-8')
        return pdf_base64

    async def mask_aadhar_final_async(self, img_path_list, logger, request_id):
        import time
        start_time = time.time()

        # Load and resize images
        image_list, img_size = [], []
        for img_path in img_path_list:
            imgs, sizes = self.get_images(img_path)
            image_list.extend(imgs)
            img_size.extend(sizes)
        logger.info(f'[{request_id}] > Extracted image list from all inputs.')

        # Parallel OCR extraction
        ocr_extracts = await self.async_get_azure_extract_multi(img_path_list, request_id, logger)
        logger.info(f'[{request_id}] > Azure OCR extract completed for all inputs.')

        # Extract text, bounding boxes, and units from OCR per page
        total_pages = len(ocr_extracts)
        text_content, bounding_boxes, units = {}, {}, {}
        for idx, extract in enumerate(ocr_extracts):
            tc, bb, u = self.get_text_bb(extract)
            text_content[idx] = ' '.join(tc.values())
            bounding_boxes[idx] = sum(bb.values(), [])
            units[idx] = u[0] if u else 'pixel'
        logger.info(f'[{request_id}] > Bounding box extraction completed.')
        logger.info(f'[{request_id}] > Aadhar masking started.')

        # Mask images
        masked_img_list = []
        invalid_aadhar_count = 0
        comments = ''
        for i, img in enumerate(image_list):
            masked_img, comment, inv_adhar = self.mask_aadhar_img(
                img, text_content.get(i, ''), bounding_boxes.get(i, []), units.get(i, 'pixel'), img_size[i])
            comments += ' | ' + comment
            masked_img_list.append(masked_img)
            invalid_aadhar_count += inv_adhar
            logger.info(f'[{request_id}] > Page {i + 1} | {comment}')
            gc.collect()

        # Convert masked images to base64 encoded compressed PDF
        pdf_base64_output = self.convert_img_to_b64(masked_img_list)

        valid_flag = True
        comment = ''
        if invalid_aadhar_count == len(image_list):
            valid_flag = False
            comment = "checksum failed, invalid aadhar detected" if "checksum" in comments else "no UID found | no aadhar number detected"
            logger.info(f'[{request_id}] > No UID found.')
        else:
            logger.info(f'[{request_id}] > Aadhar masking completed.')

        end_time = time.time()
        logger.info(f'[{request_id}] > Total processing time: {end_time - start_time:.2f} seconds')

        return "", pdf_base64_output, valid_flag, comment
