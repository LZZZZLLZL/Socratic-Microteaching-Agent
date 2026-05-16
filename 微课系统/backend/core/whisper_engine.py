import whisper
import torch
import os

class TranscriptionEngine:
    def __init__(self):
        # 1. 自动检测 3070 Ti 的 CUDA 环境
        # 既然你已经跑通了，这里会输出：🚀 Whisper 引擎已就绪 | 运行设备: cuda
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[Whisper] 引擎已就绪 | 运行设备: {self.device}")

        # 2. 加载模型 
        # 你有 3070 Ti，如果追求极致准确度，可以把 "base" 换成 "small" (约 460MB 显存)
        # 目前建议先用 "base"，它的速度快得惊人
        self.model = whisper.load_model("base", device=self.device)
        
        # base 模型显存占用很小（~140MB），FP32 全精度运行兼容性最好。
        # CUDA 设备已能提供足够的 GPU 加速，无需 FP16 半精度。

    def transcribe(self, file_path: str):
        """
        利用 3070 Ti 进行语音转文字
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"找不到音频文件: {file_path}")

        print(f"[Whisper] GPU 加速转写中: {os.path.basename(file_path)}")

        # 4. 执行转写
        # language="zh": 强制中文，免去自动检测语言的耗时
        # fp16=False: 模型为 FP32 精度，与输入类型保持一致避免 dtype 不匹配
        result = self.model.transcribe(
            file_path,
            fp16=False,
            language="zh"
        )
        
        return result["text"].strip()

# 实例化，方便 main.py 直接调用
transcriber = TranscriptionEngine()