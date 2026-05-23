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
    st.title("🩺 红兔 · 封面体检")
    st.caption("上传你的小红书封面，AI 医师给个体检 + 处方 + 改进版预览")

    if not ai.has_any_key():
        st.error("⚠️ 没有可用的 OpenAI key，去 ⚙️ 设置填一个")
        return

    # 配额条
    a_left = ai.remaining_analyze()
    i_left = ai.remaining_image()
    if a_left == -1:
        st.success("✨ 无限次模式")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("剩余诊断次数", f"{a_left} / {ai.DEFAULT_QUOTA_ANALYZE}")
        c2.metric("剩余生图次数", f"{i_left} / {ai.DEFAULT_QUOTA_IMAGE}")
        with c3:
            st.caption("⚙️ 用完了？设置页填自己的 key 或输解锁码")

    st.markdown("---")

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

    # 诊断按钮
    btn_label = "🔬 开始 AI 诊断"
    if a_left == 0:
        btn_label = "❌ 诊断次数已用完"
    if st.button(
        btn_label,
        type="primary",
        use_container_width=True,
        disabled=(a_left == 0),
    ):
        with st.spinner("AI 医师正在仔细体检（约 5-15 秒）..."):
            try:
                image_bytes = uploaded.getvalue()
                result = ai.analyze_cover(image_bytes, title=title)
                st.session_state["diagnosis"] = result
                st.session_state["image_bytes"] = image_bytes
                st.session_state.pop("improved_path", None)
                st.rerun()
            except ai.NoQuotaError as e:
                st.error(f"❌ {e}")
            except json.JSONDecodeError:
                st.error("AI 返回的 JSON 格式坏了，重试一次")
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

    # 改进版生图
    st.markdown("---")
    st.markdown("### 🪄 改进版预览")
    improvement_prompt = result.get("improvement_prompt", "")

    with st.expander("📜 AI 给图像模型的 prompt（高级用户可参考）", expanded=False):
        st.code(improvement_prompt or "（空）", language="text")

    improved_path = st.session_state.get("improved_path")
    if improved_path and Path(improved_path).exists():
        st.image(
            improved_path,
            caption="🆕 AI 改进版（仅供参考，需自行二次创作）",
            use_container_width=True,
        )
        with open(improved_path, "rb") as f:
            st.download_button(
                "💾 下载这张改进图",
                data=f.read(),
                file_name=Path(improved_path).name,
                mime="image/png",
            )
        if st.button("🔄 再生成一版"):
            st.session_state.pop("improved_path", None)
            st.rerun()
    else:
        gen_label = "🖼️ 按处方生成改进版封面"
        if i_left == 0:
            gen_label = "❌ 生图次数已用完"
        if st.button(
            gen_label,
            use_container_width=True,
            disabled=(i_left == 0 or not improvement_prompt),
        ):
            original_bytes = st.session_state.get("image_bytes")
            if not original_bytes:
                st.error("❌ 找不到原图，请重新上传并再做一次诊断")
            else:
                with st.spinner("AI 正在按处方在原图上修改（约 15-30 秒）..."):
                    try:
                        ts = int(time.time())
                        out = ai.ai_covers_dir() / f"improved_{ts}.png"
                        ai.generate_improved_cover(
                            improvement_prompt, original_bytes, out
                        )
                        st.session_state["improved_path"] = str(out)
                        st.rerun()
                    except ai.NoQuotaError as e:
                        st.error(f"❌ {e}")
                    except Exception as e:
                        st.error(f"❌ 生图失败：{type(e).__name__}: {e}")


# ============================================================
# ⚙️ 设置页
# ============================================================
def render_settings() -> None:
    st.title("⚙️ 设置")

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
    st.set_page_config(page_title="红兔", page_icon="🐰", layout="wide")

    st.sidebar.title("🐰 红兔")
    st.sidebar.caption("小红书封面 AI 体检")
    st.sidebar.markdown("---")

    if "page" not in st.session_state:
        st.session_state["page"] = "🩺 封面诊断"

    PAGES = ["🩺 封面诊断", "⚙️ 设置"]
    page = st.sidebar.radio(
        "导航", PAGES, key="page", label_visibility="collapsed"
    )

    # 侧边栏状态
    st.sidebar.markdown("---")
    if ai.is_unlimited():
        st.sidebar.success("✨ 无限次")
    elif ai.is_using_user_key():
        st.sidebar.info("🔑 用户 key")
    else:
        st.sidebar.markdown(
            f"**📊 配额**\n"
            f"- 诊断：{ai.remaining_analyze()} / {ai.DEFAULT_QUOTA_ANALYZE}\n"
            f"- 生图：{ai.remaining_image()} / {ai.DEFAULT_QUOTA_IMAGE}"
        )

    if page == "🩺 封面诊断":
        render_diagnose()
    else:
        render_settings()


if __name__ == "__main__":
    main()
