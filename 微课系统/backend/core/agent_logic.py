import os
from openai import OpenAI
from dotenv import load_dotenv

from core.runtime_config import runtime_config

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
        # API Key 缺失时不再直接抛异常——否则整个后端（含模型监测、
        # 视频转写、姿态分析等本地能力）都无法启动。
        #
        # 重要：这里**不再缓存 client**。API 配置可以通过前端界面在运行时修改，
        # 因此每次调用都重新读取配置并按需构建客户端，改完即生效、
        # 无需重启后端。
        self._client_cache = None
        self._client_cache_key = None

        if not runtime_config.configured:
            print("[Agent] 未配置 API Key —— 对话与点评功能不可用，"
                  "本地模型能力（转写 / 姿态分析 / 课标检索）不受影响")

        # 内存中保存对话历史: {session_id: [messages]}
        self.sessions = {}
        # 存储 session 元数据（教态数据等，用户问及时再注入）
        self.sessions_meta = {}

    # ------------------------------------------------------------------
    # 客户端构建（运行时可变）
    # ------------------------------------------------------------------
    def _get_client(self):
        """
        按当前运行时配置构建 OpenAI 客户端。

        以 (api_key, base_url) 作为缓存键，配置未变时复用连接；
        配置变更后自动重建，从而实现「改完即生效」。
        """
        api_key = runtime_config.api_key
        base_url = runtime_config.base_url

        if not runtime_config.is_valid_key(api_key):
            return None

        cache_key = (api_key, base_url)
        if self._client_cache is not None and self._client_cache_key == cache_key:
            return self._client_cache

        self._client_cache = OpenAI(api_key=api_key, base_url=base_url)
        self._client_cache_key = cache_key
        return self._client_cache

    @property
    def api_key_configured(self) -> bool:
        """当前是否已配置可用的 API Key（供状态接口查询）"""
        return runtime_config.configured

    def _require_client(self):
        """在需要调用大模型时校验凭证，缺失则给出明确提示"""
        client = self._get_client()
        if client is None:
            raise RuntimeError(
                "尚未配置 API Key。请在页面「完整模式 → API 设置」中填写，"
                "或写入 backend/.env 后重启后端。"
                "（快速预览模式无需 API Key，可直接体验完整流程）"
            )
        return client

    def _model_name(self) -> str:
        """当前使用的模型名"""
        return runtime_config.model

    def _get_session(self, session_id: str):
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        return self.sessions[session_id]

    def analyze_teaching(self, text: str):
        """一次性分析（向后兼容）"""
        response = self._require_client().chat.completions.create(
            model=self._model_name(),
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
        response = self._require_client().chat.completions.create(
            model=self._model_name(),
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

        response = self._require_client().chat.completions.create(
            model=self._model_name(),
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

    def get_scoring_card(self, teaching_content: str) -> dict:
        """
        让 DeepSeek 对教学表现进行多维度打分，返回结构化数据
        """
        prompt = f"""请基于以下教学语言实录，对这位师范生进行多维度评分。

【教学语言实录】
{teaching_content}

请从以下 6 个维度进行评分（百分制），每个维度给出一句话简评：

1. 教学逻辑 —— 内容组织是否清晰、层次是否分明
2. 内容准确性 —— 知识表达是否准确、有无错误
3. 互动设计 —— 是否有启发式引导、提问设计
4. 语言表达 —— 语言是否流畅、节奏把控如何
5. 内容深度 —— 是否深入浅出、重点是否突出
6. 教学设计 —— 导入-讲解-总结环节是否完整

请严格按以下 JSON 格式返回（不要加任何其他文字）：

{{"scores":[{{"name":"教学逻辑","score":85,"comment":"层次清晰，导入→讲解→总结脉络完整"}},{{"name":"内容准确性","score":90,"comment":"无知识性错误，概念表述规范"}},{{"name":"互动设计","score":65,"comment":"缺少启发式提问，互动环节设计不足"}},{{"name":"语言表达","score":78,"comment":"语速适中，但存在少量口头禅"}},{{"name":"内容深度","score":82,"comment":"重点较为突出，难点突破有方"}},{{"name":"教学设计","score":80,"comment":"环节基本完整，但导入稍显平淡"}}]}}"""

        try:
            response = self._require_client().chat.completions.create(
                model=self._model_name(),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1024
            )
            raw = response.choices[0].message.content.strip()
            # 提取 JSON（可能被 ```json 包裹）
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            import json
            return json.loads(raw)
        except Exception as e:
            print(f"[Agent] 评分卡生成失败: {e}")
            return {"scores": []}

    def clear_session(self, session_id: str):
        """清除指定 session 的对话历史"""
        self.sessions.pop(session_id, None)
        self.sessions_meta.pop(session_id, None)


# 实例化
ai_assistant = SocraticAgent()
