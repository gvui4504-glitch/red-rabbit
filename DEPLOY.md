# 部署到 Streamlit Community Cloud

5 分钟把红兔变成一个公网可访问的 URL。

## 准备

- 一个 [GitHub](https://github.com) 账号
- 一把 [OpenAI API Key](https://platform.openai.com/api-keys)
- **去 https://platform.openai.com/account/limits 把月限额砍到 $3** ← 上云之前必做，否则被刷爆账单

## 第 1 步：把代码推到 GitHub

```powershell
cd "C:\Users\SFII\Documents\red rabbit"

# 初始化（如果还没初始化）
git init
git add .
git commit -m "initial commit"

# 在 GitHub 上建一个新 repo（红兔，可以叫 red-rabbit），不要勾 README/license
# 假设你建的是 https://github.com/<你的用户名>/red-rabbit

git branch -M main
git remote add origin https://github.com/<你的用户名>/red-rabbit.git
git push -u origin main
```

> ⚠️ **push 前先检查**：`config.json` 不能在提交里（.gitignore 已经排除，但确认一下 `git status` 没看到它）

## 第 2 步：部署 Streamlit Cloud

1. 打开 https://share.streamlit.io/
2. 用 GitHub 账号登录
3. 点 **「New app」**
4. 选你刚推的 repo `<你的用户名>/red-rabbit`，分支 `main`，主文件 `app.py`
5. 点 **「Advanced settings」** → **「Secrets」**，把这段粘进去（**替换成你的 key**）：
   ```toml
   openai_api_key = "sk-proj-换成你自己的 key"
   openai_base_url = ""
   ```
6. 点 **「Deploy」**
7. 等 2-5 分钟，会拿到一个 URL：`https://red-rabbit-xxxx.streamlit.app/`

## 第 3 步：验证 + 分享

打开 URL，应该看到 🐰 红兔。上传一张封面试一下。

把 URL 发给朋友 / 评委即可。

## 国内访问

`*.streamlit.app` 在国内访问**不稳定**（时通时不通）。如果朋友主要在国内：

- 让他们用 VPN 试一下
- 或者迁到 [Hugging Face Spaces](https://huggingface.co/spaces)（部署流程类似）

## 后续更新

改完代码后：

```powershell
git add .
git commit -m "改了 xxx"
git push
```

Streamlit Cloud 会**自动检测 push 并重新部署**，无需手动操作。

## 风险提醒

- 你的 OpenAI key **在 Streamlit Secrets 里安全**（不会出现在代码/前端）
- 但任何人通过 URL 都能调用你的 key，**月限额是唯一防线**
- 黑客松 demo 后，如果不再使用，**去 Streamlit Cloud 删掉 app 或在 OpenAI 撤销那把 key**

## 常见问题

### Q: Deploy 时报错 "ModuleNotFoundError: No module named 'PIL'"
A: 检查 `requirements.txt` 有没有 push 上 GitHub。这文件 Streamlit Cloud 用来装依赖。

### Q: app 起来了但「⚙️ 设置」显示「没有可用的 OpenAI key」
A: Secrets 面板的 key 没填或者填错。回到 Streamlit Cloud → app → Settings → Secrets 重新粘 + reboot app。

### Q: 我想让自己用无限次（解锁码）
A: app 起来后进 ⚙️ 设置 → 输入解锁码 `redrabbit2026` → 解锁。但 Streamlit Cloud 容器重启会丢失（quota.json 是临时文件系统），需要每次重启后重新解锁。
