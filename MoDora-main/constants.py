import os

DELIMITER = "################"

######## Edit This
BASE_DIR = "/home/yukai/project/MoDora/datasets/MMDA" # The path to the dataset
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(PROJECT_ROOT, "cache") # The path to store the components and trees
LOG_DIR = os.path.join(PROJECT_ROOT, "log") # The path to store logs
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output") #The path to store execution results
EVALUATION_DIR = os.path.join(PROJECT_ROOT, "evaluation") # The path to store evaluation results
ENABLE_CACHE = False # False:complete test / True:starting from cache
API_KEY = "sk-qdmS5JNk5fLkBX2FPt0PIscJQRNhn3Ootv98deofA7Uzpaqz"
API_URL = "https://api.aiaiapi.com/v1"
MODEL = "qwen-vl-local" # qwen-vl-local or gemini-2.5-flash
VL_MODEL_PATH = "/home/yukai/project/modora-frontend/models/Qwen3-VL-8B-Instruct"
EM_MODEL_PATH = "/home/yukai/project/modora-frontend/models/Qwen3-Embedding-8B"
LAYOUT_MODEL = "paddle" # "paddle" or "gemini"








