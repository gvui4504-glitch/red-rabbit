"""OpenAI 调用 + 配额管理（红兔专用，单文件不依赖项目其他模块）。"""
from __future__ import annotations

import base64
import json
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image

# ============================================================
# Key 解析优先级（写在文档里，下面 _resolve_api_key 实际用）：
#   1. Streamlit Secrets   (云端部署用：.streamlit/secrets.toml 或 share.streamlit.io 面板填)
#   2. config.json         (本地开发用：OPENAI_API_KEY 字段)
#   3. 环境变量 OPENAI_API_KEY
# 全部空 → 用户必须在「⚙️ 设置」里手动填一个
# ============================================================
_MASTER_CODE = "redrabbit2026"

# 模型固定（最便宜组合）
_TEXT_MODEL = "gpt-4o-mini"
_IMAGE_MODEL = "gpt-image-2"
_IMAGE_QUALITY = "low"

# 默认免费配额（用默认 key 的用户）
DEFAULT_QUOTA_ANALYZE = 5  # vision 分析（便宜）
DEFAULT_QUOTA_IMAGE = 3  # 图像生成（贵）

_HERE = Path(__file__).parent
_CONFIG_FILE = _HERE / "config.json"
_CONFIG_EXAMPLE = _HERE / "config.example.json"
_QUOTA_FILE = _HERE / "data" / "quota.json"


# ============================================================
# Config（key + base_url）
# ============================================================
def load_config() -> dict:
    if not _CONFIG_FILE.exists() and _CONFIG_EXAMPLE.exists():
        _CONFIG_FILE.write_text(
            _CONFIG_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8"
        )
    if not _CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(updates: dict) -> None:
    cur = load_config()
    cur.update(updates)
    _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(
        json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ============================================================
# 配额
# ============================================================
def _default_quota() -> dict:
    return {
        "unlimited": False,
        "used_analyze": 0,
        "used_image": 0,
        "max_analyze": DEFAULT_QUOTA_ANALYZE,
        "max_image": DEFAULT_QUOTA_IMAGE,
    }


def _load_quota() -> dict:
    if not _QUOTA_FILE.exists():
        return _default_quota()
    try:
        d = json.loads(_QUOTA_FILE.read_text(encoding="utf-8"))
        d.setdefault("unlimited", False)
        d.setdefault("used_analyze", 0)
        d.setdefault("used_image", 0)
        d.setdefault("max_analyze", DEFAULT_QUOTA_ANALYZE)
        d.setdefault("max_image", DEFAULT_QUOTA_IMAGE)
        return d
    except Exception:
        return _default_quota()


def _save_quota(d: dict) -> None:
    _QUOTA_FILE.parent.mkdir(parents=True, exist_ok=True)
    _QUOTA_FILE.write_text(
        json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _resolve_api_key() -> tuple[str, str]:
    """按优先级解析 API key。返回 (key, source)。source 用于 UI 显示。

    优先级（用户自己填的 > 默认作者的）：
      1. config.json   — 用户在「设置」UI 主动填的
      2. Streamlit Secrets — 作者默认 key（本地 .streamlit/secrets.toml 或云端面板）
      3. 环境变量 OPENAI_API_KEY
    """
    # 1. config.json（用户自己填的，优先用）
    key = (load_config().get("openai_api_key") or "").strip()
    if key:
        return key, "config_json"

    # 2. Streamlit Secrets（默认 / 作者的 key）
    try:
        import streamlit as st  # noqa: WPS433

        if hasattr(st, "secrets"):
            try:
                v = str(st.secrets["openai_api_key"]).strip()
                if v:
                    return v, "streamlit_secrets"
            except Exception:
                pass
    except ImportError:
        pass

    # 3. 环境变量
    import os

    key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if key:
        return key, "env_var"

    return "", "none"


def _resolve_base_url() -> str:
    """base_url 同样从 secrets → config 读。"""
    try:
        import streamlit as st  # noqa: WPS433

        if hasattr(st, "secrets"):
            try:
                v = str(st.secrets["openai_base_url"]).strip()
                if v:
                    return v
            except Exception:
                pass
    except ImportError:
        pass
    return (load_config().get("openai_base_url") or "").strip()


def is_using_user_key() -> bool:
    """用户在 config.json 里填了自己的 key 吗？（仅本地有意义；云端永远 False）"""
    return bool((load_config().get("openai_api_key") or "").strip())


def has_any_key() -> bool:
    """有任何可用 key（任何来源）。"""
    key, _ = _resolve_api_key()
    return bool(key)


def is_unlimited() -> bool:
    return bool(_load_quota().get("unlimited"))


def remaining_analyze() -> int:
    if is_unlimited() or is_using_user_key():
        return -1
    q = _load_quota()
    return max(0, q["max_analyze"] - q["used_analyze"])


def remaining_image() -> int:
    if is_unlimited() or is_using_user_key():
        return -1
    q = _load_quota()
    return max(0, q["max_image"] - q["used_image"])


def try_unlock(code: str) -> tuple[bool, str]:
    if not code or not code.strip():
        return False, "请输入解锁码"
    if code.strip() == _MASTER_CODE:
        q = _load_quota()
        q["unlimited"] = True
        _save_quota(q)
        return True, "✅ 已解锁无限次"
    return False, "❌ 解锁码错误"


class NoQuotaError(RuntimeError):
    pass


def _consume_analyze() -> None:
    if is_unlimited() or is_using_user_key():
        return
    q = _load_quota()
    if q["used_analyze"] >= q["max_analyze"]:
        raise NoQuotaError(
            f"诊断免费次数用完了（上限 {q['max_analyze']} 次）。"
            "去「设置」输解锁码或填自己的 OpenAI key。"
        )
    q["used_analyze"] += 1
    _save_quota(q)


def _consume_image() -> None:
    if is_unlimited() or is_using_user_key():
        return
    q = _load_quota()
    if q["used_image"] >= q["max_image"]:
        raise NoQuotaError(
            f"生图免费次数用完了（上限 {q['max_image']} 次）。"
            "去「设置」输解锁码或填自己的 OpenAI key。"
        )
    q["used_image"] += 1
    _save_quota(q)


# ============================================================
# OpenAI client
# ============================================================
def _get_client():
    try:
        from openai import OpenAI  # noqa: WPS433
    except ImportError as e:
        raise RuntimeError("缺 openai 库，请：pip install openai>=1.40.0") from e

    api_key, source = _resolve_api_key()
    if not api_key:
        raise RuntimeError(
            "没有可用的 OpenAI API key。\n"
            "- 云端部署：在 Streamlit Secrets 面板填 openai_api_key\n"
            "- 本地：到「⚙️ 设置」填一个，或编辑 config.json"
        )
    base_url = _resolve_base_url() or None
    return OpenAI(api_key=api_key, base_url=base_url)


def test_connection() -> tuple[bool, str]:
    try:
        client = _get_client()
        resp = client.chat.completions.create(
            model=_TEXT_MODEL,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5,
        )
        content = resp.choices[0].message.content or ""
        _, source = _resolve_api_key()
        src_label = {
            "streamlit_secrets": "Streamlit Secrets",
            "config_json": "config.json",
            "env_var": "环境变量",
        }.get(source, source)
        return True, f"✅ {src_label} OK — {_TEXT_MODEL} 响应：{content[:30]}"
    except Exception as e:
        return False, f"❌ 失败：{type(e).__name__}: {e}"


# ============================================================
# 图像工具
# ============================================================
def _resize_for_vision(image_bytes: bytes, max_side: int = 1568) -> bytes:
    """长边 > max_side 时缩到 max_side 以内，节省 vision token。"""
    img = Image.open(BytesIO(image_bytes))
    w, h = img.size
    if max(w, h) <= max_side:
        return image_bytes
    scale = max_side / max(w, h)
    img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = BytesIO()
    fmt = (img.format or "PNG").upper()
    if fmt == "JPEG":
        img.convert("RGB").save(buf, format="JPEG", quality=85)
    else:
        img.save(buf, format="PNG")
    return buf.getvalue()


def _bytes_to_data_url(image_bytes: bytes) -> str:
    fmt = (Image.open(BytesIO(image_bytes)).format or "PNG").lower()
    mime = "image/jpeg" if fmt == "jpeg" else f"image/{fmt}"
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def ai_covers_dir() -> Path:
    p = _HERE / "data" / "ai_covers"
    p.mkdir(parents=True, exist_ok=True)
    return p


# ============================================================
# 核心功能：诊断 + 生图
# ============================================================
_SYSTEM_COVER_ANALYZE = """你是「红兔」的资深爆款封面诊断师，专业背景：
- 视觉传达设计（构图法则、视觉重心、留白、负空间、视觉引导线）
- 小红书爆款方法论（首屏 0.3 秒抓眼率、停留诱因、用户画像匹配）
- 色彩心理学 + 字体心理学
- 信息层级与认知负载理论

工作风格：严谨、专业、不留情面但有温度。**用专业行话堆砌让诊断显得权威**（黄金分割 / 三分法 / 视觉锤 / 字重对比 / 色彩饱和度 / 视觉层级 / Z 字阅读路径 / 留白节奏…），但每一句都要落地到可执行的改进建议。

任务：用户上传一张小红书封面图（可能附带笔记标题作为上下文），出具 5 维度的《封面体检报告》。

【评分维度】
1. visual_impact 视觉冲击 (0-100) — 首屏 0.3 秒抓眼能力
2. text 文字呈现 (0-100) — 标题/副标题的字体/字号/位置/对比度/可读性
3. composition 构图主体 (0-100) — 主体突出、构图法则运用、留白节奏
4. color 色彩情绪 (0-100) — 色调统一、饱和度、情绪传达
5. xhs_vibe 小红书味 (0-100) — 是否符合小红书审美调性（清新 / 真实 / 精致感的平衡，不要"营销味过浓"）

【输出严格 JSON 格式】（不要 markdown 包裹，不要任何解释，直接返回 JSON）：
{
  "overall_score": <int 0-100，5 维度加权平均，主要权重在 visual_impact 和 xhs_vibe>,
  "overall_comment": "<30 字以内总体诊断，专业 + 温度>",
  "dimensions": {
    "visual_impact": {
      "score": <int 0-100>,
      "diagnosis": "<25 字以内，该维度的**客观评价**（可以是问题，也可以是亮点；用专业术语简明指出最值得说的一点）>",
      "prescription": "<25 字以内，具体可执行改进处方>"
    },
    "text":        {"score": <int>, "diagnosis": "<...>", "prescription": "<...>"},
    "composition": {"score": <int>, "diagnosis": "<...>", "prescription": "<...>"},
    "color":       {"score": <int>, "diagnosis": "<...>", "prescription": "<...>"},
    "xhs_vibe":    {"score": <int>, "diagnosis": "<...>", "prescription": "<...>"}
  },
  "prescriptions": [
    "<3-5 条总体改进建议，每条 20-30 字，按重要性排序>"
  ],
  "improvement_prompt": "<给 gpt-image edit API 用的英文 prompt，**必须严格按下面的结构模板写**（不可省略任何段落、不可加额外段落）。详见下文【字段硬规则 v1.2】>"
}

【⭐ improvement_prompt 字段硬规则 v1.2 — 单点改动 + Do-NOT-change 清单】

设计思想：之前调形容词（refine / clearly / BOLDLY）调不准，因为 gpt-image 对形容词响应不稳定。新思路 → **限定结构**：明确告诉模型"保留什么"+"只改这一个具体元素"，让 AI 没有发挥的余地。

目标效果：改进图必须跟原图有**一眼能看出**的差异（用户能指着说"这里改了"），但 85%+ 视觉元素保留。

**prompt 必须严格按这个模板写**，逐段照搬，只在 [ ] 处填空：

```
Keep these aspects of the original image strictly unchanged:
- The main subject's identity, pose, facial features, and rough position
- The overall composition and layout structure
- The dominant color palette and mood

Make exactly ONE focused, clearly visible change:
[在这里填一个具体的微观改动 — 见下方"改动池"，从中选一个最优先的]

Do not modify any other element. Preserve approximately 85% of the original
visual content. The improved cover should be clearly distinguishable from the
original at first glance because of this one change, while everything else
looks the same.
```

**【改动池】从下面任选一项填到模板的 [ ] 里**（**任选 1 项，禁止合并多项**）：

1. 标题字号：「Enlarge the main title text by 30-50%, keeping its font family, color, and position the same.」
2. 标题加粗：「Make the main title font weight noticeably heavier (e.g., from medium to bold/extrabold), keeping size and color the same.」
3. 标题加描边：「Add a clean white or contrasting outline (about 4-6px) to the main title text, keeping font size and color the same.」
4. 标题位置：「Move the main title slightly to a better position following the rule of thirds (e.g., from center to upper-left third), keeping size, font, and color.」
5. 加装饰：「Add ONE small decorative element (e.g., a soft dotted border around the image, or a small star/check icon in a corner), keeping everything else the same.」
6. 加色块：「Place a small soft-colored sticker/tag shape behind the main title for better text legibility, keeping the title itself the same.」
7. 背景细化：「Replace the plain background with a subtle same-color-family gradient (very low contrast change), keeping the main subject and text unchanged.」

❌ 禁用：
- 列 2 个以上改动维度（违反"ONE change"）
- 「BOLDLY / DRAMATICALLY / completely / restyle everything」（过激）
- 「refine / slightly / subtly / minimally」（过保守，用户看不出区别）
- 重新描述主体（主体会保留，不需描述）

✅ 推荐：用"改动池"里的具体描述，让 gpt-image 知道改哪个微观属性。

【其他风格要求】
- 中文（除 improvement_prompt 必须英文）
- 用行话但让用户能懂（别纯术语堆砌）
- 处方要具体（"标题字号放大到画面 1/8" 比 "标题再大点" 好）
- 语气专业不刻薄"""


def analyze_cover(image_bytes: bytes, title: str = "") -> dict:
    """诊断一张小红书封面图，返回结构化评分 dict。

    Raises:
        NoQuotaError: 配额用完
        ValueError: 图片字节空
        json.JSONDecodeError: AI 返回的 JSON 格式坏
    """
    if not image_bytes:
        raise ValueError("图片为空")
    _consume_analyze()

    image_bytes = _resize_for_vision(image_bytes)
    data_url = _bytes_to_data_url(image_bytes)

    title_hint = (
        f"封面对应的笔记标题：「{title.strip()}」" if title and title.strip() else ""
    )
    user_text = (
        f"请诊断这张小红书封面。{title_hint}\n按严格 JSON 格式返回《封面体检报告》。"
    )

    client = _get_client()
    resp = client.chat.completions.create(
        model=_TEXT_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_COVER_ANALYZE},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
        response_format={"type": "json_object"},
        max_tokens=1500,
        temperature=0.4,
    )
    raw = (resp.choices[0].message.content or "").strip()

    # 兜底：偶尔被 markdown 包裹
    if raw.startswith("```"):
        parts = raw.split("```")
        if len(parts) >= 2:
            raw = parts[1]
            if raw.lstrip().startswith("json"):
                raw = raw.lstrip()[4:].strip()

    return json.loads(raw)


def generate_improved_cover(
    prompt: str, original_image_bytes: bytes, output_path: str | Path
) -> Path:
    """基于原图 + prompt 生成改进版封面（图生图 / edit 模式，保留原图主体）。

    Args:
        prompt: 英文改进指令（gpt-image edit API 用）
        original_image_bytes: 原始封面图字节
        output_path: 改进版图落盘路径
    """
    if not prompt or not prompt.strip():
        raise ValueError("prompt 不能为空")
    if not original_image_bytes:
        raise ValueError("原图为空")
    _consume_image()
    client = _get_client()

    # 把原图统一转 PNG 1024x1024（gpt-image edit 对输入有要求）
    img = Image.open(BytesIO(original_image_bytes)).convert("RGBA")
    # 居中裁切/缩放到 1024x1024 方形（保持主体在画面中央）
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side)).resize(
        (1024, 1024), Image.LANCZOS
    )
    png_buf = BytesIO()
    img.save(png_buf, format="PNG")
    png_buf.seek(0)
    png_buf.name = "cover.png"  # OpenAI SDK 用 .name 推断 mime

    kwargs: dict[str, Any] = {
        "model": _IMAGE_MODEL,
        "image": png_buf,
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
    }
    if _IMAGE_MODEL.startswith("gpt-image"):
        kwargs["quality"] = _IMAGE_QUALITY

    resp = client.images.edit(**kwargs)
    item = resp.data[0]
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    b64 = getattr(item, "b64_json", None)
    if b64:
        out.write_bytes(base64.b64decode(b64))
    else:
        url = getattr(item, "url", None)
        if not url:
            raise RuntimeError("生图响应没 b64_json 也没 url")
        import httpx  # noqa: WPS433

        r = httpx.get(url, timeout=60.0)
        r.raise_for_status()
        out.write_bytes(r.content)
    return out
