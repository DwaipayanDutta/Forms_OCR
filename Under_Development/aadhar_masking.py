import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
import img2pdf
import pdf2image
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
import tifftools
import os

class aadhar_text:
    def __init__(self, text):
        self.text = text

    def adhaar_read_data(self):
        res = self.text.split()
        name = None
        dob = None
        adh = None
        sex = None
        nameline = []
        dobline = []
        text0 = []
        text1 = []
        text2 = []
        lines = self.text.split('\n')
        for lin in lines:
            s = lin.strip()
            s = lin.replace('\n','')
            s = s.rstrip()
            s = s.lstrip()
            text1.append(s)

        if 'female' in self.text.lower():
            sex = "FEMALE"
        else:
            sex = "MALE"
        
        text1 = list(filter(None, text1))
        text0 = text1[:]
        
        try:
            # Cleaning first names
            name = text0[0]
            name = name.rstrip()
            name = name.lstrip()
            name = name.replace("8", "B")
            name = name.replace("0", "D")
            name = name.replace("6", "G")
            name = name.replace("1", "I")
            name = re.sub('[^a-zA-Z]+', ' ', name)

            # Cleaning DOB
            dob = text0[1][-10:]
            dob = dob.rstrip()
            dob = dob.lstrip()
            dob = dob.replace('l', '/')
            dob = dob.replace('L', '/')
            dob = dob.replace('I', '/')
            dob = dob.replace('i', '/')
            dob = dob.replace('|', '/')
            dob = dob.replace('\"', '/1')
            dob = dob.replace(":", "")
            dob = dob.replace(" ", "")

            # Cleaning Aadhaar number details
            aadhar_number = ''
            for word in res:
                if len(word) == 4 and word.isdigit():
                    aadhar_number = aadhar_number + word + ' '
            if len(aadhar_number) >= 14:
                print("Aadhar number is :"+ aadhar_number)
            else:
                print("Aadhar number not read")
            adh = aadhar_number
        except:
            pass

        data = {}
        data['Name'] = name
        data['Date of Birth'] = dob
        data['Adhaar Number'] = adh
        data['Sex'] = sex
        data['ID Type'] = "Adhaar"
        return data
    
    @staticmethod
    def findword(textlist, wordstring):
        lineno = -1
        for wordline in textlist:
            xx = wordline.split()
            if ([w for w in xx if re.search(wordstring, w)]):
                lineno = textlist.index(wordline)
                textlist = textlist[lineno + 1:]
                return textlist
        return textlist

class aadhar_fetch:

    def __init__(self, image_file_path):
        self.image_file_path = image_file_path
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

    @staticmethod
    def find_text(text):
        n = len(text)
        if n < 12:
            return 0
        for i in range(14, n):
            s = text[i - 14:i]
            if s[4] == " " and s[9] == " ":
                s = s.replace(" ", "")
                n1 = len(s)
                s1 = s[n1 - 12:n1]
                if i == 125:
                    pass
                if s1.isnumeric() and len(s1) >= 12:
                    return 1
        return 0

    def addhar_check(self, file_name):
        img = Image.open(file_name)
        u = 0
        for i in range(25):
            try:
                img.seek(i)
                u = u + 1
                array = np.array(img)
                c = len(array.shape)
                if c == 2:
                    if array[0][0] == True or array[0][0] == False:
                        array = array * 255
                        img10 = array.astype(np.uint8)
                        array = np.array(img10)

                elif c == 3:
                    if array[0][0][0] == True or array[0][0][0] == False:
                        array = array * 255
                        img10 = array.astype(np.uint8)
                        array = np.array(img10)
                text = pytesseract.image_to_string(array)
                v = self.find_text(text)
                if v:
                    break
                else:
                    gaussianBlur = cv2.GaussianBlur(array, (5, 5), cv2.BORDER_DEFAULT)
                    text = pytesseract.image_to_string(gaussianBlur)
                    v = self.find_text(text)
                    if v:
                        break
                    else:
                        pass
            except EOFError:
                u = 0
                break
        return u

    def Extract_and_Mask_UIDs(self, image_path):
        img = cv2.imread(self.image_processing(image_path=image_path))
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        rotations = [
            [gray, 1],
            [cv2.rotate(gray, cv2.ROTATE_90_COUNTERCLOCKWISE), 2],
            [cv2.rotate(gray, cv2.ROTATE_180), 3],
            [cv2.rotate(gray, cv2.ROTATE_90_CLOCKWISE), 4],
            [cv2.GaussianBlur(gray, (5, 5), 0), 1],
            [cv2.GaussianBlur(cv2.rotate(gray, cv2.ROTATE_90_COUNTERCLOCKWISE), (5, 5), 0), 2],
            [cv2.GaussianBlur(cv2.rotate(gray, cv2.ROTATE_180), (5, 5), 0), 3],
            [cv2.GaussianBlur(cv2.rotate(gray, cv2.ROTATE_90_CLOCKWISE), (5, 5), 0), 4]
        ]
        
        settings = ('-l eng --oem 3 --psm 11')
        for rotation in rotations:
            cv2.imwrite('rotated_grayscale.png', rotation[0])
            bounding_boxes = pytesseract.image_to_boxes(Image.open('rotated_grayscale.png'), config=settings).split(" 0\n")
            possible_UIDs = self.Regex_Search(bounding_boxes)
            if len(possible_UIDs) == 0:
                continue
            else:
                masked_img = self.Mask_UIDs(image_path, possible_UIDs, bounding_boxes, rotation[1])
                aadhar_data = aadhar_text(pytesseract.image_to_string(Image.open('rotated_grayscale.png'), lang='eng')).adhaar_read_data()
                return masked_img, possible_UIDs, aadhar_data

        return None, None, None

    def mask_aadhar(self):
        input_path = self.image_file_path
        k = 0
        masked_img = None
        if input_path.split('.')[-1] == "pdf":
            pages = pdf2image.convert_from_path(input_path, 300)
            for i in pages:
                i.save(input_path.split('/')[-1].split('.')[0] + ".jpg", 'JPEG')
                k += 1
                flag = self.addhar_check(input_path.split('/')[-1].split('.')[0] + ".jpg")
                if flag != 0:
                    masked_img, possible_UIDs, aadhar_data = self.Extract_and_Mask_UIDs(input_path.split('/')[-1].split('.')[0] + ".jpg")
                    if masked_img is not None and input_path.split('.')[-1] == "pdf":
                        pdf_path = masked_img.split('/')[-1].split('.')[0] + ".pdf"
                    with Image.open(masked_img) as image:
                        pdf_bytes = img2pdf.convert(image.filename)
                        with open(pdf_path, "wb") as file:
                            file.write(pdf_bytes)
                    print('Aadhar data:', aadhar_data)
                    self.merger(input_path, pdf_path, k - 1, 0)
                    os.remove('newfile.pdf')
                    os.remove('rotated_grayscale.png')
                    os.remove(input_path.split('/')[-1].split('.')[0] + "_processed.jpg")
                    break

        elif input_path.split('.')[-1] == "TIF":
            x = Image.open(input_path)
            page_no = self.addhar_check(input_path)
            y = img2pdf.convert(x.filename)
            file = open("1" + ".pdf", "wb")
            file.write(y)
            x.close()
            file.close()
            p = pdf2image.convert_from_path(y, 300)
            p[page_no - 1].save('dup.jpg', 'JPEG')
            masked_img, possible_UIDs, aadhar_data = self.Extract_and_Mask_UIDs('dup.jpg')
            print(masked_img)

        else:
            masked_img, possible_UIDs, aadhar_data = self.Extract_and_Mask_UIDs(input_path)
            pdf_path = masked_img.split('/')[-1].split('.')[0] + ".pdf"
            pdf_bytes = img2pdf.convert(masked_img)
            with open(pdf_path, "wb") as file:
                file.write(pdf_bytes)
            print('Aadhar data:', aadhar_data)
            self.merger(input_path, pdf_path, 0, 0)
            os.remove('newfile.pdf')
            os.remove('rotated_grayscale.png')
            os.remove(input_path.split('/')[-1].split('.')[0] + "_processed.jpg")

    def merger(self, input_file, output_file, start_page, end_page):
        pdf_writer = PdfWriter()
        with open(input_file, "rb") as input_pdf:
            reader = PdfReader(input_pdf)
            for page_num in range(start_page, end_page):
                pdf_writer.add_page(reader.pages[page_num])
            with open(output_file, "wb") as output_pdf:
                pdf_writer.write(output_pdf)