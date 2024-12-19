import cv2
import numpy as np
import numpy
import re
from PIL import Image
import pytesseract
# from ISR.models import RRDN
import pdf2image
import img2pdf
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2 import PdfMerger
import tifftools
import os
from aadhar_read import *
# SR_Model = RRDN(weights='gans')
pytesseract.pytesseract.tesseract_cmd =r'/opt/homebrew/Cellar/tesseract/5.5.0/bin/tesseract'

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
      (9, 8, 7, 6, 5, 4, 3, 2, 1, 0))
     self.permutation_table = (
      (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
      (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
      (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
      (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
      (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
      (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
      (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
      (7, 0, 4, 6, 9, 1, 3, 2, 5, 8))

  @staticmethod
  def find_text(text):
    n=len(text);
    if(n<12):
      return 0;
    for i in range(14,n):
      s=text[i-14:i];
      if(s[4]==" " and s[9]==" "):
        s=s.replace(" ","");
        n1=len(s);
        s1=s[n1-12:n1];
        if(i==125):
          pass;
        if(s1.isnumeric() and len(s1)>=12):
          return 1;
    return 0;
  #-------------------------------------------------------------------------------------------------------#
  def addhar_check(self, file_name):
    img = Image.open(file_name)
    u=0;
    for i in range(25):
      try:
          img.seek(i)
          u=u+1;
          array=numpy.array(img);
          c=len(array.shape);
          if(c==2):
            if(array[0][0]==True or array[0][0]==False):
              array=array*255;
              img10 = array.astype(numpy.uint8)
              array=numpy.array(img10)

          elif(c==3):
            if(array[0][0][0]==True or array[0][0][0]==False):
              array=array*255;
              img10 = array.astype(numpy.uint8)
              array=numpy.array(img10)     
          text=pytesseract.image_to_string(array);
          v=self.find_text(text);
          if(v):
                  break;
          else:
                  gaussianBlur = cv2.GaussianBlur(array,(5,5),cv2.BORDER_DEFAULT)
                  text=pytesseract.image_to_string(gaussianBlur);
                  v=self.find_text(text);
                  if(v):
                      break;
                  else:
                      pass;
      except EOFError:
          u=0;
          break
    return u;

  """Split a pdf into multiple pages and merge them all to a single TIF file."""
  @staticmethod
  def pdf2tiff(pdf_path):
  # Store Pdf with convert_from_path function
    images = pdf2image.convert_from_path(pdf_path,300#,poppler_path=r'C:\Program Files\poppler-0.68.0\bin'
                                        )
    
    li=[] 
    for i in range(len(images)):
          # Save pages as images in the pdf
        images[i].save(str(i)+".tif", 'TIFF')
        li.append(str(i)+'.tif')
    tifftools.tiff_merge(li,'final.tif')

  #---------------------------------------------------------------------------------------------------------#
  #----------------------------------------------------------------------------------------------------#
  """Remove the unmasked aadhar page from a pdf file and add a new page of masked aadhar into the pdf file."""
  def merger(self, original,masked,page_no,flag):
    infile = PdfReader(original)
    x=len(infile.pages)
    output = PdfWriter()

    for i in range(x):
      if(i!=page_no):
        p = infile.getPage(i)
        output.addPage(p)

    with open('newfile.pdf', 'wb') as f:
      output.write(f)
    merger = PdfMerger()
    merger.append('newfile.pdf')
    pdf_path = masked.split('\\')[-1].split('.')[0]+".pdf"
    merger.append(masked)
    merger.write(pdf_path)
    merger.close()
    if(flag==1):
      self.pdf2tiff(pdf_path)

  def compute_checksum(self, number):
      """Calculate the Verhoeff checksum over the provided number. The checksum
      is returned as an int. Valid numbers should have a checksum of 0."""
      
      # transform number list
      number = tuple(int(n) for n in reversed(str(number)))
      #print(number)
      
      # calculate checksum
      checksum = 0
      
      for i, n in enumerate(number):
          checksum = self.multiplication_table[checksum][self.permutation_table[i % 8][n]]
      
      #print(checksum)
      return checksum

  #---------------------------------------------------------------------------------------------------------#
  # Search Possible UIDs with Bounding Boxes
  def Regex_Search(self, bounding_boxes):
    possible_UIDs = []
    Result = ""

    for character in range(len(bounding_boxes)):
      if len(bounding_boxes[character])!=0:
        Result += bounding_boxes[character][0]
      else:
        Result += '?'

    matches = [match.span() for match in re.finditer(r'\d{12}',Result)]

    for match in matches :
      UID = int(Result[match[0]:match[1]])
      if self.compute_checksum(UID)==0 and UID%10000!=1947:
        possible_UIDs.append([UID,match[0]])
    possible_UIDs = np.array(possible_UIDs)
    print('No of possible UIDs:',len(possible_UIDs))
    if len(possible_UIDs) == 5:
      possible_UIDs = possible_UIDs[1:4,:]
    return possible_UIDs

  #---------------------------------------------------------------------------------------------------------#
  def Mask_UIDs (self, image_path,possible_UIDs,bounding_boxes,rtype):
    img = cv2.imread(image_path)
    if rtype==2:
      img = cv2.rotate(img,cv2.ROTATE_90_COUNTERCLOCKWISE)
    elif rtype==3:
      img = cv2.rotate(img,cv2.ROTATE_180)
    elif rtype==4:
      img = cv2.rotate(img,cv2.ROTATE_90_CLOCKWISE)
    height = img.shape[0]

    for UID in possible_UIDs:
      digit1 = bounding_boxes[UID[1]].split()
      digit8 = bounding_boxes[UID[1] + 7].split()
      h1 = min(height-int(digit1[4]),height-int(digit8[4]))
      h2 = max(height-int(digit1[2]),height-int(digit8[2]))

      top_left_corner = (int(digit1[1]),h1)
      bottom_right_corner = (int(digit8[3]),h2)
      botton_left_corner=(int(digit1[1]),h2-3)
      thickness=h1-h2
      img = cv2.rectangle(img,top_left_corner,bottom_right_corner,(0,0,0),-1)
      
      
    if rtype==2:
      img = cv2.rotate(img,cv2.ROTATE_90_CLOCKWISE)
    elif rtype==3:
      img = cv2.rotate(img,cv2.ROTATE_180)
    elif rtype==4:
      img = cv2.rotate(img,cv2.ROTATE_90_COUNTERCLOCKWISE)

    file_name = image_path.split('/')[-1].split('.')[0]+"_masked"+"."+image_path.split('.')[-1]
    cv2.imwrite(file_name,img)
    return file_name

  def image_processing(self, image_path):
      img = cv2.imread(image_path)
      rgb_planes = cv2.split(img)
      result_planes = []
      result_norm_planes = []
      for plane in rgb_planes:
          dilated_img = cv2.dilate(plane, np.ones((7,7), np.uint8))
          bg_img = cv2.medianBlur(dilated_img, 21)
          diff_img = 255 - cv2.absdiff(plane, bg_img)
          norm_img = cv2.normalize(diff_img,None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC1)
          result_planes.append(diff_img)
          result_norm_planes.append(norm_img)
      result = cv2.merge(result_planes)
      result_norm = cv2.merge(result_norm_planes)
      cv2.imwrite(image_path.split('/')[-1].split('.')[0]+"_processed.jpg", result_norm)
      return image_path.split('/')[-1].split('.')[0]+"_processed.jpg"

  #---------------------------------------------------------------------------------------------------------#
  def Extract_and_Mask_UIDs (self, image_path):
    img = cv2.imread(self.image_processing(image_path=image_path))
    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    rotations = [[gray,1],
                [cv2.rotate(gray,cv2.ROTATE_90_COUNTERCLOCKWISE),2],
                [cv2.rotate(gray,cv2.ROTATE_180),3],
                [cv2.rotate(gray,cv2.ROTATE_90_CLOCKWISE),4],
                [cv2.GaussianBlur(gray,(5,5),0),1],
                [cv2.GaussianBlur(cv2.rotate(gray,cv2.ROTATE_90_COUNTERCLOCKWISE),(5,5),0),2],
                [cv2.GaussianBlur(cv2.rotate(gray,cv2.ROTATE_180),(5,5),0),3],
                [cv2.GaussianBlur(cv2.rotate(gray,cv2.ROTATE_90_CLOCKWISE),(5,5),0),4]]

    settings = ('-l eng --oem 3 --psm 11')
    for rotation in rotations:
      cv2.imwrite('rotated_grayscale.png',rotation[0])
      bounding_boxes = pytesseract.image_to_boxes(Image.open('rotated_grayscale.png'),config=settings).split(" 0\n")
      possible_UIDs = self.Regex_Search(bounding_boxes)
      if len(possible_UIDs)==0:
        continue
      else:
        masked_img = self.Mask_UIDs (image_path,possible_UIDs,bounding_boxes,rotation[1])
        aadhar_data = aadhar_text(pytesseract.image_to_string(Image.open('rotated_grayscale.png'),lang='eng')).adhaar_read_data()
        return (masked_img,possible_UIDs, aadhar_data)

    return (None, None, None)

  #--------------------------------------------------------------------------------------------------------
  def mask_aadhar(self):
    input_path = self.image_file_path
    k=0
    masked_img = None
    # Path to the Input Image/PDF
    if input_path.split('.')[-1]=="pdf":    
      pages = pdf2image.convert_from_path(input_path, 300)
      for i in pages:
        i.save(input_path.split('/')[-1].split('.')[0]+".jpg", 'JPEG')
        # print("Page No:-"+str(k))
        
        k+=1
        flag=self.addhar_check(input_path.split('/')[-1].split('.')[0]+".jpg")
        # print(flag)
        if(flag!=0):
          masked_img,possible_UIDs, aadhar_data = self.Extract_and_Mask_UIDs(input_path.split('/')[-1].split('.')[0]+".jpg")
          if masked_img!=None and input_path.split('.')[-1]=="pdf" :    
            pdf_path = masked_img.split('/')[-1].split('.')[0]+".pdf"
            print(masked_img)
            # print(pdf_path)
          # Open the image file
          with Image.open(masked_img) as image:
              # Convert the image to PDF bytes
              pdf_bytes = img2pdf.convert(image.filename)
              # Write the PDF bytes to a file
              with open(pdf_path, "wb") as file:
                  file.write(pdf_bytes)
          image.close() 
          file.close()
          print('Aadhar data:', aadhar_data)
          self.merger(input_path,pdf_path,k-1,0)
          os.remove('newfile.pdf')
          os.remove('rotated_grayscale.png')
          os.remove(input_path.split('/')[-1].split('.')[0]+"_processed.jpg")
          break 

    elif input_path.split('.')[-1]=="TIF":
      x=Image.open(input_path)
      page_no=self.addhar_check(input_path)
      y=img2pdf.convert(x.filename)
      # print(type(y))
      file = open("1"+".pdf", "wb")
      dup_img = "1"+".pdf"
      file.write(y)
      x.close()
      file.close()
      p=pdf2image.convert_from_path(y, 300)
      p[page_no-1].save('dup.jpg','JPEG')
      masked_img,possible_UIDs, aadhar_data = self.Extract_and_Mask_UIDs('dup.jpg')
      print(masked_img)
    else:
      masked_img, possible_UIDs, aadhar_data = self.Extract_and_Mask_UIDs(input_path)
      # print(masked_img)
      pdf_path = masked_img.split('/')[-1].split('.')[0]+".pdf"

      # Open the image file
      with Image.open(masked_img) as image:
          # Convert the image to PDF bytes
          pdf_bytes = img2pdf.convert(image.filename)
          # Write the PDF bytes to a file
          with open(pdf_path, "wb") as file:
              file.write(pdf_bytes)
      print('Aadhar data:', aadhar_data)
      os.remove('rotated_grayscale.png')
      os.remove(input_path.split('/')[-1].split('.')[0]+"_processed.jpg")

    if masked_img!=None and input_path.split('.')[-1]=="TIF" :
      print(masked_img)
      image = Image.open(masked_img) 
      pdf_path = masked_img.split('/')[-1].split('.')[0]+".pdf"

      # Open the image file
      with Image.open(masked_img) as image:
          # Convert the image to PDF bytes
          pdf_bytes = img2pdf.convert(image.filename)
          # Write the PDF bytes to a file
          with open(pdf_path, "wb") as file:
              file.write(pdf_bytes)
      image.close() 
      file.close()
      self.merger("1.pdf",pdf_path,page_no-1,1)
      print('Aadhar data:', aadhar_data)
      os.remove('newfile.pdf')
      os.remove('rotated_grayscale.png')
      os.remove(input_path.split('/')[-1].split('.')[0]+"_processed.jpg")

    if masked_img==None:
      s="UID not found!!"
      # continue
    else:
      s="Found UIDs :"+str(possible_UIDs[:,0])
    return s
# Sample
# masking_file(r"Aadhaar.pdf")
