#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Louis 諧波形態掃描器
====================
專注於諧波形態識別，並透過 Discord Webhook 發送通知

功能：
- 8 種諧波形態掃描（蝙蝠、螃蟹、加特里、蝴蝶的看漲/看跌）
- Discord Embed 卡片式通知
- 支援手動執行與定時自動執行
- 支援雲端部署（Zeabur, Railway, Render 等）

作者：Louis_LAB / Instagram: @mr.__.l
"""

import os
import numpy as np
import pandas as pd
import ccxt
import time
import requests
import logging
import schedule
from datetime import datetime, timezone
from scipy.signal import argrelextrema

# ============================================================================
# 配置區 - 支援環境變數（雲端部署）或直接設定
# ============================================================================

# Discord Webhook URL（優先使用環境變數，方便雲端部署）
DISCORD_WEBHOOK_URL = os.environ.get(
    "DISCORD_WEBHOOK_URL",
    "你的_DISCORD_WEBHOOK_URL"  # 本地開發時可在此處填入
)

# 掃描設定（支援環境變數覆蓋）
CONFIG = {
    # 谐波形態掃描時間框架（支援：1h, 4h, 1d 等）
    "harmonic_timeframe": os.environ.get("HARMONIC_TIMEFRAME", "1h"),

    # K線數據數量
    "limit": int(os.environ.get("KLINE_LIMIT", "500")),

    # 峰值檢測靈敏度（數值越大越不敏感）
    "peak_order": int(os.environ.get("PEAK_ORDER", "10")),

    # 定時執行間隔（分鐘）
    "schedule_interval_minutes": int(os.environ.get("SCHEDULE_INTERVAL", "240")),

    # 是否啟用詳細日誌
    "verbose": os.environ.get("VERBOSE", "true").lower() == "true",
}

# 形態顏色配置（Discord Embed 顏色）
COLORS = {
    "看漲蝙蝠": 0x00FF00,      # 綠色
    "看跌蝙蝠": 0xFF0000,      # 紅色
    "看漲螃蟹": 0x00FF7F,      # 春綠色
    "看跌螃蟹": 0xFF4500,      # 橙紅色
    "看漲加特里": 0x32CD32,    # 檸檬綠
    "看跌加特里": 0xDC143C,    # 猩紅色
    "看漲蝴蝶": 0x7CFC00,      # 草地綠
    "看跌蝴蝶": 0xB22222,      # 火磚紅
}

# 作者資訊
AUTHOR_INFO = {
    "name": "Louis_LAB",
    "instagram": "https://www.instagram.com/mr.__.l",
    "icon_url": "https://i.imgur.com/AfFp7pu.png"
}

# ============================================================================
# 日誌設定
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================================
# Discord 通知模組
# ============================================================================

def get_coin_icon(symbol: str) -> str:
    """獲取幣種圖標 URL"""
    symbol_lower = symbol.lower().replace("/usdt", "")
    icons = {
        "btc": "https://assets.coingecko.com/coins/images/1/small/bitcoin.png",
        "eth": "https://assets.coingecko.com/coins/images/279/small/ethereum.png",
        "bnb": "https://assets.coingecko.com/coins/images/825/small/bnb-icon2_2x.png",
        "sol": "https://assets.coingecko.com/coins/images/4128/small/solana.png",
        "xrp": "https://assets.coingecko.com/coins/images/44/small/xrp-symbol-white-128.png",
        "doge": "https://assets.coingecko.com/coins/images/5/small/dogecoin.png",
        "ada": "https://assets.coingecko.com/coins/images/975/small/cardano.png",
        "avax": "https://assets.coingecko.com/coins/images/12559/small/Avalanche_Circle_RedWhite_Trans.png",
        "link": "https://assets.coingecko.com/coins/images/877/small/chainlink-new-logo.png",
        "dot": "https://assets.coingecko.com/coins/images/12171/small/polkadot.png",
        "matic": "https://assets.coingecko.com/coins/images/4713/small/polygon.png",
        "uni": "https://assets.coingecko.com/coins/images/12504/small/uni.jpg",
        "atom": "https://assets.coingecko.com/coins/images/1481/small/cosmos_hub.png",
        "ltc": "https://assets.coingecko.com/coins/images/2/small/litecoin.png",
        "etc": "https://assets.coingecko.com/coins/images/453/small/ethereum-classic-logo.png",
    }
    return icons.get(symbol_lower, "https://assets.coingecko.com/coins/images/1/small/bitcoin.png")


def send_discord_embed(embed_data: dict) -> bool:
    """
    發送 Discord Embed 訊息

    參數：
        embed_data: 完整的 embed 資料字典

    返回：
        bool: 是否發送成功
    """
    if DISCORD_WEBHOOK_URL == "你的_DISCORD_WEBHOOK_URL":
        logger.warning("請先設定 DISCORD_WEBHOOK_URL！")
        return False

    payload = {"embeds": [embed_data]}

    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 204:
            logger.info(f"Discord 通知發送成功：{embed_data.get('title', 'N/A')}")
            return True
        else:
            logger.error(f"Discord 通知發送失敗：{response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"Discord 通知發送異常：{str(e)}")
        return False


def send_harmonic_signal(pattern_name: str, symbol: str, prz: float, sl: float,
                         tp1: float, tp2: float, tp3: float, timeframe: str):
    """
    發送谐波形態信號到 Discord（美化版）
    """
    is_bullish = "看漲" in pattern_name
    direction = "LONG 做多" if is_bullish else "SHORT 做空"

    # 計算風險回報比
    risk = abs(prz - sl)
    reward1 = abs(tp1 - prz) if risk > 0 else 0
    reward2 = abs(tp2 - prz) if risk > 0 else 0
    reward3 = abs(tp3 - prz) if risk > 0 else 0
    rr1 = round(reward1 / risk, 2) if risk > 0 else 0
    rr2 = round(reward2 / risk, 2) if risk > 0 else 0
    rr3 = round(reward3 / risk, 2) if risk > 0 else 0

    # 形態名稱英文對照
    pattern_english = {
        "看漲蝙蝠": "Bullish Bat",
        "看跌蝙蝠": "Bearish Bat",
        "看漲加特里": "Bullish Gartley",
        "看跌加特里": "Bearish Gartley",
        "看漲螃蟹": "Bullish Crab",
        "看跌螃蟹": "Bearish Crab",
        "看漲蝴蝶": "Bullish Butterfly",
        "看跌蝴蝶": "Bearish Butterfly",
    }

    color = COLORS.get(pattern_name, 0x808080)
    pattern_en = pattern_english.get(pattern_name, pattern_name)

    # 構建 Embed
    embed = {
        "author": {
            "name": "Louis 掃描器 | 諧波形態",
            "url": AUTHOR_INFO["instagram"],
            "icon_url": AUTHOR_INFO["icon_url"]
        },
        "title": f"[{'LONG' if is_bullish else 'SHORT'}] {pattern_name} | {pattern_en}",
        "description": (
            f"```\n"
            f"{'═' * 35}\n"
            f"   {symbol}/USDT 永續合約\n"
            f"{'═' * 35}\n"
            f"```\n"
            f"發現 **{pattern_name}** 諧波形態\n"
            f"建議方向: **{direction}**"
        ),
        "color": color,
        "thumbnail": {
            "url": get_coin_icon(symbol)
        },
        "fields": [
            {"name": "交易對", "value": f"```{symbol}/USDT```", "inline": True},
            {"name": "方向", "value": f"```{direction}```", "inline": True},
            {"name": "週期", "value": f"```{timeframe}```", "inline": True},
            {"name": "\u200b", "value": "**━━━━━ 交易參數 ━━━━━**", "inline": False},
            {"name": "進場區 PRZ", "value": f"```yaml\n{prz:.8f}```", "inline": True},
            {"name": "止損 SL", "value": f"```diff\n- {sl:.8f}```", "inline": True},
            {"name": "\u200b", "value": "\u200b", "inline": True},
            {"name": "\u200b", "value": "**━━━━━ 獲利目標 ━━━━━**", "inline": False},
            {"name": f"TP1 (R:R {rr1})", "value": f"```diff\n+ {tp1:.8f}```", "inline": True},
            {"name": f"TP2 (R:R {rr2})", "value": f"```diff\n+ {tp2:.8f}```", "inline": True},
            {"name": f"TP3 (R:R {rr3})", "value": f"```diff\n+ {tp3:.8f}```", "inline": True},
        ],
        "footer": {
            "text": f"Louis 掃描器 | IG: @mr.__.l | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "icon_url": AUTHOR_INFO["icon_url"]
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    send_discord_embed(embed)


def send_scan_summary(harmonic_count: int, timeframe: str):
    """
    發送掃描摘要到 Discord
    """
    # 根據信號數量選擇狀態
    if harmonic_count == 0:
        status = "無信號"
        status_color = 0x808080
    elif harmonic_count <= 3:
        status = "少量信號"
        status_color = 0x3498DB
    elif harmonic_count <= 10:
        status = "活躍市場"
        status_color = 0xF39C12
    else:
        status = "大量機會"
        status_color = 0xE74C3C

    embed = {
        "author": {
            "name": "Louis 掃描器 | 掃描報告",
            "url": AUTHOR_INFO["instagram"],
            "icon_url": AUTHOR_INFO["icon_url"]
        },
        "title": f"諧波形態掃描完成 | {status}",
        "description": (
            f"```\n"
            f"{'═' * 35}\n"
            f"   掃描結果總覽\n"
            f"{'═' * 35}\n"
            f"```\n"
            f"本次掃描共發現 **{harmonic_count}** 個諧波形態信號\n\n"
            f"**Instagram**: [@mr.__.l]({AUTHOR_INFO['instagram']})"
        ),
        "color": status_color,
        "fields": [
            {"name": "諧波形態", "value": f"```yaml\n{harmonic_count} 個```", "inline": True},
            {"name": "掃描週期", "value": f"```{timeframe}```", "inline": True},
            {"name": "總計", "value": f"```fix\n{harmonic_count} 個信號```", "inline": True},
        ],
        "footer": {
            "text": f"Louis 掃描器 | IG: @mr.__.l | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "icon_url": AUTHOR_INFO["icon_url"]
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    send_discord_embed(embed)

# ============================================================================
# 數據收集模組
# ============================================================================

def get_exchange():
    """
    建立幣安期貨交易所連接
    """
    return ccxt.binance({
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future',
        }
    })


def collect_data(timeframe: str = '4h', limit: int = 500) -> pd.DataFrame:
    """
    收集所有 USDT 永續合約的 K線數據

    參數：
        timeframe: 時間框架（1h, 4h, 1d 等）
        limit: K線數量

    返回：
        包含所有幣種 OHLCV 數據的 DataFrame
    """
    logger.info(f"開始收集數據 | 時間框架: {timeframe} | K線數量: {limit}")

    exchange = get_exchange()

    # 獲取所有 USDT 永續合約
    all_coins = list(exchange.load_markets().keys())
    coins = [x for x in all_coins if "/USDT" in x and "_" not in x]

    logger.info(f"找到 {len(coins)} 個 USDT 交易對")

    all_candles = []
    success_count = 0
    total_coins = len(coins)
    progress_interval = max(1, total_coins // 10)

    for idx, symbol in enumerate(coins):
        try:
            df = pd.DataFrame(
                exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            )
            df['symbol'] = symbol
            df.columns = ['Datetime', 'Open', 'High', 'Low', 'Close', 'Vol', 'Symbol']

            # 時間轉換
            df['Datetime'] = df['Datetime'].apply(
                lambda x: time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(x / 1000.))
            )

            # 移除最後一根未完成的 K線
            df = df[:-1]

            all_candles.append(df)
            success_count += 1

            # 顯示進度
            if (idx + 1) % progress_interval == 0 or (idx + 1) == total_coins:
                progress = (idx + 1) / total_coins * 100
                logger.info(f"數據收集進度: {idx + 1}/{total_coins} ({progress:.0f}%)")

        except Exception as e:
            if CONFIG["verbose"]:
                logger.debug(f"跳過 {symbol}: {str(e)}")

    if not all_candles:
        logger.error("無法收集任何數據！")
        return pd.DataFrame()

    result = pd.concat(all_candles)
    result['Datetime'] = pd.to_datetime(result['Datetime'])

    logger.info(f"數據收集完成 | 成功: {success_count}/{len(coins)} 個交易對")

    return result

# ============================================================================
# 輔助函數
# ============================================================================

def list_to_string(s: list) -> str:
    """將列表轉換為字串"""
    return "".join(str(ele) for ele in s)

# ============================================================================
# 峰值檢測模組
# ============================================================================

def peak_detect(df: pd.DataFrame, order: int = 10):
    """
    檢測價格峰值，用於谐波形態識別

    參數：
        df: 單一幣種的 OHLCV 數據
        order: 峰值檢測的窗口大小

    返回：
        元組：(時間索引, 價格模式, 起始, 結束, 移動段, 高點, 低點, 最終數據, 幣種)
    """
    dt = df.Datetime
    df = df.set_index('Datetime')

    high = df.High
    low = df.Low

    # 使用 scipy 檢測局部極值
    max_idx = list(argrelextrema(high.values, np.greater, order=order)[0])
    min_idx = list(argrelextrema(low.values, np.less, order=order)[0])

    peak_1 = high.values[max_idx]
    peak_2 = low.values[min_idx]

    peaks_p = list(peak_1) + list(peak_2)
    peaks_idx = list(max_idx) + list(min_idx)

    peaks_idx_dt = np.array(dt.values[peaks_idx])
    peaks_p = np.array(peaks_p)

    final_df = pd.DataFrame({"price": peaks_p, "datetime": peaks_idx_dt})
    final_df = final_df.sort_values(by=['datetime'])

    peaks_idx_dt = final_df.datetime
    peaks_p = final_df.price

    # 組合最後 4 個峰值 + 當前價格
    current_idx = np.array(list(final_df.datetime[-4:]) + list(dt[-1:]))
    current_pat = np.array(list(final_df.price[-4:]) + list(low[-1:]))

    start = min(current_idx)
    end = max(current_idx)

    # 計算四段移動
    XA = current_pat[1] - current_pat[0]
    AB = current_pat[2] - current_pat[1]
    BC = current_pat[3] - current_pat[2]
    CD = current_pat[4] - current_pat[3]

    moves = [XA, AB, BC, CD]
    symbol = df['Symbol'].unique().tolist()

    return current_idx, current_pat, start, end, moves, high, low, final_df, symbol

# ============================================================================
# 谐波形態識別模組
# ============================================================================

def bull_bat(moves: list, symbol: list, current_pat: np.ndarray):
    """
    看漲蝙蝠形態識別

    斐波那契比例：
    - AB: 0.382-0.5 × XA
    - BC: 0.382-0.886 × AB
    - CD: 1.618-2.618 × BC
    """
    try:
        err_allowed = 0.1
        XA, AB, BC, CD = moves

        M_pat = (XA > 0 and AB < 0 and BC > 0 and CD < 0)

        AB_range = np.array([0.382 - err_allowed, 0.5 + err_allowed]) * abs(XA)
        BC_range = np.array([0.382 - err_allowed, 0.886 + err_allowed]) * abs(AB)
        CD_range = np.array([1.618 - err_allowed, 2.618 + err_allowed]) * abs(BC)

        PRZ = round(current_pat[1] - 0.886 * abs(XA), 4)
        SL = round(current_pat[0], 4)
        TP1 = round(current_pat[3] - 0.618 * abs(CD), 4)
        TP2 = round(current_pat[3] - 0.5 * abs(CD), 4)
        TP3 = round(current_pat[3] - 0.382 * abs(CD), 4)

        bat_pat = (
            AB_range[0] < abs(AB) < AB_range[1] and
            BC_range[0] < abs(BC) < BC_range[1] and
            abs(CD) >= 0.7 * abs(XA) and
            abs(CD) <= CD_range[1]
        )

        if M_pat and bat_pat:
            return list_to_string(symbol).replace("/USDT", ""), PRZ, SL, TP1, TP2, TP3
        return []

    except Exception:
        return []


def bear_bat(moves: list, symbol: list, current_pat: np.ndarray):
    """看跌蝙蝠形態識別"""
    try:
        err_allowed = 0.1
        XA, AB, BC, CD = moves

        W_pat = (XA < 0 and AB > 0 and BC < 0 and CD > 0)

        AB_range = np.array([0.382 - err_allowed, 0.5 + err_allowed]) * abs(XA)
        BC_range = np.array([0.382 - err_allowed, 0.886 + err_allowed]) * abs(AB)
        CD_range = np.array([1.618 - err_allowed, 2.618 + err_allowed]) * abs(BC)

        PRZ = round(current_pat[1] + 0.886 * abs(XA), 4)
        SL = round(current_pat[0], 4)
        TP1 = round(current_pat[3] + 0.618 * abs(CD), 4)
        TP2 = round(current_pat[3] + 0.5 * abs(CD), 4)
        TP3 = round(current_pat[3] + 0.382 * abs(CD), 4)

        bat_pat = (
            AB_range[0] < abs(AB) < AB_range[1] and
            BC_range[0] < abs(BC) < BC_range[1] and
            abs(CD) >= 0.7 * abs(XA) and
            abs(CD) <= CD_range[1]
        )

        if W_pat and bat_pat:
            return list_to_string(symbol).replace("/USDT", ""), PRZ, SL, TP1, TP2, TP3
        return []

    except Exception:
        return []


def bull_gartley(moves: list, symbol: list, current_pat: np.ndarray):
    """
    看漲加特里形態識別

    斐波那契比例：
    - AB: 0.618 × XA（精確）
    - BC: 0.382-0.886 × AB
    - CD: 1.272-1.618 × BC
    """
    try:
        err_allowed = 0.1
        XA, AB, BC, CD = moves

        M_pat = (XA > 0 and AB < 0 and BC > 0 and CD < 0)

        AB_range = np.array([0.618 - err_allowed, 0.618 + err_allowed]) * abs(XA)
        BC_range = np.array([0.382 - err_allowed, 0.886 + err_allowed]) * abs(AB)
        CD_range = np.array([1.272 - err_allowed, 1.618 + err_allowed]) * abs(BC)

        PRZ = round(current_pat[1] - 0.786 * abs(XA), 4)
        SL = round(current_pat[0], 4)
        TP1 = round(current_pat[3] - 0.618 * abs(CD), 4)
        TP2 = round(current_pat[3] - 0.5 * abs(CD), 4)
        TP3 = round(current_pat[3] - 0.382 * abs(CD), 4)

        gartley_pat = (
            AB_range[0] < abs(AB) < AB_range[1] and
            BC_range[0] < abs(BC) < BC_range[1] and
            abs(CD) >= 0.6 * abs(XA) and
            abs(CD) <= CD_range[1]
        )

        if M_pat and gartley_pat:
            return list_to_string(symbol).replace("/USDT", ""), PRZ, SL, TP1, TP2, TP3
        return []

    except Exception:
        return []


def bear_gartley(moves: list, symbol: list, current_pat: np.ndarray):
    """看跌加特里形態識別"""
    try:
        err_allowed = 0.1
        XA, AB, BC, CD = moves

        W_pat = (XA < 0 and AB > 0 and BC < 0 and CD > 0)

        AB_range = np.array([0.618 - err_allowed, 0.618 + err_allowed]) * abs(XA)
        BC_range = np.array([0.382 - err_allowed, 0.886 + err_allowed]) * abs(AB)
        CD_range = np.array([1.272 - err_allowed, 1.618 + err_allowed]) * abs(BC)

        PRZ = round(current_pat[1] + 0.786 * abs(XA), 4)
        SL = round(current_pat[0], 4)
        TP1 = round(current_pat[3] + 0.618 * abs(CD), 4)
        TP2 = round(current_pat[3] + 0.5 * abs(CD), 4)
        TP3 = round(current_pat[3] + 0.382 * abs(CD), 4)

        gartley_pat = (
            AB_range[0] < abs(AB) < AB_range[1] and
            BC_range[0] < abs(BC) < BC_range[1] and
            abs(CD) >= 0.6 * abs(XA) and
            abs(CD) <= CD_range[1]
        )

        if W_pat and gartley_pat:
            return list_to_string(symbol).replace("/USDT", ""), PRZ, SL, TP1, TP2, TP3
        return []

    except Exception:
        return []


def bull_crab(moves: list, symbol: list, current_pat: np.ndarray):
    """
    看漲螃蟹形態識別

    斐波那契比例：
    - AB: 0.382-0.618 × XA
    - BC: 0.382-0.886 × AB
    - CD: 2.618-3.618 × BC（最激進的形態）
    """
    try:
        err_allowed = 0.1
        XA, AB, BC, CD = moves

        M_pat = (XA > 0 and AB < 0 and BC > 0 and CD < 0)

        AB_range = np.array([0.382 - err_allowed, 0.618 + err_allowed]) * abs(XA)
        BC_range = np.array([0.382 - err_allowed, 0.886 + err_allowed]) * abs(AB)
        CD_range = np.array([2.618 - err_allowed, 3.618 + err_allowed]) * abs(BC)

        PRZ = round(current_pat[1] - 1.618 * abs(XA), 4)
        SL = PRZ * 0.98
        TP1 = round(current_pat[3] - 0.618 * abs(CD), 4)
        TP2 = round(current_pat[3] - 0.5 * abs(CD), 4)
        TP3 = round(current_pat[3] - 0.382 * abs(CD), 4)

        crab_pat = (
            AB_range[0] < abs(AB) < AB_range[1] and
            BC_range[0] < abs(BC) < BC_range[1] and
            abs(CD) >= 1.3 * abs(XA) and
            abs(CD) <= CD_range[1]
        )

        if M_pat and crab_pat:
            return list_to_string(symbol).replace("/USDT", ""), PRZ, SL, TP1, TP2, TP3
        return []

    except Exception:
        return []


def bear_crab(moves: list, symbol: list, current_pat: np.ndarray):
    """看跌螃蟹形態識別"""
    try:
        err_allowed = 0.1
        XA, AB, BC, CD = moves

        W_pat = (XA < 0 and AB > 0 and BC < 0 and CD > 0)

        AB_range = np.array([0.382 - err_allowed, 0.618 + err_allowed]) * abs(XA)
        BC_range = np.array([0.382 - err_allowed, 0.886 + err_allowed]) * abs(AB)
        CD_range = np.array([2.618 - err_allowed, 3.618 + err_allowed]) * abs(BC)

        PRZ = round(current_pat[1] + 1.618 * abs(XA), 4)
        SL = PRZ * 1.02
        TP1 = round(current_pat[3] + 0.618 * abs(CD), 4)
        TP2 = round(current_pat[3] + 0.5 * abs(CD), 4)
        TP3 = round(current_pat[3] + 0.382 * abs(CD), 4)

        crab_pat = (
            AB_range[0] < abs(AB) < AB_range[1] and
            BC_range[0] < abs(BC) < BC_range[1] and
            abs(CD) >= 1.3 * abs(XA) and
            abs(CD) <= CD_range[1]
        )

        if W_pat and crab_pat:
            return list_to_string(symbol).replace("/USDT", ""), PRZ, SL, TP1, TP2, TP3
        return []

    except Exception:
        return []


def bull_butterfly(moves: list, symbol: list, current_pat: np.ndarray):
    """
    看漲蝴蝶形態識別

    斐波那契比例：
    - AB: 0.786 × XA
    - BC: 0.382-0.886 × AB
    - CD: 1.618-2.618 × BC
    """
    try:
        err_allowed = 0.1
        XA, AB, BC, CD = moves

        M_pat = (XA > 0 and AB < 0 and BC > 0 and CD < 0)

        AB_range = np.array([0.786 - err_allowed, 0.786 + err_allowed]) * abs(XA)
        BC_range = np.array([0.382 - err_allowed, 0.886 + err_allowed]) * abs(AB)
        CD_range = np.array([1.618 - err_allowed, 2.618 + err_allowed]) * abs(BC)

        PRZ = round(current_pat[1] - 1.27 * abs(XA), 4)
        SL = PRZ * 0.98
        TP1 = round(current_pat[3] - 0.618 * abs(CD), 4)
        TP2 = round(current_pat[3] - 0.5 * abs(CD), 4)
        TP3 = round(current_pat[3] - 0.382 * abs(CD), 4)

        butterfly_pat = (
            AB_range[0] < abs(AB) < AB_range[1] and
            BC_range[0] < abs(BC) < BC_range[1] and
            abs(CD) >= 1.2 * abs(XA) and
            abs(CD) <= CD_range[1]
        )

        if M_pat and butterfly_pat:
            return list_to_string(symbol).replace("/USDT", ""), PRZ, SL, TP1, TP2, TP3
        return []

    except Exception:
        return []


def bear_butterfly(moves: list, symbol: list, current_pat: np.ndarray):
    """看跌蝴蝶形態識別"""
    try:
        err_allowed = 0.1
        XA, AB, BC, CD = moves

        W_pat = (XA < 0 and AB > 0 and BC < 0 and CD > 0)

        AB_range = np.array([0.786 - err_allowed, 0.786 + err_allowed]) * abs(XA)
        BC_range = np.array([0.382 - err_allowed, 0.886 + err_allowed]) * abs(AB)
        CD_range = np.array([1.618 - err_allowed, 2.618 + err_allowed]) * abs(BC)

        PRZ = round(current_pat[1] + 1.27 * abs(XA), 4)
        SL = PRZ * 0.98
        TP1 = round(current_pat[3] + 0.618 * abs(CD), 4)
        TP2 = round(current_pat[3] + 0.5 * abs(CD), 4)
        TP3 = round(current_pat[3] + 0.382 * abs(CD), 4)

        butterfly_pat = (
            AB_range[0] < abs(AB) < AB_range[1] and
            BC_range[0] < abs(BC) < BC_range[1] and
            abs(CD) >= 1.2 * abs(XA) and
            abs(CD) <= CD_range[1]
        )

        if W_pat and butterfly_pat:
            return list_to_string(symbol).replace("/USDT", ""), PRZ, SL, TP1, TP2, TP3
        return []

    except Exception:
        return []

# ============================================================================
# 谐波形態掃描主函數
# ============================================================================

def scan_harmonic_patterns(data: pd.DataFrame, order: int = 10,
                           send_notifications: bool = True) -> dict:
    """
    掃描所有谐波形態

    參數：
        data: OHLCV 數據
        order: 峰值檢測靈敏度
        send_notifications: 是否發送 Discord 通知

    返回：
        包含所有檢測到形態的字典
    """
    logger.info("開始谐波形態掃描...")

    coins = data['Symbol'].unique().tolist()
    timeframe = CONFIG["harmonic_timeframe"]

    # 形態檢測函數映射
    pattern_functions = {
        "看漲蝙蝠": bull_bat,
        "看跌蝙蝠": bear_bat,
        "看漲加特里": bull_gartley,
        "看跌加特里": bear_gartley,
        "看漲螃蟹": bull_crab,
        "看跌螃蟹": bear_crab,
        "看漲蝴蝶": bull_butterfly,
        "看跌蝴蝶": bear_butterfly,
    }

    results = {name: [] for name in pattern_functions.keys()}
    signal_count = 0
    total_coins = len(coins)
    progress_interval = max(1, total_coins // 10)

    for idx, coin in enumerate(coins):
        try:
            data_coin = data[data['Symbol'] == coin]
            _, current_pat, _, _, moves, _, _, _, symbol = peak_detect(
                data_coin, order=order
            )

            for pattern_name, pattern_func in pattern_functions.items():
                result = pattern_func(moves, symbol, current_pat)

                if result:
                    symbol_name, prz, sl, tp1, tp2, tp3 = result
                    results[pattern_name].append({
                        "symbol": symbol_name,
                        "prz": prz,
                        "sl": sl,
                        "tp1": tp1,
                        "tp2": tp2,
                        "tp3": tp3,
                    })
                    signal_count += 1

                    logger.info(f"發現信號: {symbol_name} | {pattern_name}")

                    if send_notifications:
                        send_harmonic_signal(
                            pattern_name, symbol_name, prz, sl, tp1, tp2, tp3, timeframe
                        )
                        time.sleep(0.5)  # 避免 Discord 速率限制

        except Exception as e:
            if CONFIG["verbose"]:
                logger.debug(f"掃描 {coin} 時發生錯誤: {str(e)}")

        # 顯示掃描進度
        if (idx + 1) % progress_interval == 0 or (idx + 1) == total_coins:
            progress = (idx + 1) / total_coins * 100
            logger.info(f"形態掃描進度: {idx + 1}/{total_coins} ({progress:.0f}%)")

    logger.info(f"谐波形態掃描完成 | 發現 {signal_count} 個信號")

    return results

# ============================================================================
# 主掃描函數
# ============================================================================

def run_scan(send_notifications: bool = True):
    """
    執行諧波形態掃描

    參數：
        send_notifications: 是否發送 Discord 通知
    """
    logger.info("=" * 60)
    logger.info("開始諧波形態掃描")
    logger.info("=" * 60)

    start_time = time.time()

    # 收集數據
    data = collect_data(
        timeframe=CONFIG["harmonic_timeframe"],
        limit=CONFIG["limit"]
    )

    # 執行谐波形態掃描
    harmonic_results = {}
    harmonic_count = 0
    if not data.empty:
        harmonic_results = scan_harmonic_patterns(
            data,
            order=CONFIG["peak_order"],
            send_notifications=send_notifications
        )
        harmonic_count = sum(len(v) for v in harmonic_results.values())

    elapsed_time = time.time() - start_time

    # 發送掃描摘要
    if send_notifications:
        send_scan_summary(harmonic_count, CONFIG["harmonic_timeframe"])

    logger.info("=" * 60)
    logger.info(f"掃描完成 | 耗時: {elapsed_time:.2f} 秒")
    logger.info(f"諧波形態: {harmonic_count} 個信號")
    logger.info("=" * 60)

    return {
        "harmonic": harmonic_results,
        "elapsed_time": elapsed_time,
    }

# ============================================================================
# 定時執行模組
# ============================================================================

def start_scheduler():
    """
    啟動定時執行排程器
    """
    interval = CONFIG["schedule_interval_minutes"]

    logger.info(f"啟動定時排程器 | 執行間隔: 每 {interval} 分鐘")

    # 立即執行一次
    run_scan()

    # 設定定時任務
    schedule.every(interval).minutes.do(run_scan)

    logger.info("定時任務已設定，按 Ctrl+C 停止")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("收到中斷信號，停止排程器")

# ============================================================================
# 命令列介面
# ============================================================================

def print_usage():
    """顯示使用說明"""
    usage = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    諧波形態掃描器 - 使用說明                                   ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  使用方式：                                                                   ║
║  ─────────────────────────────────────────────────────────────────────────   ║
║                                                                              ║
║  1. 手動執行（單次掃描）：                                                     ║
║     python harmonic_scanner.py                                               ║
║     python harmonic_scanner.py scan                                          ║
║                                                                              ║
║  2. 定時自動執行：                                                            ║
║     python harmonic_scanner.py auto                                          ║
║                                                                              ║
║  3. 測試 Discord 通知：                                                       ║
║     python harmonic_scanner.py test                                          ║
║                                                                              ║
║  ─────────────────────────────────────────────────────────────────────────   ║
║                                                                              ║
║  設定說明：                                                                   ║
║  ─────────────────────────────────────────────────────────────────────────   ║
║                                                                              ║
║  1. Discord Webhook 設定：                                                    ║
║     - 在 Discord 頻道設定中創建 Webhook                                        ║
║     - 複製 Webhook URL                                                        ║
║     - 將 URL 貼到程式碼中的 DISCORD_WEBHOOK_URL 變數                           ║
║                                                                              ║
║  2. 掃描參數設定（CONFIG 字典）：                                              ║
║     - harmonic_timeframe: 谐波形態時間框架（1h, 4h, 1d）                        ║
║     - limit: K線數據數量                                                      ║
║     - peak_order: 峰值檢測靈敏度                                              ║
║     - schedule_interval_minutes: 定時執行間隔（分鐘）                          ║
║                                                                              ║
║  ─────────────────────────────────────────────────────────────────────────   ║
║                                                                              ║
║  【谐波形態說明】基於斐波那契比例的價格形態                                       ║
║    - 蝙蝠形態（Bat）: AB = 0.382-0.5 XA                                       ║
║    - 加特里形態（Gartley）: AB = 0.618 XA                                      ║
║    - 螃蟹形態（Crab）: CD = 2.618-3.618 BC（最激進）                           ║
║    - 蝴蝶形態（Butterfly）: AB = 0.786 XA                                      ║
║                                                                              ║
║  ─────────────────────────────────────────────────────────────────────────   ║
║                                                                              ║
║  相依套件安裝：                                                               ║
║     pip install ccxt pandas numpy scipy requests schedule                    ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    print(usage)


def test_discord():
    """測試 Discord 通知功能"""
    logger.info("測試 Discord 通知...")

    embed = {
        "author": {
            "name": "Louis 掃描器 | 系統測試",
            "url": AUTHOR_INFO["instagram"],
            "icon_url": AUTHOR_INFO["icon_url"]
        },
        "title": "Discord Webhook 連接成功",
        "description": (
            f"```\n"
            f"{'═' * 35}\n"
            f"   測試訊息\n"
            f"{'═' * 35}\n"
            f"```\n"
            f"如果你看到這則訊息，表示 Webhook 設定正確！\n\n"
            f"**Instagram**: [@mr.__.l]({AUTHOR_INFO['instagram']})"
        ),
        "color": 0x00FF00,
        "fields": [
            {"name": "狀態", "value": "```diff\n+ 連接成功```", "inline": True},
            {"name": "時間", "value": f"```{datetime.now().strftime('%H:%M:%S')}```", "inline": True},
            {"name": "日期", "value": f"```{datetime.now().strftime('%Y-%m-%d')}```", "inline": True},
        ],
        "footer": {
            "text": "Louis_LAB • IG: @mr.__.l • 諧波形態掃描器",
            "icon_url": AUTHOR_INFO["icon_url"]
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    success = send_discord_embed(embed)

    if success:
        logger.info("Discord 測試通知發送成功！")
    else:
        logger.error("Discord 測試通知發送失敗，請檢查 Webhook URL")


def main():
    """主程式入口"""
    import sys

    # 檢查是否為雲端部署模式（透過環境變數）
    cloud_mode = os.environ.get("CLOUD_MODE", "").lower() == "true"

    if cloud_mode:
        logger.info("偵測到雲端部署模式，啟動自動排程...")
        start_scheduler()
        return

    if len(sys.argv) < 2:
        # 預設執行掃描
        run_scan()
        return

    command = sys.argv[1].lower()

    if command in ['help', '-h', '--help', '?']:
        print_usage()

    elif command == 'scan':
        run_scan()

    elif command == 'auto':
        start_scheduler()

    elif command == 'test':
        test_discord()

    else:
        logger.error(f"未知命令: {command}")
        print_usage()


if __name__ == "__main__":
    main()
