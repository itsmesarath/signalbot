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

## Prerequisites

Before running locally, ensure you have:

- **Node.js** >= 18.x
- **Python** >= 3.9
- **MongoDB** >= 6.0 (running locally or cloud instance)
- **Yarn** (recommended) or npm
- **Expo CLI** (`npm install -g expo-cli`)

## Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd hft-signal-generator
```

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env with your settings (see Configuration section)
```

### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd ../frontend

# Install dependencies
yarn install
# or: npm install

# Create .env file
cp .env.example .env

# Edit .env with your backend URL
```

### 4. Start MongoDB

Make sure MongoDB is running:

```bash
# Using Docker (recommended)
docker run -d -p 27017:27017 --name mongodb mongo:latest

# Or start local MongoDB service
# macOS: brew services start mongodb-community
# Linux: sudo systemctl start mongod
# Windows: net start MongoDB
```

## Configuration

### Backend Environment Variables (`backend/.env`)

```env
# MongoDB connection string
MONGO_URL="mongodb://localhost:27017"

# Database name
DB_NAME="hft_signals"

# Optional: OpenRouter API Key (for AI features)
# OPENROUTER_API_KEY="your-openrouter-api-key"
```

### Frontend Environment Variables (`frontend/.env`)

```env
# Backend API URL (local development)
EXPO_PUBLIC_BACKEND_URL=http://localhost:8001

# For LAN testing (use your computer's IP)
# EXPO_PUBLIC_BACKEND_URL=http://192.168.1.100:8001
```

## Running the Application

### Start Backend

```bash
cd backend

# Activate virtual environment if not already active
source venv/bin/activate  # macOS/Linux
# or: .\venv\Scripts\activate  # Windows

# Run the server
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

Backend will be available at: `http://localhost:8001`

### Start Frontend

```bash
cd frontend

# Start Expo development server
yarn start
# or: npx expo start
```

This will show options to:
- Press `w` - Open in web browser
- Press `a` - Open in Android emulator/device
- Press `i` - Open in iOS simulator (macOS only)
- Scan QR code with Expo Go app on your phone

## Usage Guide

### 1. Quick Start with Simulated Data

1. Open the app (web or mobile)
2. Go to **Settings** tab
3. Scroll down and click **Start Simulation**
4. Return to **Dashboard** to see real-time signals

### 2. Connect to Binance (Live Crypto Data)

1. Go to **Settings** tab
2. In the **Binance (Crypto)** section:
   - Select your desired cryptocurrency (BTCUSDT, ETHUSDT, etc.)
   - Click **Connect to Binance**
3. View live signals on the Dashboard

*Note: Binance public data doesn't require API keys*

### 3. Connect to Rithmic (Gold/XAUUSD)

1. Go to **Settings** tab
2. In the **Rithmic (XAUUSD)** section:
   - Enter your Rithmic username
   - Enter your Rithmic password
   - Select server (Paper Trading or Live)
   - Select gateway (Chicago, etc.)
   - Click **Save**, then **Connect**

*Note: Requires Rithmic subscription/trial account*

### 4. Enable AI Analysis

1. Get an API key from [OpenRouter](https://openrouter.ai)
2. Go to **Settings** tab
3. In the **OpenRouter AI** section:
   - Paste your API key
   - Click on "Select AI Model" to load available models
   - Search and select your preferred model
   - Click **Save OpenRouter Settings**
4. On the **Signals** page, click **AI Insight** for analysis

## App Screens

### Dashboard
- Real-time price display with trend indicator
- Current trading signal (BUY/SELL/NO_TRADE)
- Probability distribution bars
- HFSS (High-Frequency Signal Score)
- Order flow metrics cards (Delta, Absorption, Iceberg, OFMBI)
- Market structure info (Regime, Trend, BOS/CHOCH)

### Signals
- Historical signal list
- Filter by type (All, Buy, Sell, Hold)
- AI Insight button for market analysis
- Signal details with breakdown reasoning

### DOM (Depth of Market)
- Order book ladder visualization
- Bid/Ask depth bars
- Spread indicator
- Time & Sales tape

### Settings
- Connection status
- Binance cryptocurrency selection
- Rithmic credentials
- OpenRouter AI configuration
- Simulated data toggle

## API Endpoints

### Health & Status
- `GET /api/health` - Health check
- `GET /api/data-source/status` - Connection status

### Settings
- `GET /api/settings` - Get all settings
- `POST /api/settings/rithmic` - Update Rithmic credentials
- `POST /api/settings/binance` - Update Binance settings
- `POST /api/settings/openrouter` - Update OpenRouter settings

### Data Sources
- `POST /api/data-source/connect?source=binance&symbol=BTCUSDT` - Connect
- `POST /api/data-source/disconnect` - Disconnect
- `GET /api/binance/symbols` - Get available symbols

### Signals & Analytics
- `GET /api/signals/current` - Current signal
- `GET /api/signals/history?limit=100` - Signal history
- `GET /api/metrics` - Current analytics metrics

### AI
- `GET /api/openrouter/models` - Get available AI models
- `POST /api/openrouter/set-model?model_id=...` - Set active model
- `POST /api/ai/analyze` - Get AI market analysis
- `GET /api/ai/summary` - Get quick summary

### WebSocket
- `WS /api/ws` - Real-time data stream (trades, orderbook, signals)

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

### OFMBI (Order Flow Momentum Burst Index)
```
OFMBI(t) = Δ_norm(t) · TS(t) / (S(t) + ε)
```

### HFSS (High Frequency Signal Score)
```
HFSS(t) = w₁Δ̃(t) + w₂AS̃(t) + w₃IP̃(t) + w₄OFMBĨ(t) + w₅Structurẽ(t) - w₆SpreadPeñ(t)
```

## Troubleshooting

### Backend won't start
- Ensure MongoDB is running: `mongosh` to test connection
- Check Python version: `python --version` (needs 3.9+)
- Verify all dependencies: `pip install -r requirements.txt`

### Frontend connection issues
- Verify backend is running on port 8001
- Check EXPO_PUBLIC_BACKEND_URL in frontend/.env
- For mobile testing, use your computer's LAN IP, not localhost

### No signals being generated
- Ensure a data source is connected (check Settings > Connection Status)
- Try the Simulated data source first
- Check backend logs for errors

### Binance connection fails
- Some regions block Binance API (use VPN if needed)
- Try simulated data as fallback

## Development

### Project Structure
```
├── backend/
│   ├── server.py           # FastAPI main server
│   ├── models.py           # Pydantic data models
│   ├── analytics_engine.py # Order flow analytics
│   ├── data_feeds.py       # Binance/Rithmic/Simulated feeds
│   ├── openrouter_client.py# AI integration
│   ├── requirements.txt    # Python dependencies
│   └── .env               # Environment variables
├── frontend/
│   ├── app/
│   │   ├── (tabs)/        # Tab screens
│   │   │   ├── index.tsx  # Dashboard
│   │   │   ├── signals.tsx# Signal history
│   │   │   ├── orderbook.tsx # DOM view
│   │   │   └── settings.tsx# Configuration
│   │   └── _layout.tsx    # Navigation layout
│   ├── package.json       # Node dependencies
│   └── .env              # Environment variables
└── README.md
```

### Adding New Data Sources

1. Create a new feed class in `backend/data_feeds.py`
2. Implement `connect()`, `disconnect()`, and callback handlers
3. Add to the `connect_data_source()` endpoint in `server.py`
4. Add UI controls in `frontend/app/(tabs)/settings.tsx`

## License

MIT License - See LICENSE file for details

## Support

For issues and feature requests, please open a GitHub issue.
