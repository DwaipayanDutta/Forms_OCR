import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from masking import AadharMask


app = FastAPI(title="Aadhaar Masking API", version="1.0")

masker = AadharMask()
UPLOAD_DIR = "temp"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/mask-aadhar")
async def mask_aadhar(file: UploadFile = File(...)):
    """Upload an image or PDF and get masked Base64 output."""
    try:
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in [".pdf", ".png", ".jpg", ".jpeg"]:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        temp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{file_ext}")
        with open(temp_path, "wb") as f:
            f.write(await file.read())

        result = masker.mask_aadhar_final(temp_path)
        os.remove(temp_path)

        return JSONResponse(content=result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
