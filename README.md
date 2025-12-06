# HFT Signal Generator

A professional-grade high-frequency trading signal generator for XAUUSD (Gold) and cryptocurrencies. Features real-time order flow analytics, advanced signal generation using quantitative formulas, and AI-powered market analysis.

![Dashboard](https://img.shields.io/badge/Platform-Mobile%20%26%20Web-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

### Data Sources
- **Binance** - Real-time cryptocurrency data (BTC, ETH, SOL, etc.)
- **Rithmic** - XAUUSD gold futures (requires Rithmic credentials)
- **Simulated** - Demo data for testing without external connections

### Order Flow Analytics Engine
- **Delta Analysis** - Raw, normalized, and depth-aware delta calculations
- **Absorption Detection** - Identifies support/resistance walls
- **Iceberg Detection** - Finds hidden liquidity using fill-to-display ratios
- **OFMBI** - Order Flow Momentum Burst Index
- **Structure Analysis** - BOS/CHOCH detection, regime identification

### Signal Generation (HFSS)
Composite High-Frequency Signal Score combining:
- Order flow delta
- Absorption strength
- Iceberg probability
- Momentum burst index
- Market structure alignment
- Spread penalty

### AI Integration (OpenRouter)
- Access 100+ AI models through OpenRouter
- Real-time market analysis
- Anomaly detection
- Safety validation against quantitative metrics

## Tech Stack

- **Frontend**: React Native (Expo) - iOS, Android, Web
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Real-time**: WebSockets

---

## Prerequisites

### Check Your Node.js Version First!

```bash
node --version
```

**Important**: This determines which installation option to use.

| Your Node.js Version | Recommended Option |
|---------------------|--------------------|
| >= 20.19.0 or >= 22.x | **Option A** (Standard Install) |
| 20.17.x - 20.18.x | **Option B** (Compatible Install) or Upgrade Node.js |
| < 20.17.0 | Upgrade to Node.js 20.19+ or 22.x LTS |

### Other Requirements
- **Python** >= 3.9
- **MongoDB** >= 6.0 (local or cloud)
- **Yarn** (recommended) or npm

---

## Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd hft-signal-generator
```

### 2. Backend Setup (Same for Both Options)

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate
# Windows:
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
# Edit .env if needed (default MongoDB settings work locally)
```

### 3. Frontend Setup

---

## Option A: Standard Install (Node.js >= 20.19.0)

**Recommended if you can upgrade Node.js**

#### Upgrade Node.js (if needed)

```bash
# Using nvm (recommended)
nvm install 22
nvm use 22

# Or download from https://nodejs.org (22.x LTS recommended)
```

#### Install Frontend

```bash
cd frontend

# Use existing package.json (latest Expo SDK 54)
yarn install

# Create environment file
cp .env.example .env

# Edit .env - set backend URL:
# EXPO_PUBLIC_BACKEND_URL=http://localhost:8001
```

---

## Option B: Compatible Install (Node.js 20.17.x)

**Use this if you cannot upgrade Node.js**

```bash
cd frontend

# Use compatible package.json (Expo SDK 51)
copy package.compatible.json package.json   # Windows
# or
cp package.compatible.json package.json     # macOS/Linux

# Remove old lock file if exists
rm -f yarn.lock package-lock.json

# Install dependencies
yarn install

# Create environment file
cp .env.example .env

# Edit .env - set backend URL:
# EXPO_PUBLIC_BACKEND_URL=http://localhost:8001
```

---

### 4. Start MongoDB

```bash
# Using Docker (recommended)
docker run -d -p 27017:27017 --name mongodb mongo:latest

# Or start local MongoDB service
# macOS: brew services start mongodb-community
# Linux: sudo systemctl start mongod
# Windows: net start MongoDB
```

---

## Running the Application

### Terminal 1: Start Backend

```bash
cd backend
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

Backend runs at: `http://localhost:8001`

### Terminal 2: Start Frontend

```bash
cd frontend
yarn start
```

This shows options:
- Press `w` - Open in web browser
- Press `a` - Open in Android emulator
- Press `i` - Open in iOS simulator
- Scan QR with Expo Go app on phone

---

## Quick Start Guide

### 1. Test with Simulated Data (No API Keys Needed)

1. Open the app (web or mobile)
2. Go to **Settings** tab
3. Scroll down and click **Start Simulation**
4. Return to **Dashboard** to see real-time signals

### 2. Connect to Binance (Live Crypto)

1. Go to **Settings** tab
2. In **Binance (Crypto)** section:
   - Select cryptocurrency (BTCUSDT, ETHUSDT, etc.)
   - Click **Connect to Binance**
3. View live signals on Dashboard

*Note: Binance public data doesn't require API keys. However, Binance may be blocked in certain regions (US, etc.). When running locally from an unrestricted region, it should work. The cloud preview may show geographic restrictions.*

### 3. Connect to Rithmic (Gold/XAUUSD)

Rithmic provides professional futures market data. To use real Rithmic data:

1. **Get Rithmic Credentials**:
   - Contact your futures broker (many offer Rithmic connectivity)
   - Or apply directly at [rithmic.com/apis](https://www.rithmic.com/apis)
   - For production, you must pass Rithmic's conformance test

2. **Configure in App**:
   - Go to **Settings** tab → **Rithmic (XAUUSD)**
   - Enter your Username and Password
   - Select Server: "Rithmic Paper Trading" or "Rithmic Test"
   - Select Gateway: "Test/Paper Trading" for testing
   - Click **Save**, then **Connect**

3. **Gateway Options**:
   - **Test/Paper Trading**: rituz00100.rithmic.com:443 (for conformance testing)
   - **Chicago**: Requires conformance approval
   - **Custom URL**: Enter your broker-provided gateway URL

*Without valid credentials, Rithmic data is simulated for demonstration.*

### 4. Enable AI Analysis

1. Get API key from [OpenRouter](https://openrouter.ai)
2. Go to **Settings** → **OpenRouter AI**
3. Paste API key and select a model
4. Use **AI Insight** button on Signals page

---

## App Screens

### Dashboard
- Real-time price with trend indicator
- Trading signal (BUY/SELL/NO_TRADE)
- Probability distribution bars
- HFSS Score
- Order flow metrics (Delta, Absorption, Iceberg, OFMBI)
- Market structure info

### Signals
- Historical signal list
- Filter by type (All, Buy, Sell, Hold)
- AI Insight button
- Signal breakdown reasoning

### DOM (Depth of Market)
- Order book ladder
- Bid/Ask depth visualization
- Spread indicator
- Time & Sales tape

### Settings
- Connection status
- Data source configuration
- AI model selection

---

## API Reference

### Health & Status
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/data-source/status` | GET | Connection status |

### Settings
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/settings` | GET | Get all settings |
| `/api/settings/rithmic` | POST | Update Rithmic credentials |
| `/api/settings/binance` | POST | Update Binance settings |
| `/api/settings/openrouter` | POST | Update OpenRouter settings |

### Data Sources
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/data-source/connect` | POST | Connect to source |
| `/api/data-source/disconnect` | POST | Disconnect |
| `/api/binance/symbols` | GET | Available symbols |

### Signals & Analytics
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/signals/current` | GET | Current signal |
| `/api/signals/history` | GET | Signal history |
| `/api/metrics` | GET | Analytics metrics |

### AI
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/openrouter/models` | GET | Available AI models |
| `/api/ai/analyze` | POST | AI market analysis |

### WebSocket
- `WS /api/ws` - Real-time stream (trades, orderbook, signals)

---

## Signal Formulas

### Delta (Order Flow Imbalance)
```
Δ_raw(t) = V_buy(t) - V_sell(t)
Δ_norm(t) = (V_buy - V_sell) / (V_buy + V_sell + ε)
Δ_depth(t) = (V_buy - V_sell) / (D_bid + D_ask + ε)
```

### Absorption Strength
```
AbsorptionScore(p,t) = V_hit(p,t) / (V_hit(p,t) + L_vis(p,t) + ε)
```

### Iceberg Probability
```
IP(p,t) = σ(a₀ + a₁·FDR(p,t) + a₂·R_refill(p,t) + a₃·T_persist(p,t))
```

### HFSS (High Frequency Signal Score)
```
HFSS(t) = w₁Δ̃(t) + w₂AS̃(t) + w₃IP̃(t) + w₄OFMBĨ(t) + w₅Structurẽ(t) - w₆SpreadPeñ(t)
```

---

## Troubleshooting

### "The engine node is incompatible" Error

```
error metro@0.83.2: The engine "node" is incompatible. Expected ">=20.19.4". Got "20.17.0"
```

**Solutions**:
1. **Upgrade Node.js** to 20.19+ or 22.x LTS (recommended)
2. **Use compatible packages**: Copy `package.compatible.json` to `package.json`

### Backend Won't Start

- Ensure MongoDB is running: `mongosh` to test
- Check Python version: `python --version` (needs 3.9+)
- Reinstall dependencies: `pip install -r requirements.txt`

### Frontend Connection Issues

- Verify backend is running on port 8001
- Check `EXPO_PUBLIC_BACKEND_URL` in `.env`
- For mobile: use computer's LAN IP, not localhost

### No Signals Generated

- Check Settings → Connection Status
- Try Simulated data source first
- Check backend logs for errors

### Binance Connection Fails

- Some regions block Binance API (use VPN)
- Use simulated data as fallback

---

## Project Structure

```
├── backend/
│   ├── server.py           # FastAPI main server
│   ├── models.py           # Pydantic data models
│   ├── analytics_engine.py # Order flow analytics
│   ├── data_feeds.py       # Data source integrations
│   ├── openrouter_client.py# AI integration
│   ├── requirements.txt    # Python dependencies
│   └── .env.example        # Environment template
├── frontend/
│   ├── app/
│   │   ├── (tabs)/         # Tab screens
│   │   │   ├── index.tsx   # Dashboard
│   │   │   ├── signals.tsx # Signal history
│   │   │   ├── orderbook.tsx # DOM view
│   │   │   └── settings.tsx# Configuration
│   │   └── _layout.tsx     # Navigation
│   ├── package.json        # Latest dependencies
│   ├── package.compatible.json # Node 20.17 compatible
│   └── .env.example        # Environment template
└── README.md
```

---

## License

MIT License

## Support

For issues and feature requests, please open a GitHub issue.
