import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from constants import LOG_DIR

# 确保日志目录存在
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

class MoDoraLogger:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MoDoraLogger, cls).__new__(cls)
            cls._instance._setup_main_logger()
        return cls._instance

    def _setup_main_logger(self):
        """配置主应用日志"""
        self.logger = logging.getLogger("MoDora")
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            # 日志格式：时间 - 模块名 - 级别 - 信息
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

            # 滚动文件处理器：最大10MB，保留5个备份
            app_log_path = os.path.join(LOG_DIR, "app.log")
            file_handler = RotatingFileHandler(
                app_log_path, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

            # 控制台处理器
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def get_logger(self):
        return self.logger

    def get_request_logger(self, request_id):
        """
        为特定请求创建专用 Logger。
        用于记录推理过程，输出到独立文件供前端展示。
        """
        req_logger = logging.getLogger(f"Request-{request_id}")
        req_logger.setLevel(logging.INFO)
        
        log_file = os.path.join(LOG_DIR, f"api_req_{request_id}.log")
        
        # 请求日志通常只记录推理内容，使用纯文本格式
        formatter = logging.Formatter('%(message)s')
        
        # 'w' 模式确保每个 Request ID 对应的日志是全新的
        file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        file_handler.setFormatter(formatter)
        
        # 清除旧的 Handler，防止重复记录
        req_logger.handlers = []
        req_logger.addHandler(file_handler)
        
        return req_logger

# 导出单例对象和常用 logger
modora_logger = MoDoraLogger()
logger = modora_logger.get_logger()
