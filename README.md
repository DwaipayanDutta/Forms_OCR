# 🆔 Document Extractor

A Python application that utilizes [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) to extract Driving License numbers, PAN numbers, and EPIC numbers from images and PDF documents. This tool is designed for easy identification and extraction of important document numbers.

## 📦 Features

- **Extract Driving License Numbers**: Identify and extract driving license numbers from images or PDFs.
- **Extract PAN Numbers**: Extract PAN (Permanent Account Number) from various document formats.
- **Extract EPIC Numbers**: Retrieve EPIC (Electors Photo Identity Card) numbers from voter ID cards.

## ⚙️ Installation

### Prerequisites

Make sure you have Python installed on your machine. You can download it from [python.org](https://www.python.org/downloads/).

### Install Required Libraries
Make sure you have pip installed and use it to install the required libraries:
```
pip install paddleocr pymupdf paddlepaddle
```
If you're using a GPU, you can install the GPU version of PaddlePaddle:
```
pip install paddlepaddle-gpu
```
Optionally, you can install the image handling library if needed:
```
pip install pdf2image
```
**View Results**: The extracted numbers will be printed in the console.

## 📄 Example Output
When you run the script with a valid image or PDF containing identification documents, you should see output similar to:\
Driving License Numbers: ['DL123456789012']\
PAN Numbers: ['ABCDE1234F']\
EPIC Numbers: ['ABC1234567']

## 🛠️ Contributing
Contributions are welcome! Please feel free to submit a pull request or open an issue for any suggestions or improvements.
## 📜 License
This project is licensed under the MIT License - see the [LICENSE](https://github.com/DwaipayanDutta/Forms_OCR/blob/main/LICENSE.md) file for details.
## 🤝 Acknowledgments
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) for providing powerful OCR capabilities.
- [PyMuPDF](https://pymupdf.readthedocs.io/en/latest/) for handling PDF files.

