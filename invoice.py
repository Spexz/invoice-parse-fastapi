# importing os module
import os
import fitz
import numpy as np
from paddleocr import PaddleOCR
import json
import pathlib
from fastapi import UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from openai import OpenAI


class Invoice():
    prompt = """
    Create a table from the given Invoice Text of the invoice as a JSON object.
    The given image is the invoice.
    Return the created table as a JSON object.
    No descriptions and explanations. Return only raw JSON object without markdown. No markdown format.
    The required properties in JSON object are as follows.

    [Properties in JSON object]
    "invoiceTitle": "title of invoice"
    "invoiceDate": "date of invoice"
    "invoiceNumber": "number of the invoice"
    "invoiceDestinationName": "Name of destination on invoice"
    "invoiceDestinationAddress": "address of the destination of invoice"
    "paymentMethod": "a partial of the credit card used to make the payment. This could include the credit card processor"
    "totalCost": "total amount of all costs"
    "grandTotal": "total amount of all costs + taxes"
    "taxes": "total amount of taxes"
    "invoiceItems": "Array of invoice items. This is an array of objects of the invoice items."

    [Properties of the "invoiceItems" object]
    "description": "title or description of the invoice item"
    "quantity": "the quantity of the invoice item"
    "unitCost": "the unit cost of the invoice item"
    "totalCost": "the total cost of the invoice item"

    If the required information is not found set "no value".
    Return only raw JSON object without markdown. No markdown format. No markdown tags.

    [Invoice Text]

    """

    # Define the system message
    system_msg = 'You are a helpful assistant who understands and parses invoices from text to JSON format.'

    def __init__(self, file: UploadFile):
        use_gpu = False
        self.ocr = PaddleOCR(lang='en', use_angle_cls=True, use_gpu=use_gpu,
                             show_log=False)
        self.file = file

        # assigning API KEY to initialize openai environment
        # openai.api_key = gpt_api_key
        gpt_api_key = os.getenv("OPENAI_KEY")
        self.gpt_client = OpenAI(
            # defaults to os.environ.get("OPENAI_API_KEY")
            api_key=gpt_api_key,
        )

    def parse_invoice(self):
        # name = pathlib.Path(self.file.filename).stem
        nameWithExt = pathlib.Path(self.file.filename).name

        bytes = self.file.file.read()
        doc = fitz.open(stream=bytes)

        zoom = 4
        mat = fitz.Matrix(zoom, zoom)

        final_text = ''

        for j in range(0, len(doc)):
            page = doc[j]
            pix = page.get_pixmap(matrix=mat, annots=True)

            image = self.pix2np(pix)

            text = self.image_to_text(image)
            final_text = final_text + text + '\n'

            final_text = self.remove_non_ascii(final_text)

        print(final_text)

        # Define the user message
        user_msg = self.prompt + final_text

        # Create a dataset using GPT
        response = self.gpt_client.chat.completions.create(model="gpt-3.5-turbo",
                                                           messages=[{"role": "system", "content": self.system_msg},
                                                                     {"role": "user", "content": user_msg}])
        inv_obj = json.loads(response.choices[0].message.content.strip())
        inv_obj["file_name"] = nameWithExt
        inv_obj["invoice_text"] = final_text
        json_compatible_item_data = jsonable_encoder(inv_obj)
        return JSONResponse(content=json_compatible_item_data)

        # return final_text

    def pix2np(self, pix):
        im = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.h, pix.w, pix.n)
        im = np.ascontiguousarray(im[..., [2, 1, 0]])  # rgb to bgr
        return im

    def remove_non_ascii(self, string):
        return string.encode('ascii', errors='ignore').decode()

    def sort_bounding_box(self, data):
        # Sort the elements based on the bottom left y-coordinate
        sorted_data = sorted(data[0], key=lambda x: x[0][3][1])
        # print(sorted_data)

        # Group the elements by line using the bottom left y-coordinate and a tolerance
        tolerance = 20  # You can adjust the tolerance value as needed
        grouped_data = []
        current_line = [sorted_data[0]]

        for i in range(1, len(sorted_data)):
            curr_coords = sorted_data[i][0]
            prev_coords = current_line[-1][0]

            # Check if the current element is in the same line based on the y-coordinate and tolerance
            if abs(curr_coords[3][1] - prev_coords[3][1]) <= tolerance:
                current_line.append(sorted_data[i])
            else:
                grouped_data.append(current_line)
                current_line = [sorted_data[i]]

        # Add the last line to the grouped data
        grouped_data.append(current_line)

        # Sort grouped lines on bottom left x coord so text is order left to right
        sorted_grouped_data = []
        for line in grouped_data:
            sorted_data = sorted(line, key=lambda x: x[0][3][0])
            sorted_grouped_data.append(sorted_data)

        return sorted_grouped_data

    def image_to_text(self, image):
        data = self.ocr.ocr(image, cls=True)

        sorted_data = self.sort_bounding_box(data)

        final_text = ''
        for line in sorted_data:
            ln = ''
            for text_part in line:
                ln = ln + text_part[1][0] + ' '

            final_text = final_text + ln.strip() + '\n'

        final_text = final_text.strip()

        return final_text
