# ==========================================================================
# 学思践悟 — 运行时 API 配置
#
# 目的：让用户在前端「完整模式」里直接填写 API Key / Base URL / 模型名，
#       无需手工编辑 backend/.env 再重启后端。
#
# 设计要点：
#   1. 运行时配置优先于 .env —— 前端保存后立即生效
#   2. 持久化到 backend/data/runtime_config.json，重启后仍然有效
#   3. 密钥永不回传明文：状态查询只返回掩码（sk-abc••••••1234）
#   4. 写入前做一次真实连通性校验，避免存下一个错误 Key
# ==========================================================================

import json
import os
import re
import threading
from typing import Dict, Optional, Tuple

# --------------------------------------------------------------------------
# 可配置项与默认值
# --------------------------------------------------------------------------
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"

# 允许用户覆盖的字段
CONFIG_FIELDS = ("api_key", "base_url", "model")

# 常见的服务地址预设（供前端下拉选择）
BASE_URL_PRESETS = [
    {"label": "DeepSeek 官方", "value": "https://api.deepseek.com"},
    {"label": "DeepSeek 兼容模式", "value": "https://api.deepseek.com/v1"},
    {"label": "阿里云百炼（通义千问）", "value": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    {"label": "智谱 GLM", "value": "https://open.bigmodel.cn/api/paas/v4"},
    {"label": "Moonshot（Kimi）", "value": "https://api.moonshot.cn/v1"},
    {"label": "本地 Ollama", "value": "http://127.0.0.1:11434/v1"},
]

# 模型名建议（按服务商）
MODEL_SUGGESTIONS = [
    "deepseek-chat",
    "deepseek-reasoner",
    "qwen-plus",
    "glm-4-plus",
    "moonshot-v1-8k",
]


class RuntimeConfig:
    """运行时 API 配置（线程安全，可热更新）"""

    def __init__(self, data_dir: str):
        self._lock = threading.RLock()
        self._path = os.path.join(data_dir, "runtime_config.json")

        # 内存中的当前值
        self._api_key: str = ""
        self._base_url: str = DEFAULT_BASE_URL
        self._model: str = DEFAULT_MODEL

        # 来源标记，便于前端区分「来自 .env」还是「界面填写」
        self._source: str = "none"

        os.makedirs(data_dir, exist_ok=True)
        self._load()

    # ==================================================================
    # 读写
    # ==================================================================
    def _load(self):
        """加载顺序：运行时文件 → 环境变量 / .env → 默认值"""
        # 1) 运行时配置文件（最高优先级）
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._api_key = (data.get("api_key") or "").strip()
                self._base_url = (data.get("base_url") or DEFAULT_BASE_URL).strip()
                self._model = (data.get("model") or DEFAULT_MODEL).strip()
                if self._api_key:
                    self._source = "file"
                    print(f"[Config] 已从 runtime_config.json 载入 API 配置 "
                          f"(base_url={self._base_url}, model={self._model})")
                    return
            except Exception as e:  # noqa: BLE001
                print(f"[Config] runtime_config.json 读取失败，忽略: {e}")

        # 2) 环境变量 / .env
        env_key = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
        if env_key and env_key != "your_deepseek_api_key_here":
            self._api_key = env_key
            self._base_url = (os.getenv("DEEPSEEK_BASE_URL") or DEFAULT_BASE_URL).strip()
            self._model = (os.getenv("DEEPSEEK_MODEL") or DEFAULT_MODEL).strip()
            self._source = "env"
            print("[Config] 已从环境变量载入 API Key")
            return

        # 3) 未配置
        self._source = "none"

    def _save(self):
        """持久化到磁盘（权限 0600，避免密钥被其他用户读取）"""
        payload = {
            "api_key": self._api_key,
            "base_url": self._base_url,
            "model": self._model,
        }
        tmp = self._path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self._path)
        try:
            os.chmod(self._path, 0o600)
        except OSError:
            pass

    # ==================================================================
    # 查询
    # ==================================================================
    @property
    def api_key(self) -> str:
        with self._lock:
            return self._api_key

    @property
    def base_url(self) -> str:
        with self._lock:
            return self._base_url

    @property
    def model(self) -> str:
        with self._lock:
            return self._model

    @property
    def configured(self) -> bool:
        with self._lock:
            return self.is_valid_key(self._api_key)

    @staticmethod
    def is_valid_key(key: str) -> bool:
        """基础格式校验：非空、不是占位符、长度合理"""
        k = (key or "").strip()
        if not k or k == "your_deepseek_api_key_here":
            return False
        # 大多数服务商的 Key 都在 16 字符以上；本地 Ollama 可能不需要 Key
        return len(k) >= 8

    @staticmethod
    def mask_key(key: str) -> str:
        """
        生成掩码用于前端展示，绝不回传明文。

        sk-abcdefghijklmnop1234  →  sk-abc••••••1234
        """
        k = (key or "").strip()
        if not k:
            return ""
        if len(k) <= 10:
            return k[:2] + "•" * max(len(k) - 2, 2)

        head = k[:6]
        tail = k[-4:]
        return f"{head}{'•' * 6}{tail}"

    def status(self) -> Dict:
        """返回给前端的配置状态（不含明文密钥）"""
        with self._lock:
            return {
                "configured": self.is_valid_key(self._api_key),
                "api_key_masked": self.mask_key(self._api_key),
                "base_url": self._base_url,
                "model": self._model,
                "source": self._source,
                "presets": BASE_URL_PRESETS,
                "model_suggestions": MODEL_SUGGESTIONS,
                "defaults": {
                    "base_url": DEFAULT_BASE_URL,
                    "model": DEFAULT_MODEL,
                },
            }

    # ==================================================================
    # 更新
    # ==================================================================
    def update(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict:
        """
        更新配置并持久化。

        - api_key 传空字符串表示「清除」
        - 传 None 表示「保持原值不变」
        """
        with self._lock:
            if api_key is not None:
                self._api_key = api_key.strip()
            if base_url is not None and base_url.strip():
                self._base_url = base_url.strip().rstrip("/")
            if model is not None and model.strip():
                self._model = model.strip()

            # 用户手工填写后，来源标记为界面
            if api_key is not None and self._api_key:
                self._source = "ui"

            self._save()
            return self.status()

    def clear(self) -> Dict:
        """清除运行时配置（回到 .env / 未配置状态）"""
        with self._lock:
            self._api_key = ""
            self._base_url = DEFAULT_BASE_URL
            self._model = DEFAULT_MODEL
            self._source = "none"
            try:
                if os.path.exists(self._path):
                    os.remove(self._path)
            except OSError:
                pass
            return self.status()


# ==========================================================================
# 工具函数
# ==========================================================================
def normalize_base_url(url: str) -> str:
    """
    规范化服务地址。

    多数兼容 OpenAI 的网关需要 /v1 后缀，但 DeepSeek 官方文档给的是
    不带 /v1 的形式（SDK 会自动补）。这里只做去尾斜杠，不做猜测性改写，
    避免把可用的地址改坏。
    """
    u = (url or "").strip()
    if not u:
        return DEFAULT_BASE_URL
    return u.rstrip("/")


def validate_base_url(url: str) -> Tuple[bool, str]:
    """校验服务地址格式"""
    u = (url or "").strip()
    if not u:
        return False, "服务地址不能为空"
    if not re.match(r"^https?://", u):
        return False, "服务地址必须以 http:// 或 https:// 开头"
    if len(u) < 12:
        return False, "服务地址格式不正确"
    return True, ""


# ==========================================================================
# 单例：供 main.py / agent_logic.py 直接调用
# ==========================================================================
# 配置持久化目录与后端数据目录保持一致
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
runtime_config = RuntimeConfig(_DATA_DIR)
