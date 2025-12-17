import requests
import json
import os
from tqdm import tqdm
from openai import OpenAI

import fitz  # PyMuPDF
from PIL import Image
import io
import base64

from constants import *
# from qwen_call import *

def pdf_to_base64(pdf_path):

    pdf_document = fitz.open(pdf_path)
    images = []
    
    try:
        # Full PDF to Base64
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)

        total_width = max(img.width for img in images)
        total_height = sum(img.height for img in images)
        merged_image = Image.new("RGB", (total_width, total_height))
        y_offset = 0
        for img in images:
            merged_image.paste(img, (0, y_offset))
            y_offset += img.height

        buffered = io.BytesIO()
        merged_image.save(buffered, format="PNG")
        buffered.seek(0)

        base64_image = base64.b64encode(buffered.read()).decode('utf-8')

        return base64_image

    except Exception as e:
        print(f"Error in pdf_to_base64：{e}")
        # Replace with blank 1x1 square
        empty_image = Image.new("RGB", (1, 1), color=(255, 255, 255))
        buffered = io.BytesIO()
        empty_image.save(buffered, format="PNG")
        buffered.seek(0)
        
        base64_empty_image = base64.b64encode(buffered.read()).decode('utf-8')
        
        return base64_empty_image

    finally:
        pdf_document.close()

def bbox_to_base64(pdf_path, bbox_list):

    pdf_document = fitz.open(pdf_path)
    images = []

    try:
        # Crop specified regions and splice them vertically
        for bbox in bbox_list:
            page_num = bbox['page'] - 1
            crop_range = [bbox['range'][0]/2,bbox['range'][1]/2,bbox['range'][2]/2,bbox['range'][3]/2]

            # Fetch the specified page
            if page_num < 0 or page_num >= len(pdf_document):
                raise ValueError(f"Page index {page_num} exceeds the exact length {len(pdf_document)}")
            page = pdf_document[page_num]

            # Crop the specified area
            pix = page.get_pixmap(clip=crop_range)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)

        if not images:
            raise ValueError("No specified regions")

        # Splice results
        total_width = max(img.width for img in images)
        total_height = sum(img.height for img in images)
        merged_image = Image.new("RGB", (total_width, total_height))

        y_offset = 0
        for img in images:
            merged_image.paste(img, (0, y_offset))
            y_offset += img.height


        buffered = io.BytesIO()
        merged_image.save(buffered, format="PNG")
        buffered.seek(0)

        base64_image = base64.b64encode(buffered.read()).decode('utf-8')

        return base64_image

    except Exception as e:
        # Replace with blank 1x1 square
        print(f"!!! Error in bbox_to_base64: {e}")  # <--- 添加这一行
        empty_image = Image.new("RGB", (1, 1), color=(255, 255, 255))
        buffered = io.BytesIO()
        empty_image.save(buffered, format="PNG")
        buffered.seek(0)
        
        base64_empty_image = base64.b64encode(buffered.read()).decode('utf-8')
        
        return base64_empty_image

    finally:
        pdf_document.close()

def bbox_to_base64_2(pdf_path, bbox_list):

    pdf_document = fitz.open(pdf_path)
    images = []

    try:
        # Crop specified regions and splice them by relative location relations
        page_bboxes = {}
        for bbox in bbox_list:
            page_num = bbox['page'] - 1
            crop_range = [bbox['range'][0]/2,bbox['range'][1]/2,bbox['range'][2]/2,bbox['range'][3]/2]
            if page_num not in page_bboxes:
                page_bboxes[page_num] = []
            page_bboxes[page_num].append(crop_range)

        for page_num, bboxes in page_bboxes.items():
            # Fetch the specified page
            if page_num < 0 or page_num >= len(pdf_document):
                raise ValueError(f"Page index {page_num} exceeds the exact length {len(pdf_document)}")
            page = pdf_document[page_num]
            page_width, page_height = int(page.rect.width), int(page.rect.height)

            # Create a blank page with the same size
            canvas = Image.new("RGB", (page_width, page_height), color=(255, 255, 255))

            # Initial the overall bbox
            min_x, min_y = page_width, page_height
            max_x, max_y = 0, 0

            # Crop the specified area and paste it to the corresponding position
            for crop_range in bboxes:
                pix = page.get_pixmap(clip=crop_range)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                x0, y0, x1, y1 = map(int, crop_range)
                canvas.paste(img, (x0, y0))

                # Update the overall bbox
                min_x = min(min_x, x0)
                min_y = min(min_y, y0)
                max_x = max(max_x, x1)
                max_y = max(max_y, y1)

            # Crop the overall bbox in the page
            if min_x < max_x and min_y < max_y:
                canvas = canvas.crop((min_x, min_y, max_x, max_y))
            images.append(canvas)

        if not images:
            raise ValueError("No specified regions")

        # Splice pages
        total_width = max(img.width for img in images)
        total_height = sum(img.height for img in images)
        merged_image = Image.new("RGB", (total_width, total_height))
        
        y_offset = 0
        for img in images:
            merged_image.paste(img, (0, y_offset))
            y_offset += img.height

        buffered = io.BytesIO()
        merged_image.save(buffered, format="PNG")
        buffered.seek(0)

        base64_image = base64.b64encode(buffered.read()).decode('utf-8')

        return base64_image

    except Exception as e:
        # Replace with blank 1x1 square
        empty_image = Image.new("RGB", (1, 1), color=(255, 255, 255))
        buffered = io.BytesIO()
        empty_image.save(buffered, format="PNG")
        buffered.seek(0)
        
        base64_empty_image = base64.b64encode(buffered.read()).decode('utf-8')
        
        return base64_empty_image

    finally:
        pdf_document.close()

def gpt_generate(prompt, key=API_KEY, url=API_URL, base_model = MODEL):
    # Support Local Model
    if base_model == 'qwen-vl-local':
        print(f"[Model Call] Using Local Model: {base_model}")
        from qwen_call import call_qwen_vl_textonly, ensure_model_loaded
        ensure_model_loaded()
        return call_qwen_vl_textonly(prompt)

    # Call LLM
    print(f"[Model Call] Using Remote API: {base_model} at {url}")
    client = OpenAI(
        base_url=url,
        api_key=key
    )
    res = ""
    cnt = 0
    if len(prompt) > 100000:
        prompt = prompt[0:100000]

    while cnt < 100:
        try:
            response = client.chat.completions.create(
                model=base_model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature = 1
            )
            res = response.choices[0].message.content
            return res

        except Exception as e:
            cnt += 1
            print(f"LLM Error: {e}. Try for time {cnt}！")
            import time; time.sleep(0.1)

    return res
    
def gpt_generate_pdf(base64_image, prompt, key=API_KEY, url=API_URL, base_model = MODEL):
    # Support Local Model
    if base_model == 'qwen-vl-local':
        print(f"[Model Call] Using Local Model (Vision): {base_model}")
        from qwen_call import call_qwen_vl, ensure_model_loaded
        ensure_model_loaded()
        return call_qwen_vl(prompt, base64_image)

    # Call MLLM
    print(f"[Model Call] Using Remote API (Vision): {base_model} at {url}")
    client = OpenAI(
        base_url=url,
        api_key=key
    )
    res = ""
    cnt = 0
    if len(prompt) > 100000:
        prompt = prompt[0:100000]

    while cnt < 50:
        try:
            response = client.chat.completions.create(
                model=base_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                temperature = 1
            )
            res = response.choices[0].message.content
            return res

        except Exception as e:
            cnt += 1
            print(f"MLLM Error: {e}. Try for time {cnt}！")
            import time; time.sleep(0.1)

    return res