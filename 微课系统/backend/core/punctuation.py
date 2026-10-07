# ==========================================================================
# 学思践悟 — 中文标点还原与识别纠错引擎
#
# 两个独立能力：
#   A. 标点还原 —— Whisper 输出的中文文稿通常几乎没有标点，
#      通过「句子边界识别 + 小句切分 + 停顿利用」三级策略补全标点与断句。
#   B. 同音错字纠正 —— Whisper 常把专业词听成音近字
#      （销量→销售、覆盖→复改、升序→生讯…），按保守白名单纠正。
#
# 设计原则：
#   1. 零依赖、零网络、零 API —— 不消耗任何 token
#   2. 标点还原「只加标点、不改字词」；字词替换仅由纠错表显式负责
#   3. 保守优先：宁可少改，不可错改。纠错必须命中已知音近错误
#   4. 利用 Whisper 分段时间戳，把「长停顿」作为断句的强信号
# ==========================================================================

import re
from typing import Dict, List, Optional, Tuple

# --------------------------------------------------------------------------
# 1. 词汇表
# --------------------------------------------------------------------------

# 句末语气词 —— 这些字出现在位置边界时，几乎必然是一个句子的结束
# 注意：「好」「啊」需额外校验（见 _is_final_particle），避免在
# 「同学好」「技术好」等词语内部误断。
_FINAL_PARTICLES = {"吗", "呢", "吧", "啊", "呀", "嘛", "哦", "噢", "啦", "咯"}
_AMBIGUOUS_PARTICLES = {"好", "了", "的", "是"}
_LOGICAL_CONNECTORS = {"那", "这", "就", "也", "都", "还", "又", "才", "只", "便", "即"}

# 疑问标记词 —— 出现在句中任意位置即倾向于把整句判为疑问句
_INTERROGATIVE_WORDS = (
    "什么", "为什么", "怎么", "怎样", "如何", "哪里", "哪儿", "哪个", "哪些",
    "谁", "多少", "是不是", "对不对", "好不好", "行不行", "能不能",
    "可不可以", "有没有", "是否", "难道", "岂不是", "何必", "多会儿",
)

# 感叹标记
_EXCLAMATION_STARTS = ("太好了", "非常好", "多么", "太棒了", "真棒", "了不起")

# 句子起始词 —— 出现在某位置且其前有内容时，说明这里是新句子的开头
# 注意：只收录多字、无歧义的词。像「好」「那」「来」这类单字词
# 极易在「各位同学好」「那我们」等词组中被误判，一律不收录。
_SENTENCE_STARTERS = (
    "首先", "其次", "再次", "接下来", "随后",
    "那么", "所以", "但是", "不过", "然而", "因此", "于是", "另外",
    "此外", "同时", "总之", "例如", "比如", "换句话说", "也就是说",
    "第一", "第二", "第三", "第四", "下面我们",
)

# 呼语 —— 只作为「句首呼语」处理（后接逗号），不参与句子切分
_ADDRESS_TERMS = (
    "各位同学", "同学们", "各位老师", "老师们", "大家好", "各位",
    "小朋友", "孩子们", "同学", "老师", "大家",
)

# 句中小句切分的连词（前置型：切在它之前）
_CLAUSE_BREAK_BEFORE = (
    "但是", "不过", "然而", "可是", "因为", "由于", "所以", "因此",
    "而且", "并且", "如果", "假如", "虽然", "尽管", "只要", "只有",
    "无论", "不管", "即使", "哪怕", "既然", "一旦", "同时", "另外",
)

# 句中小句切分的连词（后置型：切在它之后）
_CLAUSE_BREAK_AFTER = (
    "首先", "其次", "再次", "然后", "接着", "接下来", "最后",
    "那么", "例如", "比如", "也就是说", "换句话说",
)

# 逐字顺读时，这些字之后是自然的呼吸点（仅在超长小句需要强制切分时使用）
_SOFT_CUT_AFTER = ("的", "了", "是", "在", "有", "和", "与", "对", "把", "被", "会", "能", "就", "也", "都")

# 常见双字词 —— 若断点正好落在这些词的中间，则判定为「切断了词语」
_COMMON_BIGRAMS = {
    "接下", "下来", "来说", "表现", "反映", "信息", "技术", "同学", "老师",
    "我们", "你们", "他们", "这个", "那个", "什么", "怎么", "可以", "需要",
    "数据", "图像", "声音", "方式", "特征", "概念", "定义", "支持", "获取",
    "加工", "存储", "传输", "展示", "所有", "总称", "课后", "思考", "生活",
    "场景", "用到", "分享", "节课", "一起", "基本", "客观", "世界", "各种",
    "事物", "通过", "计算机", "通信", "情况下", "时候", "地方", "东西",
    "问题", "同学", "注意", "一定", "操作", "规范", "非常", "优秀", "智能",
    "人类", "取代", "如何", "共处", "函数", "定义域", "值域", "搞混", "做题",
    "条件", "看清", "计算", "跟着", "继续", "往下", "强调", "一点", "接口",
    "返回", "对象", "字段", "必须", "数学", "语文", "英语", "物理", "化学",
    # 课堂高频词，避免在这些词中间断句
    "相同", "同时", "一举", "首要", "次要", "关系", "效果", "理想",
    "修整", "视角", "结束", "感谢", "评委", "菜品", "菜肴", "风格",
}

# --------------------------------------------------------------------------
# 2. 阈值
# --------------------------------------------------------------------------
PAUSE_STRONG = 0.9     # Whisper 段间停顿 ≥ 该值 → 判定为句末
PAUSE_MEDIUM = 0.5     # Whisper 段间停顿 ≥ 该值 → 可作为小句边界

MIN_SENTENCE_LEN = 8   # 一个句子至少这么长（字），否则不与前句切分
MAX_SENTENCE_LEN = 46  # 句子超过该长度时按标点预算切分
MAX_CLAUSE_LEN = 26    # 小句达到该长度时强制找一个呼吸点插入逗号
HARD_CAP_LEN = 110     # 无任何边界可依时的硬上限（尽量高，避免硬切语义）

# 「句末标点后不该再断」的收尾字：断点落在这些字之前说明句子尚未说完
_INCOMPLETE_TAIL = ("请", "让", "使", "把", "被", "的", "地", "得", "了", "着",
                    "和", "与", "或", "及", "以", "从", "向", "对", "为", "在")

# 已有标点判定
_HAS_PUNCT_RE = re.compile(r"[，。！？；：、,.!?;:]")

# 半角 → 全角标点映射（Whisper 常输出半角逗号/问号，需统一为中文标点）
_HALFWIDTH_MAP = {
    ",": "，",
    "?": "？",
    "!": "！",
    ";": "；",
    ":": "：",
    ".": "。",
}

# 句末标点集合（成句后追加）
_FINAL_PUNCT = "。！？"

# --------------------------------------------------------------------------
# 同音错字纠正表
# --------------------------------------------------------------------------
# Whisper 对中文专业术语极易听成音近字。这里维护一份「保守白名单」：
# 只有整词精确匹配才替换，绝不做模糊匹配，避免误改正常表达。
#
# 条目来源：
#   1. 真实课堂录音中实际观察到的误识别（信息技术 / 编程教学场景）
#   2. 该学科高频术语的音近混淆对
_HOMOPHONE_FIXES: Dict[str, str] = {
    # ── 真实课堂录音中实际出现的错误 ──
    "无时无刻不再": "无时无刻不在",
    "无时无刻不载": "无时无刻不在",
    "带排序": "待排序",
    "代排序": "待排序",
    "降续排序": "降序排序",
    "生讯排序": "升序排序",
    "升讯排序": "升序排序",
    "降讯排序": "降序排序",
    "复改": "覆盖",
    "永续排序": "有序排序",
    "初餐": "出餐",
    "销售": "销量",
    "降续": "降序",
    "生讯": "升序",
    "升讯": "升序",
    "降讯": "降序",

    # ── 编程 / 数据处理常见音近词 ──
    "行数": "函数",
    "涵数": "函数",
    "函授": "函数",
    "参素": "参数",
    "餐数": "参数",
    "遍量": "变量",
    "带码": "代码",
    "编成": "编程",
    "算发": "算法",
    "对像": "对象",
    "数据矿": "数据框",
    "分组冬季": "分组统计",
    "运行接果": "运行结果",
    "派序": "排序",

    # ── 信息技术学科术语 ──
    "信息记术": "信息技术",
    "计算思路": "计算思维",
    "信息素样": "信息素养",
    "课程标尊": "课程标准",
    "人工职能": "人工智能",
}

# 按「错误写法长度」倒序，保证长词优先匹配
# （例如先匹配「无时无刻不再」，再匹配其可能的前缀短词）
_HOMOPHONE_ORDERED: List[Tuple[str, str]] = sorted(
    _HOMOPHONE_FIXES.items(),
    key=lambda kv: len(kv[0]),
    reverse=True,
)

# 出现这些上下文时跳过纠错，避免把正常表达改坏
# 例如谈论餐厅经营时「销售额」是正确表达，不应被改成「销量额」
_HOMOPHONE_SKIP_CONTEXT: Dict[str, Tuple[str, ...]] = {
    "销售": ("销售额", "销售收入", "销售部", "销售员", "销售情况"),
    "行数": ("行数列", "行数值", "行数量"),
    "参素": ("参素数",),
}


class PunctuationRestorer:
    """中文标点还原引擎（纯规则，本地运行）"""

    def __init__(self):
        # 按长度倒序，保证长词优先匹配
        self._starters = sorted(_SENTENCE_STARTERS, key=len, reverse=True)
        self._address = sorted(_ADDRESS_TERMS, key=len, reverse=True)
        self._break_before = sorted(_CLAUSE_BREAK_BEFORE, key=len, reverse=True)
        self._break_after = sorted(_CLAUSE_BREAK_AFTER, key=len, reverse=True)
        self._interrogatives = sorted(_INTERROGATIVE_WORDS, key=len, reverse=True)

    # ==================================================================
    # 公共入口
    # ==================================================================
    def restore(
        self,
        text: str,
        segments: Optional[List[dict]] = None,
        fix_homophones: bool = True,
    ) -> str:
        """
        为中文文本做「同音错字纠正 + 标点还原 + 分段」。

        Args:
            text: 待处理文本（可含换行）
            segments: Whisper 分段 [{"start":, "end":, "text":}, ...]
                      提供时将利用段间停顿时间辅助断句
            fix_homophones: 是否执行同音错字纠正（默认开启）

        Returns:
            纠错并添加标点、按语义分好段的文本

        Note:
            纠错与标点是两个独立阶段：先按白名单纠正已知音近错误，
            再补标点。标点阶段本身仍然「只加标点、不改字词」。
        """
        if not text or not text.strip():
            return text

        # 第零步：同音错字纠正（仅在显式开启时）
        source = self._fix_homophones(text) if fix_homophones else text

        # 第一步：无论标点是否充分，都先规范化半角标点与空格
        normalized = self._normalize(source)

        # 已有充分标点（标点密度 > 每 12 字 1 个）则只做规范化后返回
        if self._punctuation_density(normalized) > 1 / 12:
            return normalized

        if segments:
            sentences = self._sentences_from_segments(segments)
            if sentences:
                return self._finalize(self._format_paragraphs(sentences))

        raw = re.sub(r"\s+", "", normalized)
        if not raw:
            return normalized

        sentences = self._split_sentences(raw)
        sentences = [self._punctuate_clauses(s) for s in sentences]
        sentences = self._rejoin_fragments(sentences)
        return self._finalize(self._format_paragraphs(sentences))

    # ------------------------------------------------------------------
    # 碎句回收
    # ------------------------------------------------------------------
    # 句子切分与「按预算切分」可能产生极短的残句，
    # 例如「水煮鱼虾？」+「饺三鲜面这些菜…」把「虾饺」拦腰截断。
    # 这里把过短的句子并回前一句，避免出现读不通的孤立短句。
    MIN_STANDALONE_SENTENCE = 12

    def _rejoin_fragments(self, sentences: List[str]) -> List[str]:
        """
        把过短的句子与相邻句合并。

        规则：若某句去掉句末标点后短于 MIN_STANDALONE_SENTENCE，
        且它不是整段的第一句，则把它并回前一句（保留前句标点）。
        """
        if len(sentences) <= 1:
            return sentences

        merged: List[str] = [sentences[0]]
        for cur in sentences[1:]:
            core = cur.rstrip(_FINAL_PUNCT)
            prev_core = merged[-1].rstrip(_FINAL_PUNCT)

            if len(core) < self.MIN_STANDALONE_SENTENCE:
                # 碎句：并回前句，前句保持原有句末标点
                if prev_core.endswith(("，", "、", "；", "：")):
                    merged[-1] = prev_core + core + self._pick_final_punct(prev_core + core)
                else:
                    merged[-1] = prev_core + core + merged[-1][-1]
                continue

            # 前句本身过短且不以句末标点收束 → 合并
            if len(prev_core) < 6 and merged[-1][-1] not in _FINAL_PUNCT:
                merged[-1] = merged[-1] + core + self._pick_final_punct(cur)
                continue

            merged.append(cur)

        return merged

    @staticmethod
    def _finalize(text: str) -> str:
        """
        收尾处理：在所有标点都插入完毕后，统一清理非法标点组合。

        必须在标点生成之后调用 —— 切分歧义处产生的「，。」「？？」
        等组合只有到此阶段才可能存在。
        """
        if not text:
            return text
        # 先合并重复，再清理跨标点组合，最后压缩空白
        out = re.sub(r"([，。！？；：、])\1+", r"\1", text)
        out = PunctuationRestorer._cleanup_sequences(out)
        out = re.sub(r"[ \t]+", " ", out)
        out = re.sub(r"\n{3,}", "\n\n", out)
        return out.strip()

    # ==================================================================
    # 同音错字纠正
    # ==================================================================
    def _fix_homophones(self, text: str) -> str:
        """
        按白名单纠正 Whisper 的同音错字。

        策略：
          - 长词优先（「无时无刻不再」先于「不再」）
          - 整词精确匹配，不做模糊/正则匹配
          - 命中跳过上下文（如「销售额」）时不替换，避免误改正常表达
          - 长词替换后，短词不再重复处理同一位置（用占位保护）
        """
        if not text:
            return text

        out = text
        for wrong, right in _HOMOPHONE_ORDERED:
            if wrong not in out:
                continue

            skips = _HOMOPHONE_SKIP_CONTEXT.get(wrong, ())

            if not skips:
                out = out.replace(wrong, right)
                continue

            # 逐处判断上下文：命中跳过词的位置保持原样
            parts: List[str] = []
            idx = 0
            while True:
                pos = out.find(wrong, idx)
                if pos == -1:
                    parts.append(out[idx:])
                    break

                # 检查该位置周围是否处于跳过上下文中
                window = out[max(0, pos - 2): pos + len(wrong) + 2]
                if any(s in window for s in skips):
                    parts.append(out[idx:pos + len(wrong)])
                    idx = pos + len(wrong)
                else:
                    parts.append(out[idx:pos])
                    parts.append(right)
                    idx = pos + len(wrong)

            out = "".join(parts)

        return out

    # ==================================================================
    # 标点规范化
    # ==================================================================
    @staticmethod
    def _normalize(text: str) -> str:
        """
        统一标点与空白：
          - 半角标点 → 全角中文标点
          - 中文语境下的英文句点 → 句号
          - 压缩多余空白，去掉标点前后的空格
          - 清理非法标点组合
        """
        out = text
        for half, full in _HALFWIDTH_MAP.items():
            out = out.replace(half, full)

        # 合并重复标点（如「。。」「，，」）
        out = re.sub(r"([，。！？；：、])\1+", r"\1", out)
        # 去掉标点前的空格、标点后的多余空格
        out = re.sub(r"\s+([，。！？；：、])", r"\1", out)
        out = re.sub(r"([，。！？；：、])\s*", r"\1", out)
        # 压缩连续空白
        out = re.sub(r"[ \t]+", " ", out)
        out = re.sub(r"\n{3,}", "\n\n", out)

        out = PunctuationRestorer._cleanup_sequences(out)
        return out.strip()

    @staticmethod
    def _cleanup_sequences(text: str) -> str:
        """
        清理不合法 / 不美观的标点组合。

        标点还原过程中，句子切分与句末标点判定是两条独立路径，
        衔接处容易产生「，。」「？？」「。呀」这类组合。
        这里统一收敛为「保留语义最强的那个标点」。
        """
        out = text

        # 1) 句末标点 + 逗号/顿号 → 只保留句末标点
        out = re.sub(r"([。！？；：])[，、]+", r"\1", out)
        # 2) 逗号 + 句末标点 → 只保留句末标点
        out = re.sub(r"[，、]+([。！？；：])", r"\1", out)
        # 3) 句末标点 + 另一句末标点 → 保留强度更高的
        #    优先级：？ > ！ > 。 ；：保留前者
        def _merge_final(m):
            a, b = m.group(1), m.group(2)
            for stronger in ("？", "！"):
                if a == stronger or b == stronger:
                    return stronger
            return a
        out = re.sub(r"([。！？；：])([。！？；：])", _merge_final, out)
        # 4) 句号后紧跟逗号/顿号（跨轮拼接产生）
        out = re.sub(r"。[，、]+", "。", out)
        # 5) 语气词前的多余句号：「。呀」「。好」等 → 去掉句号
        #    但仅当语气词后面还有内容时（避免把正常断句的「好。」误伤）
        out = re.sub(r"。([呀啊呢吧嘛哦噢啦咯])(?=.)", r"\1", out)
        # 6) 段首/段尾的孤立标点
        out = re.sub(r"\n\s*[，、。；：]+", "\n", out)
        # 7) 段落之间若以逗号结尾，补成句号（整段只有一个逗号结尾很别扭）
        out = re.sub(r"，(\n|$)", r"。\1", out)
        # 8) 收尾清理：去掉结尾多余的逗号
        out = re.sub(r"[，、]+$", "。", out)

        return out

    # ==================================================================
    # 标点密度
    # ==================================================================
    @staticmethod
    def _punctuation_density(text: str) -> float:
        if not text:
            return 0.0
        return len(_HAS_PUNCT_RE.findall(text)) / max(len(text), 1)

    # ==================================================================
    # 第一级：切分为句子
    # ==================================================================
    def _split_sentences(self, raw: str) -> List[str]:
        """
        扫描整段文本，在「句子边界」处切开。

        边界优先级：
          1. 已有的句末标点（。！？；）—— 这是最强的边界信号，
             因为 Whisper 有时已经吐出了部分标点，必须尊重它，
             否则会在标点之后又按长度硬切，把词语拦腰截断。
          2. 句末语气词之后
          3. 超长无边界时的安全兜底
        """
        sentences: List[str] = []
        buf = ""

        for ch in raw:
            # 0) 已有句末标点 → 立即收句（标点随句保留）
            if ch in "。！？；":
                buf += ch
                if len(buf.strip()) > 1:
                    sentences.append(buf)
                    buf = ""
                continue

            buf += ch

            # 1) 句末语气词 → 收句（需通过词语边界校验）
            if self._is_final_particle(raw, buf, ch) and len(buf) >= MIN_SENTENCE_LEN:
                sentences.append(buf)
                buf = ""
                continue

            # 2) 超长兜底：达到上限时，先尝试在安全位置收束
            if len(buf) >= HARD_CAP_LEN:
                safe = self._last_safe_cut(raw, buf)
                if safe:
                    sentences.append(buf[:safe])
                    buf = buf[safe:]
                # 找不到安全断点就继续累积——宁可句子偏长，也不切断语义

        if buf.strip():
            sentences.append(buf)

        # 二次切分：处理「句首起始词前断句」
        refined: List[str] = []
        for sent in sentences:
            refined.extend(self._split_on_starters(sent))

        # 三次切分：超长句按标点预算切分
        final: List[str] = []
        for sent in refined:
            final.extend(self._split_by_budget(sent))

        return [s for s in final if s.strip()]

    def _split_by_budget(self, sent: str) -> List[str]:
        """
        当一个句子过长时，按「标点预算」把它切成若干句。
        切分点选在连词/起始词处，并保证不低于 MIN_SENTENCE_LEN。
        """
        if len(sent) <= MAX_SENTENCE_LEN:
            return [sent]

        # 收集候选切分点（切在该位置之前）
        candidates: List[int] = []
        i = 0
        n = len(sent)
        while i < n:
            hit = self._match_any(sent, i, self._break_before + self._starters)
            if hit is not None:
                # 必须通过词语边界校验，避免「一举|同时」这类误切
                if i >= MIN_SENTENCE_LEN and self._is_safe_cut(sent, i):
                    candidates.append(i)
                i += len(hit)
            else:
                i += 1

        if not candidates:
            return [sent]

        parts: List[str] = []
        prev = 0
        for pos in candidates:
            # 距离上一个切点太近就跳过，避免产生碎片句
            if pos - prev < MIN_SENTENCE_LEN:
                continue
            # 已经够短就不再切
            if len(sent) - prev <= MAX_SENTENCE_LEN:
                break
            parts.append(sent[prev:pos])
            prev = pos

        parts.append(sent[prev:])
        return [p for p in parts if p.strip()]

    def _split_on_starters(self, sent: str) -> List[str]:
        """
        在一个长句中，把句首起始词之前的位置切开。

        关键约束：切点必须通过 _is_safe_cut 校验，否则会把
        「一举|同时」「虾|饺」这类词拦腰截断。
        """
        # 收集所有起始词出现位置
        positions: List[int] = []
        i = 0
        n = len(sent)
        while i < n:
            hit = self._match_any(sent, i, self._starters)
            if hit is not None:
                # 起始词不能在句首（那本来就是句首）
                # 且切点必须落在词语边界上（如「一举同时」中的「同时」前面
                # 是「举」，属于构词，不可断）
                if i >= MIN_SENTENCE_LEN and self._is_safe_cut(sent, i):
                    positions.append(i)
                i += len(hit)
            else:
                i += 1

        if not positions:
            return [sent]

        parts: List[str] = []
        prev = 0
        for pos in positions:
            if pos - prev >= MIN_SENTENCE_LEN:
                parts.append(sent[prev:pos])
                prev = pos
        parts.append(sent[prev:])
        return [p for p in parts if p.strip()]

    # ==================================================================
    # 利用 Whisper 分段停顿
    # ==================================================================
    def _sentences_from_segments(self, segments: List[dict]) -> List[str]:
        """按段间停顿长短，把 Whisper 分段合并成句子"""
        seg_texts: List[Tuple[str, float]] = []  # (text, gap_to_next)

        for i, seg in enumerate(segments):
            text = re.sub(r"\s+", "", seg.get("text", "") or "")
            if not text:
                continue
            gap = 0.0
            if i + 1 < len(segments):
                try:
                    gap = float(segments[i + 1].get("start", 0)) - float(seg.get("end", 0))
                except (TypeError, ValueError):
                    gap = 0.0
            seg_texts.append((text, gap))

        if not seg_texts:
            return []

        sentences: List[str] = []
        buf = ""
        for text, gap in seg_texts:
            buf += text
            ends_with_particle = buf and buf[-1] in _FINAL_PARTICLES
            long_enough = len(buf) >= MIN_SENTENCE_LEN

            if long_enough and (gap >= PAUSE_STRONG or ends_with_particle):
                sentences.append(buf)
                buf = ""
            elif long_enough and gap >= PAUSE_MEDIUM and len(buf) >= 20:
                sentences.append(buf)
                buf = ""

        if buf.strip():
            sentences.append(buf)

        # 每个句子内部再做小句切分 + 补标点
        return [self._punctuate_clauses(s) for s in sentences]

    # ==================================================================
    # 第二级：句内小句切分 + 标点
    # ==================================================================
    def _punctuate_clauses(self, sentence: str) -> str:
        """
        为一个句子补上句末标点，并在内部合理位置插入逗号。
        返回：带标点的完整句子
        """
        body = sentence.strip()
        if not body:
            return body

        # 去掉可能残留的空白
        body = re.sub(r"\s+", "", body)

        # 句末标点先摘出来，避免被当成正文参与切分
        final_punct = self._pick_final_punct(body)
        core = body.rstrip("，。！？；：、")

        # 若句内已有标点，说明这句已经被上游标点化过（例如 Whisper 自带的
        # 逗号）。此时必须**尊重既有标点**，只在没有标点的长片段里补逗号，
        # 否则会把「一举相同时，」错切成「一举相，同时，」。
        if _HAS_PUNCT_RE.search(core):
            return self._punctuate_keeping_existing(core, final_punct)

        # 1) 无既有标点：切小句
        clauses = self._split_clauses(core)

        # 2) 逐个补标点：内部小句用逗号，最后一句用句末标点
        if len(clauses) == 1:
            return clauses[0] + final_punct

        out = ""
        for i, c in enumerate(clauses):
            if i < len(clauses) - 1:
                out += c.rstrip("，。！？；：、") + "，"
            else:
                out += c.rstrip("，。！？；：、") + final_punct
        return out

    def _punctuate_keeping_existing(self, core: str, final_punct: str) -> str:
        """
        句内已有标点时，保持既有标点不变，只为其中「过长的无标点片段」
        补上逗号。

        这样既不会破坏 Whisper 已有的正确断句，又能改善长句可读性。
        """
        # 按既有标点切片，保留分隔符
        pieces = re.split(r"([，、；：])", core)

        out: List[str] = []
        for piece in pieces:
            if not piece:
                continue
            if piece in "，、；：":
                out.append(piece)
                continue

            # 纯文本片段：仅当过长时才补逗号
            if len(piece) > MAX_CLAUSE_LEN:
                sub = self._split_clauses(piece)
                if len(sub) > 1:
                    out.append("，".join(s.rstrip("，、；：") for s in sub if s))
                    continue
            out.append(piece)

        result = "".join(out).rstrip("，、；：")
        return result + final_punct

    def _split_clauses(self, body: str) -> List[str]:
        """在小句边界处切分，并处理超长小句的呼吸点"""
        # 1) 收集切分点（切在该位置之前）
        cuts = set()
        i = 0
        n = len(body)
        while i < n:
            hit = self._match_any(body, i, self._break_before)
            if hit is not None:
                # 切点必须落在词语边界上
                if i >= 6 and self._is_safe_cut(body, i):
                    cuts.add(i)
                i += len(hit)
                continue
            i += 1

        # 2) 后置型连词：切在词之后
        i = 0
        while i < n:
            hit = self._match_any(body, i, self._break_after)
            if hit is not None:
                end = i + len(hit)
                # 必须同时满足：
                #   a) 前后都留有足够内容
                #   b) 切点落在词语边界上（防止「一举相同时」被切成
                #      「一举相，同时」—— '同时' 本身是词，切点在它之前
                #      会破坏 '相同时'）
                #   c) 切点前不是构词字
                if end < n - 4 and end >= 4 and self._is_safe_cut(body, i):
                    cuts.add(end)
                i = end
                continue
            i += 1

        # 3) 按切分点切分
        ordered = sorted(c for c in cuts if 0 < c < n)
        parts: List[str] = []
        prev = 0
        for c in ordered:
            if c - prev < 5:
                continue
            parts.append(body[prev:c])
            prev = c
        parts.append(body[prev:])
        parts = [p for p in parts if p]

        # 4) 超长小句：寻找自然呼吸点强制切开
        result: List[str] = []
        for p in parts:
            result.extend(self._break_long_clause(p))
        return result

    def _break_long_clause(self, clause: str) -> List[str]:
        """
        仅在句子明显过长（超过 MAX_SENTENCE_LEN）且能找到**连词**级别的
        安全断点时才插入逗号。

        设计取舍：课堂上的一句话如果只有 30-45 字，不插逗号完全可读；
        勉强插入反而会破坏语义。因此这里保持高度保守。
        """
        if len(clause) <= MAX_CLAUSE_LEN:
            return [clause]

        # 只在连词/起始词处切分，不用虚词做呼吸点（虚词切分容易读起来很怪）
        cuts: List[int] = []
        i = 0
        n = len(clause)
        while i < n:
            hit = self._match_any(clause, i, self._break_after)
            if hit is not None:
                end = i + len(hit)
                if 10 <= end <= n - 8 and self._is_safe_cut(clause, end):
                    cuts.append(end)
                i = end
                continue
            i += 1

        if not cuts:
            return [clause]

        parts: List[str] = []
        prev = 0
        for c in cuts:
            if c - prev < 12:
                continue
            parts.append(clause[prev:c])
            prev = c
        parts.append(clause[prev:])
        return [p for p in parts if p]

    # ==================================================================
    # 句末标点选择
    # ==================================================================
    def _pick_final_punct(self, sentence: str) -> str:
        if not sentence:
            return "。"

        # 感叹句
        if sentence.startswith(_EXCLAMATION_STARTS):
            return "！"

        # 疑问句判定 —— 必须同时满足「含疑问词」且「句末语气支持疑问」，
        # 否则「首先什么是信息信息是客观世界…」这类陈述会被误判为疑问句。
        has_interrogative = any(w in sentence for w in self._interrogatives)
        if has_interrogative and self._is_question_shaped(sentence):
            return "？"

        if sentence[-1] in {"吗", "呢"}:
            return "？"

        return "。"

    @staticmethod
    def _is_question_shaped(sentence: str) -> bool:
        """
        判断含疑问词的句子是否真的是疑问句。

        疑问句的典型标志：
          a) 句末是「吗/呢/吧」等语气词
          b) 疑问词出现在句子的**后半段**
          c) 句子以疑问词**开头**（如「什么是信息？」「如何设计导入？」）
        """
        tail = sentence[-1]
        if tail in _FINAL_PARTICLES:
            return True

        # 找最早出现的疑问词位置
        earliest = len(sentence)
        for w in ("什么", "为什么", "怎么", "怎样", "如何", "哪里", "哪儿",
                  "哪个", "哪些", "谁", "多少", "是不是", "对不对", "好不好",
                  "行不行", "能不能", "可不可以", "有没有", "是否", "难道"):
            idx = sentence.find(w)
            if idx != -1 and idx < earliest:
                earliest = idx

        if earliest == len(sentence):
            return False

        # 疑问词位于句子后半段 → 疑问句
        if earliest >= len(sentence) * 0.5:
            return True

        # 疑问词在句首，且句子较短（≤ 24 字）→ 疑问句
        if earliest <= 4 and len(sentence) <= 24:
            return True

        return False

    # ==================================================================
    # 工具
    # ==================================================================
    # ==================================================================
    # 词语边界校验 —— 防止在词语内部误断
    # ==================================================================
    @staticmethod
    def _is_final_particle(raw: str, buf: str, ch: str) -> bool:
        """
        判断 buf 末尾的 ch 是否真的是「句末语气词」。

        关键约束：如果 ch 的**后一个字**是逻辑连接词（那/这/就/也/都…）或
        常用虚词，说明 ch 正在参与构词（如「同学好今天…」「…话来表现」），
        此时不得断句。
        """
        # 含歧义的字（好/了/的/是）仅在无后续串接时才可能是句末
        if ch in _AMBIGUOUS_PARTICLES:
            return False

        if ch not in _FINAL_PARTICLES:
            return False

        idx = len(buf) - 1
        nxt = raw[idx + 1] if idx + 1 < len(raw) else ""

        # 后面紧跟连接词/虚词 → 属于构词，不断
        if nxt and (nxt in _LOGICAL_CONNECTORS or nxt in _AMBIGUOUS_PARTICLES):
            return False

        # 前面是称呼类字（「同学们」「老师们」中的「们」）且 ch 是语气词
        # 例如「老师们的」——避免误断
        if len(buf) >= 2 and buf[-2] == "们":
            return False

        return True

    @staticmethod
    def _is_safe_cut(text: str, pos: int) -> bool:
        """
        判断在 pos 处断句是否安全（不切断词语）。

        采用「逆序校验」：中文的句子边界通常紧跟在**实词**之后，
        因此如果 pos 前面的字是动词/名词性实词，且 pos 后面的字
        是常用虚词或动词，则极可能切断了「动宾结构」。
        """
        if pos <= 0 or pos >= len(text):
            return False

        prev = text[pos - 1]
        nxt = text[pos]

        # 前半段以「结构标记字」结尾 → 必然切断了词
        BAD_END = {
            "接", "我", "你", "他", "她", "它", "大", "这", "那", "什",
            "怎", "为", "如", "数", "对", "图", "声", "信", "技", "下",
            "上", "中", "里", "面", "的", "地", "得", "了", "着", "过",
            "们", "个", "么", "象", "时", "会", "能", "要", "就", "也",
            "都", "还", "又", "才", "只", "便", "即", "和", "与", "或",
            "被", "把", "在", "从", "向", "给", "让", "使", "于", "所",
            # 构词高频字：出现在断点前说明极可能切断了双字词
            "语", "言", "术", "文", "知", "识", "学", "生",
            "教", "师", "课", "堂", "问", "题", "方", "法",
            "程", "结", "内", "容", "目", "标", "重",
            # 「相同时」「相同」类：'相' 后接 '同' 时不可断
            "相", "不", "没", "无", "非", "未", "很", "更", "最",
            "比", "较", "真", "正", "确", "应", "该", "需",
        }
        if prev in BAD_END:
            return False

        # 后半段以这些字开头 → 几乎总是被切断了
        BAD_START = {
            "来", "去", "们", "的", "地", "得", "了", "着", "过",
            "个", "么", "象", "面", "里", "中", "上", "下", "时",
            "我", "你", "他", "她", "它", "这", "那",
        }
        if nxt in BAD_START:
            return False

        # 前后两字若构成常见双字词，则此处不安全
        if (prev + nxt) in _COMMON_BIGRAMS:
            return False

        # 前半段以「未完成结构的引导字」结尾 → 句子还没说完
        if prev in _INCOMPLETE_TAIL:
            return False

        # 后半段以助词开头 → 被切断了
        if nxt in {"的", "地", "得", "了", "着", "过", "们"}:
            return False

        return True

    def _last_safe_cut(self, raw: str, buf: str) -> int:
        """
        在 buf 中寻找最靠后的一个安全切分点（相对 buf 的偏移）。

        优先选择**句子起始词之前**的位置（如「接下来」「最后」「所以」之前），
        这类断点语义最自然；其次才退化到通用安全位置。
        """
        base = len(raw) - len(buf)
        floor = max(int(len(buf) * 0.55), 12)

        # 优先级 1：起始词之前
        for pos in range(len(buf) - 1, floor - 1, -1):
            if any(buf.startswith(t, pos) for t in self._starters):
                if self._is_safe_cut(raw, base + pos):
                    return pos

        # 优先级 2：连词之前
        for pos in range(len(buf) - 1, floor - 1, -1):
            if any(buf.startswith(t, pos) for t in self._break_before):
                if self._is_safe_cut(raw, base + pos):
                    return pos

        # 优先级 3：任意安全位置
        for pos in range(len(buf) - 1, floor - 1, -1):
            if self._is_safe_cut(raw, base + pos):
                return pos

        return 0

    @staticmethod
    def _match_any(text: str, pos: int, terms: List[str]) -> Optional[str]:
        for t in terms:
            if text.startswith(t, pos):
                return t
        return None

    @staticmethod
    def _format_paragraphs(sentences: List[str]) -> str:
        """将句子合并为自然段：每段 2-4 句，优先在语义完整处收束"""
        if not sentences:
            return ""

        paragraphs: List[str] = []
        chunk: List[str] = []
        chunk_len = 0

        for s in sentences:
            chunk.append(s)
            chunk_len += len(s)
            # 段落在 3 句或 90 字左右收束
            if len(chunk) >= 3 or chunk_len >= 110:
                paragraphs.append("".join(chunk))
                chunk = []
                chunk_len = 0

        if chunk:
            paragraphs.append("".join(chunk))

        return "\n\n".join(paragraphs)

    # ==================================================================
    # 一行调用兼容接口
    # ==================================================================
    @staticmethod
    def quick_restore(text: str) -> str:
        return PunctuationRestorer().restore(text)

    @staticmethod
    def diff_corrections(original: str, processed: str) -> List[str]:
        """
        列出本次处理中实际修正的同音错字。

        用于向用户透明展示「改了什么」，避免纠错过程成为黑盒。
        返回形如 ["销售→销量", "降续→降序"] 的列表。
        """
        if not original or not processed:
            return []

        found: List[str] = []
        for wrong, right in _HOMOPHONE_ORDERED:
            # 纠正后应出现 right 且不再出现 wrong
            if right in processed and processed.count(right) > original.count(right):
                found.append(f"{wrong}→{right}")
        return found


# 单例，供 main.py / whisper_engine 直接调用
punctuation_restorer = PunctuationRestorer()
