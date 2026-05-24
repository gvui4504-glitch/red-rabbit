"""🐰 红兔 — 小红书封面 AI 体检（Streamlit 单页 app）.

启动：
    streamlit run app.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import streamlit as st

import ai

_HERE = Path(__file__).parent
_LOGO = _HERE / "assets" / "red-rabbit.png"


# ============================================================
# 全局 CSS — 红白配色精细化
# ============================================================
_CUSTOM_CSS = """
<style>
/* 隐藏 Streamlit 默认 header / footer，让页面更"产品化" */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stHeader"] {background: transparent;}

/* 主标题加红色下划线 */
h1 {
    color: #1F1F1F;
    font-weight: 800 !important;
    border-bottom: 3px solid #FF2442;
    padding-bottom: 0.3em;
    margin-bottom: 0.8em;
}

/* h2 加左边红条 */
h2 {
    color: #1F1F1F;
    padding-left: 14px !important;
    border-left: 5px solid #FF2442;
    margin-top: 1.2em !important;
}

h3 {
    color: #1F1F1F;
    margin-top: 1em !important;
}

/* st.metric 值变红 + 加粗 */
[data-testid="stMetricValue"] {
    color: #FF2442 !important;
    font-weight: 800 !important;
}
[data-testid="stMetricLabel"] {
    color: #666 !important;
    font-weight: 500;
}

/* Primary 按钮：实心红 + 阴影 + hover 提升 */
.stButton > button[kind="primary"] {
    background-color: #FF2442;
    color: white;
    border: none;
    border-radius: 999px;
    padding: 0.6em 1.5em;
    font-weight: 600;
    box-shadow: 0 4px 14px rgba(255, 36, 66, 0.35);
    transition: all 0.15s ease;
}
.stButton > button[kind="primary"]:hover {
    background-color: #E61E3A;
    box-shadow: 0 6px 20px rgba(255, 36, 66, 0.45);
    transform: translateY(-2px);
}
.stButton > button[kind="primary"]:disabled {
    background-color: #FFB8C5;
    box-shadow: none;
    color: white;
}

/* Secondary 按钮：白底红边 */
.stButton > button:not([kind="primary"]) {
    background-color: #FFFFFF;
    color: #FF2442;
    border: 1.5px solid #FFB8C5;
    border-radius: 999px;
    font-weight: 500;
    transition: all 0.15s;
}
.stButton > button:not([kind="primary"]):hover {
    border-color: #FF2442;
    background-color: #FFF5F7;
}

/* 文件上传区：淡粉底 + 红色虚线边 */
[data-testid="stFileUploaderDropzone"] {
    background-color: #FFF7F8;
    border: 2px dashed #FFB8C5;
    border-radius: 12px;
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: #FF2442;
    background-color: #FFEFF1;
}

/* 进度条变红 */
.stProgress > div > div > div > div {
    background-color: #FF2442 !important;
}

/* Expander 边框圆角 */
[data-testid="stExpander"] {
    border-radius: 10px;
    border: 1px solid #FFE0E5;
}

/* Info / success / error 卡片更圆 */
[data-testid="stAlert"] {
    border-radius: 10px;
}

/* Sidebar 整体 */
[data-testid="stSidebar"] {
    background-color: #FFF7F8;
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    border: none;
    padding-left: 0;
    color: #FF2442;
}

/* Caption 颜色 */
.caption, [data-testid="stCaptionContainer"] {
    color: #888;
}

/* 表格圆角（如果有用到） */
[data-testid="stTable"] {
    border-radius: 10px;
    overflow: hidden;
}
</style>
"""


def _inject_styles() -> None:
    """注入全局 CSS。每次 rerun 都会跑一次（Streamlit 限制），但很轻量。"""
    st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)

# 5 维度展示元信息
_DIMENSIONS = [
    ("visual_impact", "⚡ 视觉冲击", "首屏 0.3 秒抓眼能力"),
    ("text", "📝 文字呈现", "字体 / 字号 / 位置 / 对比度"),
    ("composition", "🎯 构图主体", "主体突出 / 留白 / 构图法则"),
    ("color", "🎨 色彩情绪", "色调统一 / 饱和度 / 情绪"),
    ("xhs_vibe", "✨ 小红书味", "清新 / 真实 / 精致感的平衡"),
]


def _score_emoji(score: int) -> str:
    if score >= 85:
        return "🟢"
    if score >= 70:
        return "🟡"
    if score >= 50:
        return "🟠"
    return "🔴"


def _score_grade(score: int) -> str:
    if score >= 90:
        return "S 神级"
    if score >= 80:
        return "A 优秀"
    if score >= 70:
        return "B 良好"
    if score >= 60:
        return "C 及格"
    if score >= 40:
        return "D 待改"
    return "F 重做"


def _reset_diagnosis() -> None:
    for k in ("diagnosis", "image_bytes", "improved_path"):
        st.session_state.pop(k, None)


# ============================================================
# 🩺 诊断页
# ============================================================
def render_diagnose() -> None:
    # 红底 hero banner
    st.markdown(
        """
        <div style='background: linear-gradient(135deg, #FF2442 0%, #FF6B7E 100%);
                    padding: 1.8em 2em; border-radius: 18px; margin-bottom: 1.5em;
                    box-shadow: 0 6px 24px rgba(255, 36, 66, 0.25);'>
            <div style='font-size:2.2em; font-weight:800; color:white; line-height:1.1;'>
                🩺 封面体检室
            </div>
            <div style='color:rgba(255,255,255,0.92); margin-top:0.4em; font-size:1.05em;'>
                两步走：①上传封面 → 🔬 AI 评分诊断　　②看完处方 → 🪄 在原图上生成改进版
            </div>
            <div style='color:rgba(255,255,255,0.8); margin-top:0.6em; font-size:0.9em;'>
                ⚡ 视觉冲击　📝 文字呈现　🎯 构图主体　🎨 色彩情绪　✨ 小红书味
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not ai.has_any_key():
        st.error("⚠️ 没有可用的 OpenAI key，去 ⚙️ 设置填一个")
        return

    # 配额条（仅在受限模式下显示，无限模式 sidebar 已有）
    a_left = ai.remaining_analyze()
    i_left = ai.remaining_image()
    if a_left != -1:
        c1, c2, c3 = st.columns([1, 1, 2])
        c1.metric("剩余诊断", f"{a_left} / {ai.DEFAULT_QUOTA_ANALYZE}")
        c2.metric("剩余生图", f"{i_left} / {ai.DEFAULT_QUOTA_IMAGE}")
        with c3:
            st.caption(
                "⚙️ 用完了？设置页填自己的 OpenAI key 或输入解锁码即可继续"
            )

    # 上传区
    col_up, col_preview = st.columns([3, 2])
    with col_up:
        uploaded = st.file_uploader(
            "📤 上传封面图（PNG / JPG / WEBP，建议 ≤ 5MB）",
            type=["png", "jpg", "jpeg", "webp"],
            key="cover_uploader",
            on_change=_reset_diagnosis,
        )
        title = st.text_input(
            "📝 笔记标题（可选）",
            placeholder="比如：3 天瘦 5 斤的早餐秘籍",
            help="告诉 AI 这张封面对应的标题，能给出更精准的诊断",
        )
    with col_preview:
        if uploaded:
            st.image(uploaded, caption="原始封面", use_container_width=True)

    if not uploaded:
        st.info("👆 先上传一张封面图")
        return

    # ===== 第 1 步：只跑 AI 评分诊断 =====
    can_diagnose = (a_left != 0)
    btn1_label = "🔬 第 1 步：AI 评分诊断"
    if not can_diagnose:
        btn1_label = "❌ 诊断次数已用完（去 ⚙️ 设置填自己 key 或解锁）"

    if st.button(
        btn1_label,
        type="primary",
        use_container_width=True,
        disabled=not can_diagnose,
        key="btn_analyze",
    ):
        image_bytes = uploaded.getvalue()
        with st.spinner("AI 医师正在体检（约 5-15 秒）..."):
            try:
                result = ai.analyze_cover(image_bytes, title=title)
                st.session_state["diagnosis"] = result
                st.session_state["image_bytes"] = image_bytes
                # 重新做诊断 → 清掉上次的改进图，避免错位对应
                st.session_state.pop("improved_path", None)
                st.session_state.pop("generate_error", None)
                st.rerun()
            except ai.NoQuotaError as e:
                st.error(f"❌ {e}")
            except json.JSONDecodeError:
                st.error("AI 返回的 JSON 格式坏了，请重试一次")
            except Exception as e:
                st.error(f"❌ 诊断失败：{type(e).__name__}: {e}")

    # 诊断结果
    result = st.session_state.get("diagnosis")
    if not result:
        return

    st.markdown("---")
    st.markdown("## 🏥 诊断报告")

    overall = int(result.get("overall_score", 0))
    col_s, col_c = st.columns([1, 3])
    with col_s:
        st.metric(
            "综合评分",
            f"{overall}",
            delta=f"{_score_emoji(overall)} {_score_grade(overall)}",
            delta_color="off",
        )
    with col_c:
        st.info(f"💬 **总体诊断**：{result.get('overall_comment', '')}")

    # 5 维度
    st.markdown("### 📊 各项体检")
    dimensions = result.get("dimensions", {}) or {}
    for key, label, sub in _DIMENSIONS:
        d = dimensions.get(key, {}) or {}
        score = int(d.get("score", 0))
        with st.expander(
            f"{label} — **{score}/100** {_score_emoji(score)}", expanded=True
        ):
            st.caption(sub)
            st.markdown(f"**🔍 病灶**：{d.get('diagnosis', '（AI 没给出）')}")
            st.markdown(f"**💊 处方**：{d.get('prescription', '（AI 没给出）')}")
            st.progress(score / 100)

    # 整体处方
    prescriptions = result.get("prescriptions", []) or []
    if prescriptions:
        st.markdown("### 💊 整体处方建议")
        for i, p in enumerate(prescriptions, 1):
            st.markdown(f"**{i}.** {p}")

    # ===== 第 2 步：按处方生成改进图 =====
    st.markdown("---")
    st.markdown("## 🪄 第 2 步：按处方生成改进版")
    improvement_prompt = result.get("improvement_prompt", "")

    improved_path = st.session_state.get("improved_path")
    gen_err = st.session_state.get("generate_error")

    if improved_path and Path(improved_path).exists():
        # ===== 已经生成过，显示原图 vs 改进图 对比 =====
        col_orig, col_new = st.columns(2)
        with col_orig:
            st.markdown("**📍 原图**")
            if st.session_state.get("image_bytes"):
                st.image(
                    st.session_state["image_bytes"],
                    use_container_width=True,
                )
        with col_new:
            st.markdown("**🆕 AI 改进版**")
            st.image(improved_path, use_container_width=True)
            with open(improved_path, "rb") as f:
                st.download_button(
                    "💾 下载改进图",
                    data=f.read(),
                    file_name=Path(improved_path).name,
                    mime="image/png",
                    use_container_width=True,
                )

        st.caption(
            "⚠️ AI 改进图仅供参考，主体大致保留但细节会变。建议作为修改方向，自己再做二次创作。"
        )

        if i_left != 0:
            if st.button(
                "🔄 再生成一版（消耗 1 次生图）",
                use_container_width=True,
                key="btn_regenerate",
            ):
                original_bytes = st.session_state.get("image_bytes")
                if not original_bytes or not improvement_prompt:
                    st.error("找不到原图或 prompt，重新上传 + 诊断一次")
                else:
                    with st.spinner("AI 正在按处方重新作画（约 15-30 秒）..."):
                        try:
                            ts = int(time.time())
                            out = ai.ai_covers_dir() / f"improved_{ts}.png"
                            ai.generate_improved_cover(
                                improvement_prompt, original_bytes, out
                            )
                            st.session_state["improved_path"] = str(out)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 生图失败：{type(e).__name__}: {e}")

    else:
        # ===== 还没生过图：显示生图按钮（独立的第 2 步）=====
        if gen_err:
            st.warning(f"⚠️ 上次生图失败：{gen_err}")

        btn2_label = "🪄 在原图基础上生成改进版"
        can_generate = (i_left != 0) and bool(improvement_prompt)
        if i_left == 0:
            btn2_label = "❌ 生图次数已用完"
        elif not improvement_prompt:
            btn2_label = "⚠️ 诊断结果缺 improvement_prompt，重做第 1 步"

        if st.button(
            btn2_label,
            type="primary",
            use_container_width=True,
            disabled=not can_generate,
            key="btn_generate",
        ):
            original_bytes = st.session_state.get("image_bytes")
            if not original_bytes:
                st.error("❌ 找不到原图，请重新上传并重做第 1 步")
            else:
                with st.spinner("AI 正在按处方在原图上修改（约 15-30 秒）..."):
                    try:
                        ts = int(time.time())
                        out = ai.ai_covers_dir() / f"improved_{ts}.png"
                        ai.generate_improved_cover(
                            improvement_prompt, original_bytes, out
                        )
                        st.session_state["improved_path"] = str(out)
                        st.session_state.pop("generate_error", None)
                        st.rerun()
                    except ai.NoQuotaError as e:
                        st.session_state["generate_error"] = str(e)
                        st.rerun()
                    except Exception as e:
                        st.session_state["generate_error"] = (
                            f"{type(e).__name__}: {e}"
                        )
                        st.rerun()

    # AI 给图像模型的 prompt（高级用户可看）— 折叠在最底
    with st.expander("📜 AI 给图像模型的 prompt（高级用户可参考）", expanded=False):
        st.code(improvement_prompt or "（空）", language="text")


# ============================================================
# ⚙️ 设置页
# ============================================================
def render_settings() -> None:
    # 红底 hero（更小、更安静的版本，因为设置页不是主舞台）
    st.markdown(
        """
        <div style='background: linear-gradient(135deg, #FF6B7E 0%, #FFB8C5 100%);
                    padding: 1.2em 1.8em; border-radius: 16px; margin-bottom: 1.5em;'>
            <div style='font-size:1.6em; font-weight:700; color:white;'>
                ⚙️ 设置
            </div>
            <div style='color:rgba(255,255,255,0.92); margin-top:0.2em; font-size:0.95em;'>
                解锁码 / OpenAI key / base URL — 都在这里改
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cfg = ai.load_config()

    # 配额状态
    st.subheader("📊 当前配额")
    if ai.is_unlimited():
        st.success("✨ 无限次模式（已解锁）")
    elif ai.is_using_user_key():
        st.success("✨ 用户 key 模式（用你自己的额度）")
    else:
        c1, c2 = st.columns(2)
        c1.metric("剩余诊断", f"{ai.remaining_analyze()} / {ai.DEFAULT_QUOTA_ANALYZE}")
        c2.metric("剩余生图", f"{ai.remaining_image()} / {ai.DEFAULT_QUOTA_IMAGE}")

    st.markdown("---")

    # 解锁码
    st.subheader("🔓 解锁码")
    code = st.text_input("输入解锁码（一次性，永久解锁无限次）", type="password")
    if st.button("解锁"):
        ok, msg = ai.try_unlock(code)
        (st.success if ok else st.error)(msg)
        if ok:
            time.sleep(0.5)
            st.rerun()

    st.markdown("---")

    # 自己的 key
    st.subheader("🔑 用自己的 OpenAI Key（不限次，用你自己的钱）")
    new_key = st.text_input(
        "OpenAI API Key（sk-... 开头）",
        value=cfg.get("openai_api_key", ""),
        type="password",
    )
    new_url = st.text_input(
        "OpenAI Base URL（可选，国内中转代理用）",
        value=cfg.get("openai_base_url", ""),
        placeholder="https://api.openai.com/v1（默认）",
    )
    col_save, col_test = st.columns(2)
    if col_save.button("💾 保存"):
        ai.save_config(
            {"openai_api_key": new_key.strip(), "openai_base_url": new_url.strip()}
        )
        st.success("已保存")
        time.sleep(0.5)
        st.rerun()
    if col_test.button("🔌 测试连接"):
        with st.spinner("ping ..."):
            ok, msg = ai.test_connection()
            (st.success if ok else st.error)(msg)


# ============================================================
# main
# ============================================================
def main() -> None:
    # page icon 用本地 PNG（红底白兔），没有就 fallback 到 emoji
    page_icon = str(_LOGO) if _LOGO.exists() else "🐰"
    st.set_page_config(
        page_title="红兔 · 小红书封面诊断",
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    _inject_styles()

    # ===== Sidebar =====
    with st.sidebar:
        # 顶部 logo + 名字
        if _LOGO.exists():
            col_logo, col_name = st.columns([1, 2])
            with col_logo:
                st.image(str(_LOGO), width=64)
            with col_name:
                st.markdown(
                    "<h1 style='margin:0; padding:0; font-size:2em;'>红兔</h1>"
                    "<div style='color:#888; font-size:0.85em; margin-top:-4px;'>"
                    "小红书封面 AI 体检</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.title("🐰 红兔")
            st.caption("小红书封面 AI 体检")

        st.markdown("<hr style='margin:1em 0; border-color:#FFE0E5;'>", unsafe_allow_html=True)

        if "page" not in st.session_state:
            st.session_state["page"] = "🩺 封面诊断"

        PAGES = ["🩺 封面诊断", "⚙️ 设置"]
        page = st.radio(
            "导航", PAGES, key="page", label_visibility="collapsed"
        )

        st.markdown("<hr style='margin:1em 0; border-color:#FFE0E5;'>", unsafe_allow_html=True)

        # 状态卡片
        if ai.is_unlimited():
            st.success("✨ 无限次模式")
        elif ai.is_using_user_key():
            st.info("🔑 用户 key 模式")
        else:
            a, i = ai.remaining_analyze(), ai.remaining_image()
            st.markdown(
                f"""
                <div style='background:#FFFFFF; padding:12px 14px; border-radius:10px;
                            border:1px solid #FFE0E5;'>
                    <div style='font-weight:600; color:#FF2442; margin-bottom:6px;'>📊 免费配额</div>
                    <div style='font-size:0.9em; color:#444;'>
                        诊断 <b style='color:#FF2442;'>{a}</b> / {ai.DEFAULT_QUOTA_ANALYZE}<br>
                        生图 <b style='color:#FF2442;'>{i}</b> / {ai.DEFAULT_QUOTA_IMAGE}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if page == "🩺 封面诊断":
        render_diagnose()
    else:
        render_settings()


if __name__ == "__main__":
    main()
