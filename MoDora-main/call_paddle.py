from pathlib import Path
from paddleocr import PPStructureV3
import paddle

paddle_pipeline = PPStructureV3(
        device="gpu:2",
        # text_recognition_model_name = "en_PP-OCRv4_mobile_rec" # For ALL English test
    )

def paddle_generate(input_file, output_path):
    
    output = paddle_pipeline.predict_iter(input=input_file, use_table_recognition=True)
    for res in output:
        res.save_to_json(save_path=output_path)
        #res.save_to_img(save_path=output_path) # Visualize OCR results

def main():
    paddle_generate()

if __name__ == "__main__":
    main()