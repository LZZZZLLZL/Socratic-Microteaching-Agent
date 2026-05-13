import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class SocraticAgent:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )

    def analyze_teaching(self, text: str):
        # 这是灵魂：苏格拉底式 Prompt
        system_prompt = """
        你是一位资深的师范生实训导师，擅长苏格拉底式教学法。
        你的任务是分析用户的教学转写文稿。
        要求：
        1. 不要直接给出改进答案，而是针对文稿中的逻辑漏洞或教学互动不足点提出启发式问题。
        2. 语气要专业且温和，多使用“你觉得...”、“如果...会怎样？”的句式。
        3. 请使用简体中文。
        """
        
        response = self.client.chat.completions.create(
            model="deepseek-chat",  # 或者用 deepseek-reasoner (R1)
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"这是我的教学片段文稿，请进行引导式评价：\n{text}"}
            ],
            stream=True  # 开启流式传输，提升前端体验
        )
        return response

# 实例化
ai_assistant = SocraticAgent()