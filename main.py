# Kill process using required port
# sudo lsof -i:8000
# kill -9 $PID  //to forcefully kill the port

from fastapi import FastAPI, Depends, UploadFile
from fastapi.openapi.models import APIKey
from auth import api_key_auth
from invoice import Invoice
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()


@app.get("/invoice/{query}")
async def read_item(query, api_key: APIKey = Depends(api_key_auth)):
    # return await amz.scrapedata(query)
    return 'test'


@app.post("/parse-invoice")
def upload(file: UploadFile):
    try:
        print(file.filename)
        # contents = file.file.read()
        inv = Invoice(file)
        result = inv.parse_invoice()
        return result

    except Exception as e:
        print(e)
        return {"message": "There was an error uploading the file"}
    finally:
        file.file.close()

    return {"message": f"Successfully uploaded {file.filename}"}
