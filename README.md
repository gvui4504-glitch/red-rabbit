# 🐰 红兔 — 小红书封面 AI 体检

上传一张小红书封面 → AI 一通煞有介事的分析 → 给评分 + 处方 → 一键生成改进版。

## 一句话定位

把"做封面"这件事拆成「**先让 AI 体检 → 看处方 → 自己改 / AI 直接出改进版参考**」三步。专门针对**小红书**，没有多平台幻想。

## 工作流

```
[你上传封面图]
    ↓
[GPT-4o-mini 视觉分析]
    ↓
5 维度评分（视觉冲击 / 文字 / 构图 / 色彩 / 小红书味）
+ 综合评分（S/A/B/C/D/F 等级）
+ 每维度「缺点 + 处方」
+ 整体处方 3-5 条
    ↓
（可选）按处方调 gpt-image-2 生成改进版
```

## 快速开始

### 双击式启动

1. 双击 `setup.bat` — 一键装 Python（没装的话用 winget 自动装）+ 装依赖
2. 装完会自动启动 `start.bat`
3. 浏览器自动打开 `http://localhost:8501`
4. 点 🩺 封面诊断 → 上传图 → 「开始 AI 诊断」

### 或者手动

```powershell
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
streamlit run app.py
```

## 配额机制（沿用「免费试 + 解锁 + 用户自带 key」三档）

| 模式 | 触发条件 | 用量 |
|---|---|---|
| 默认免费 | 啥也不动 | 5 次诊断 + 3 次生图（用作者 key） |
| 解锁无限 | ⚙️ 设置里输解锁码 | 无限次（仍用作者 key） |
| 用户 key | ⚙️ 设置里填自己的 sk-... | 无限次（用你自己的钱） |

解锁码：`redrabbit2026`

## 项目结构

```
red rabbit/
├── app.py              # Streamlit UI（诊断页 + 设置页）
├── ai.py               # OpenAI 调用 + 配额管理（全部在这里）
├── requirements.txt    # 三个包：streamlit / openai / pillow
├── config.json         # 用户填的 key + base_url（首次运行自动从 example 复制）
├── config.example.json
├── setup.bat / start.bat
└── data/
    ├── quota.json      # 配额计数
    └── ai_covers/      # 生成的改进版图
```

## 国内访问 OpenAI

默认走 `api.openai.com`，国内网络多数情况下要 VPN。如果没 VPN：

- 在 ⚙️ 设置 → 填一个 OpenAI **中转代理** 的 `base_url`（自己买 / 朋友共享）
- 或者用了 Clash 之类的代理走全局模式

## 给朋友分发

```powershell
Compress-Archive -Path app.py,ai.py,requirements.txt,config.example.json,*.bat,README.md -DestinationPath red-rabbit.zip
```

注意：**不要打包 `config.json`**（你的 key 在里面）和 **`data/quota.json`**（你的用量记录）。

## License

MIT
