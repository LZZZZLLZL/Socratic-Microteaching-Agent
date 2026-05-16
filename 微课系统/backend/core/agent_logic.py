import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# 苏格拉底导师的系统人格
TUTOR_SYSTEM_PROMPT = """
你是一位资深师范生实训导师，精通苏格拉底式教学法（Socratic Method）。

## 核心原则
1. **绝不直接给答案**。永远用提问引导对方自己发现问题。
2. **从具体细节切入**。先指出你观察到的具体教学行为，再追问。
3. **由浅入深**。先问"是什么"，再问"为什么"，最后问"还能怎么改进"。
4. **适时引用课标**。当讨论涉及课程标准要求时，自然地引用相关条目。
5. **保持温和专业的语气**。多用"你觉得……？""如果换一种方式……会怎样？""你有没有注意到……？"。
6. **教学内容绝对优先，这是不可逾越的铁律**。你的分析必须始终以**教学语言内容（语音转写文稿）为核心素材**来展开讨论。**除非用户自己主动问及教态问题，否则整场对话不得提及任何肢体语言、手势、站位、背对等教态内容**。你收到的教态数据仅用于内部参考，不应出现在输出中。

## 对话节奏
- 每轮只问1-2个问题，不要一股脑全抛出来
- 根据对方的回答决定追问方向
- 当对方说出有价值的反思时，给予肯定再深入
- 不要急于覆盖所有话题，一次深入一个点
"""

INITIAL_ANALYSIS_PROMPT = """
你刚刚分析了一位师范生的教学视频。以下是这位师范生的教学语言内容（这是你分析的核心依据）：

【教学语言实录】
{teaching_content}

相关课标依据：
{standards_text}

**请注意：你收到的教态数据仅作为后台记录，不得在分析中提及。第一轮及后续对话中，除非用户主动问起，否则绝对不讨论任何肢体语言、手势、站位、背对等内容。**

请基于以上教学语言内容做两件事：
1. 先用一段话简要总结这位师范生的教学表现（优点 + 待改进），**仅从教学内容维度评价**：
   - 教学逻辑是否清晰
   - 内容组织是否合理
   - 知识表达是否准确、流畅
   - 是否有启发式引导意识
2. 然后提出第一个苏格拉底式引导问题，引导 ta 自己反思教学内容上最需要改进的那个点

注意：语气要像一位温和的导师，先肯定再引导，不要居高临下。
"""


class SocraticAgent:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )
        # 内存中保存对话历史: {session_id: [messages]}
        self.sessions = {}
        # 存储 session 元数据（教态数据等，用户问及时再注入）
        self.sessions_meta = {}

    def _get_session(self, session_id: str):
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        return self.sessions[session_id]

    def analyze_teaching(self, text: str):
        """一次性分析（向后兼容）"""
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": TUTOR_SYSTEM_PROMPT},
                {"role": "user", "content": f"这是我的教学片段文稿，请进行引导式评价：\n{text}"}
            ],
            stream=True
        )
        return response

    def analyze_with_rag(self, multimodal_context: str, standards: list):
        """基于RAG的一次性分析（向后兼容）"""
        standards_text = "\n".join(f"- {s}" for s in standards) if standards else "无匹配课标"
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": TUTOR_SYSTEM_PROMPT},
                {"role": "user", "content": INITIAL_ANALYSIS_PROMPT.format(
                    teaching_content=multimodal_context,
                    standards_text=standards_text
                )}
            ],
            stream=True,
            temperature=0.7
        )
        return response

    def init_chat_session(self, session_id: str, teaching_content: str, gesture_data: str, standards: list):
        """初始化一个对话 session，把教学内容和教态数据分开存储"""
        standards_text = "\n".join(f"- {s}" for s in standards) if standards else "无匹配课标"
        session = self._get_session(session_id)
        # 清空旧历史
        session.clear()
        session.append({"role": "system", "content": TUTOR_SYSTEM_PROMPT})
        session.append({"role": "user", "content": INITIAL_ANALYSIS_PROMPT.format(
            teaching_content=teaching_content,
            standards_text=standards_text
        )})
        # 教态数据存入 session 元数据，后续用户问及时再注入
        meta = self.sessions_meta.setdefault(session_id, {})
        meta["gesture_data"] = gesture_data

    def chat_stream(self, session_id: str, user_message: str = None):
        """
        多轮对话 SSE 流式返回。
        首次调用时 user_message=None，返回 AI 的初始点评。
        后续调用传入 user_message 为师范生的回复。
        """
        session = self._get_session(session_id)
        if not session or (len(session) <= 1 and not user_message):
            return None  # session 未初始化

        if user_message:
            # 检测用户是否主动问及教态/手势/肢体语言
            gesture_keywords = ["手势", "教态", "肢体", "站位", "背对", "动作", "姿势", "体态",
                                "手", "站姿", "走动", "位移", "眼神", "表情"]
            meta = self.sessions_meta.get(session_id, {})
            if meta.get("gesture_data") and any(kw in user_message for kw in gesture_keywords):
                # 用户主动问教态了，注入教态数据
                gesture_block = f"\n\n（用户问及教态，以下为教态分析数据供参考）\n{meta['gesture_data']}"
                session.append({"role": "user", "content": user_message + gesture_block})
            else:
                session.append({"role": "user", "content": user_message})

        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=session,
            stream=True,
            temperature=0.7
        )

        # 收集完整回复并存入历史
        full_content = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_content += content
                yield content

        session.append({"role": "assistant", "content": full_content})

    def clear_session(self, session_id: str):
        """清除指定 session 的对话历史"""
        self.sessions.pop(session_id, None)
        self.sessions_meta.pop(session_id, None)


# 实例化
ai_assistant = SocraticAgent()
