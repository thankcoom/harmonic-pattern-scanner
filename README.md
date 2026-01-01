# Harmonic Pattern Scanner

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Exchange-Binance-yellow.svg" alt="Binance">
  <img src="https://img.shields.io/badge/Deploy-Zeabur-7B68EE.svg" alt="Zeabur">
</p>

> 加密貨幣諧波形態自動掃描器 - 掃描幣安永續合約市場，識別 8 種經典諧波形態，並透過 Discord 即時通知
>
> 支援一鍵部署到 Zeabur、Railway、Render 等雲端平台

**作者**: Louis_LAB | **Instagram**: [@mr.__.l](https://www.instagram.com/mr.__.l)

---

## 功能特色

- **8 種諧波形態識別**
  - 蝙蝠形態 (Bat) - 看漲/看跌
  - 加特里形態 (Gartley) - 看漲/看跌
  - 螃蟹形態 (Crab) - 看漲/看跌
  - 蝴蝶形態 (Butterfly) - 看漲/看跌

- **完整交易參數**
  - PRZ 進場區間
  - Stop Loss 止損位
  - TP1/TP2/TP3 三階段獲利目標
  - 風險回報比 (R:R) 自動計算

- **Discord 即時通知**
  - 美觀的 Embed 卡片式訊息
  - 幣種圖標顯示
  - 掃描完成摘要報告

- **彈性執行方式**
  - 手動單次掃描
  - 定時自動執行

---

## 諧波形態說明

諧波形態是基於斐波那契比例的價格形態，用於預測潛在的價格反轉區域。

| 形態 | AB 回撤 | PRZ 位置 | 特性 |
|------|---------|----------|------|
| **蝙蝠 (Bat)** | 0.382-0.5 XA | 0.886 XA | 最常見，成功率較高 |
| **加特里 (Gartley)** | 0.618 XA | 0.786 XA | 經典形態，精確度高 |
| **螃蟹 (Crab)** | 0.382-0.618 XA | 1.618 XA | 延伸形態，利潤空間大 |
| **蝴蝶 (Butterfly)** | 0.786 XA | 1.27 XA | 延伸形態，較為激進 |

### 形態結構圖

```
看漲形態 (M形):          看跌形態 (W形):

    B                        X───────A
   /\                              /
  /  \      D                     /
 /    \    /                     B
X      \  /                       \
        \/                         \      D
        C                           \    /
                                     \  /
                                      \/
                                      C
```

---

## 快速開始

### 方式一：雲端部署（推薦）

一鍵部署到 Zeabur，24/7 自動運行：

[![Deploy on Zeabur](https://zeabur.com/button.svg)](https://zeabur.com/templates/harmonic-scanner)

**Zeabur 手動部署步驟：**

1. 前往 [Zeabur](https://zeabur.com) 註冊/登入
2. 創建新專案 → 選擇「從 GitHub 導入」
3. 選擇此 Repository
4. 在環境變數中設定：
   - `DISCORD_WEBHOOK_URL`: 你的 Discord Webhook URL（**必填**）
   - `CLOUD_MODE`: `true`（自動排程模式）
   - `HARMONIC_TIMEFRAME`: `1h`（掃描週期）
   - `SCHEDULE_INTERVAL`: `240`（掃描間隔，分鐘）
5. 部署完成！

### 方式二：本地執行

#### 1. 安裝依賴套件

```bash
pip install -r requirements.txt
```

#### 2. 設定 Discord Webhook

1. 在 Discord 頻道設定中，選擇「整合」→「Webhook」
2. 點擊「新 Webhook」並複製 URL
3. 設定環境變數（推薦）或直接修改程式碼：

```bash
# Linux/Mac
export DISCORD_WEBHOOK_URL="你的_WEBHOOK_URL"

# Windows PowerShell
$env:DISCORD_WEBHOOK_URL="你的_WEBHOOK_URL"
```

#### 3. 執行掃描

```bash
# 單次掃描
python harmonic_scanner.py

# 或
python harmonic_scanner.py scan
```

---

## 使用方式

### 命令列參數

| 命令 | 說明 |
|------|------|
| `python harmonic_scanner.py` | 執行單次掃描 |
| `python harmonic_scanner.py scan` | 執行單次掃描 |
| `python harmonic_scanner.py auto` | 啟動定時自動掃描 |
| `python harmonic_scanner.py test` | 測試 Discord 連接 |
| `python harmonic_scanner.py help` | 顯示使用說明 |

### 設定參數

在 `harmonic_scanner.py` 中的 `CONFIG` 字典：

```python
CONFIG = {
    # 掃描時間框架（1h, 4h, 1d 等）
    "harmonic_timeframe": "1h",

    # K線數據數量
    "limit": 500,

    # 峰值檢測靈敏度（數值越大越不敏感，建議 8-15）
    "peak_order": 10,

    # 定時執行間隔（分鐘）
    "schedule_interval_minutes": 240,

    # 是否啟用詳細日誌
    "verbose": True,
}
```

#### 參數調整建議

| 參數 | 建議值 | 說明 |
|------|--------|------|
| `harmonic_timeframe` | `1h` / `4h` | 短線用 1h，波段用 4h |
| `peak_order` | `8-12` | 較小值會檢測更多形態，但可能有雜訊 |
| `limit` | `300-500` | K線數量，太少可能遺漏形態 |

---

## 環境變數（雲端部署用）

| 變數名稱 | 必填 | 預設值 | 說明 |
|----------|------|--------|------|
| `DISCORD_WEBHOOK_URL` | ✅ | - | Discord Webhook URL |
| `CLOUD_MODE` | - | `false` | 設為 `true` 啟用自動排程 |
| `HARMONIC_TIMEFRAME` | - | `1h` | 掃描時間框架 |
| `SCHEDULE_INTERVAL` | - | `240` | 掃描間隔（分鐘） |
| `PEAK_ORDER` | - | `10` | 峰值檢測靈敏度 |
| `KLINE_LIMIT` | - | `500` | K線數據數量 |
| `VERBOSE` | - | `true` | 詳細日誌 |

---

## Discord 通知範例

### 信號通知

```
┌─────────────────────────────────────┐
│  Louis 掃描器 | 諧波形態              │
├─────────────────────────────────────┤
│  [LONG] 看漲蝙蝠 | Bullish Bat      │
│                                     │
│  ══════════════════════════════════ │
│     BTC/USDT 永續合約                │
│  ══════════════════════════════════ │
│                                     │
│  發現 看漲蝙蝠 諧波形態               │
│  建議方向: LONG 做多                 │
│                                     │
│  交易對: BTC/USDT    方向: LONG     │
│  週期: 1h                           │
│                                     │
│  ━━━━━ 交易參數 ━━━━━               │
│  進場區 PRZ: 42000.0000             │
│  止損 SL: 41500.0000                │
│                                     │
│  ━━━━━ 獲利目標 ━━━━━               │
│  TP1 (R:R 1.5): 42750.0000          │
│  TP2 (R:R 2.0): 43000.0000          │
│  TP3 (R:R 2.5): 43250.0000          │
└─────────────────────────────────────┘
```

---

## 注意事項

> **免責聲明**: 本工具僅供學習和研究使用，不構成任何投資建議。加密貨幣交易具有高風險，請謹慎操作，自行承擔盈虧。

- 諧波形態並非 100% 準確，建議搭配其他技術分析工具使用
- 建議先用小倉位測試，熟悉形態特性後再加大操作
- PRZ 是「區間」而非精確點位，可分批進場
- 務必嚴格執行止損

---

## 常見問題

### Q: 為什麼掃描沒有發現任何形態？

A: 諧波形態需要符合嚴格的斐波那契比例，在某些時段可能確實沒有符合條件的形態。可以嘗試：
- 調整 `peak_order` 參數（降低數值）
- 更換時間框架
- 耐心等待市場形成新形態

### Q: Discord 通知發送失敗？

A: 請檢查：
1. Webhook URL 是否正確
2. 網路連接是否正常
3. 執行 `python harmonic_scanner.py test` 測試連接

### Q: 如何同時監控多個時間框架？

A: 可以開啟多個終端，分別執行不同時間框架的掃描：
```bash
# 終端 1
python harmonic_scanner.py  # 使用預設 1h

# 終端 2（修改 CONFIG 後）
python harmonic_scanner.py  # 使用 4h
```

---

## 技術棧

- **Python 3.8+**
- **ccxt** - 交易所 API 連接
- **pandas** - 數據處理
- **numpy** - 數值計算
- **scipy** - 峰值檢測
- **requests** - HTTP 請求
- **schedule** - 定時任務

---

## 貢獻

歡迎提交 Issue 和 Pull Request！

如果這個項目對你有幫助，請給個 Star 支持一下！

---

## 授權

MIT License

---

## 聯繫方式

- **Instagram**: [@mr.__.l](https://www.instagram.com/mr.__.l)
- **Author**: Louis_LAB

---

<p align="center">
  <b>Happy Trading!</b>
</p>
