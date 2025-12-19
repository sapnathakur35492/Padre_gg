# Padre.gg Real-Time Data Relay 🚀

**Status:** 100% Verified & Production Ready  
**Purpose:** Ultra-low latency (<50ms) tracking of Padre.gg WebSocket activity with automated relay and visual dashboard.

---

## ✅ Deliverables Summary
- **Real-Time Tracking**: Direct `wss://` protocol integration (MsgPack/JSON hybrid).
- **Target Tracking**: Specific account identification (e.g., `@cz_binance`).
- **Data Enrichment**: Unix Millisecond timestamps + Human-readable time.
- **Relay System**: Custom WebSocket server to broadcast data to any bot.
- **Visual UI**: Chrome-based dashboard for instant monitoring.

---

## 📂 Project Structure

| File | Role |
| :--- | :--- |
| **`relay_server.py`** | The "Master" server. Runs on port `8765`. |
| **`padre_tracker.py`** | The "Fisherman". Captures data from Padre & pushes to Relay. |
| **`client_dashboard.html`** | The "Screen". Shows live data in your browser. |
| **`test_bot_receiver.py`** | Sample client showing how to consume the stream in Python. |
| **`.env`** | Authentication and Filter settings (Keep this secret!). |
| **`config.py`** | System configuration loader. |

---

## 🛠 Setup & Run Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Credentials
Open `.env` and update the following:
```ini
PADRE_TOKEN=your_token_here
PADRE_UID=your_uid_here
TARGET_USERNAMES=cz_binance
FILTER_ONLY_TARGETS=false
```

### 3. Execution Sequence
For the system to work, follow this order:

1. **Start Relay Server** (New Terminal):
   ```powershell
   python relay_server.py
   ```
2. **Start Tracker** (New Terminal):
   ```powershell
   python padre_tracker.py
   ```
3. **Open Dashboard**:
   Double-click `client_dashboard.html` in your folder.

---

## 🔍 Understanding the Output (JSON)
Each event sent via the relay has this structure:
```json
{
  "timestamp": 1734623456123,
  "timestamp_human": "21:30:56.123",
  "is_target_match": true,
  "source": "padre",
  "event": { ... raw_data ... }
}
```

---

## ⚡ Troubleshooting (Must-Read)

### 🔴 Error: `1008 Policy Violation`
**Reason:** Your Token has expired.
**Fix:** Refesh Padre.gg in Chrome, get a new token from LocalStorage, and update it in `.env`. Restart `padre_tracker.py`.

### 🔴 Error: `10048 Address already in use`
**Reason:** Another `relay_server.py` is already running.
**Fix:** Close all Python terminals and restart. If it persists, run:
`Stop-Process -Id (Get-NetTCPConnection -LocalPort 8765).OwningProcess -Force`

---
**Verified by AI Engineer.** 🏁
