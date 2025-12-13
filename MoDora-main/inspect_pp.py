from paddleocr import PPStructureV3
import numpy as np

pp = PPStructureV3(device="cpu") # Use CPU for quick check
img = np.zeros((100, 100, 3), dtype=np.uint8) # Dummy image
try:
    res = next(pp.predict_iter(img))
    print("Result keys:", res.keys())
    # print("Result content:", res) 
except Exception as e:
    print("Error:", e)
