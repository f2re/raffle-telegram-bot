# Changelog - Mini App Integration

## Version 2.0.0 - Mini App Release

### 🎮 New Features

#### Frontend (Vue 3 Mini App)
- **Vue 3 + TypeScript** - Modern reactive framework with full type safety
- **TON Connect Integration** - Seamless wallet connection for payments
- **Real-time Updates** - Raffle status updates every 10 seconds
- **Beautiful UI** - Gradient design with smooth animations
- **Responsive Design** - Works perfectly on all mobile devices
- **Telegram WebApp API** - Native integration with Telegram features

#### Backend (FastAPI)
- **REST API** - Fast async API for Mini App
- **Telegram Auth** - Secure WebApp data verification
- **Shared Database** - Integrated with existing bot database
- **Health Checks** - API monitoring endpoints

#### Bot Integration
- **Mini App Button** - One-click access from bot menu
- **Seamless UX** - Switch between bot and Mini App

### 📁 New Files

#### Frontend
```
frontend/
├── src/
│   ├── App.vue                    # Main Mini App component
│   ├── main.ts                    # Entry point
│   ├── style.css                  # Global styles
│   ├── composables/
│   │   ├── useTonConnect.ts       # TON Connect integration
│   │   └── useTelegram.ts         # Telegram WebApp API
│   └── api/
│       ├── types.ts               # TypeScript types
│       └── raffle.ts              # API client
├── public/
│   └── tonconnect-manifest.json   # TON Connect manifest
├── index.html                     # HTML entry
├── vite.config.ts                 # Vite configuration
├── tsconfig.json                  # TypeScript config
├── package.json                   # Dependencies
└── dev.sh                         # Development script
```

#### Backend
```
backend/
├── app/
│   ├── main.py                    # FastAPI application
│   ├── config.py                  # Settings
│   ├── database.py                # Database session
│   └── api/
│       ├── raffle.py              # Raffle endpoints
│       ├── schemas.py             # Pydantic models
│       └── dependencies.py        # Auth & dependencies
├── Dockerfile                     # Multi-stage build
├── docker-entrypoint.sh           # Container startup
└── requirements.txt               # Python dependencies
```

#### Configuration
```
nginx.conf                         # Nginx configuration
deploy.sh                          # Deployment script
MINI_APP_SETUP.md                 # Deployment guide
QUICK_START.md                     # Quick start guide
.dockerignore                      # Docker ignore patterns
```

### 🔧 Modified Files

- `docker-compose.yml` - Added multi-stage build support
- `.env.example` - Added Mini App configuration variables
- `app/keyboards/inline.py` - Added Mini App button
- `app/config.py` - May need MINI_APP_URL setting

### 🚀 Deployment Changes

#### New Environment Variables
```bash
# Mini App
MINI_APP_URL=https://yourdomain.com
BOT_NAME=raffle-bot
BACKEND_PORT=8000

# Frontend Build
VITE_API_URL=https://yourdomain.com/api
VITE_WS_URL=wss://yourdomain.com/ws
VITE_BOT_USERNAME=your_bot
VITE_TON_WALLET_ADDRESS=UQxxx...
VITE_TON_CONNECT_MANIFEST_URL=https://yourdomain.com/tonconnect-manifest.json

# Docker
CACHEBUST=1
DOCKER_LOG_MAX_SIZE=10m
DOCKER_LOG_MAX_FILE=3
```

#### Docker Build Process
1. **Stage 1**: Build Vue 3 frontend with Vite
2. **Stage 2**: Copy frontend + setup Python backend + bot
3. **Result**: Single container running both bot and API

#### Nginx Setup Required
- Serves static frontend files from `./static/`
- Proxies `/api/` to FastAPI backend
- Handles TON Connect manifest with CORS

### 📊 API Endpoints

- `GET /api/health` - Health check
- `GET /api/raffle/current` - Get current active raffle
- `GET /api/raffle/{id}/participants` - List participants
- `POST /api/raffle/join` - Join raffle with TON payment

### 🔐 Security

- Telegram WebApp data verification using HMAC-SHA256
- Authorization header format: `tma <init_data>`
- Secure wallet connection via TON Connect
- CORS configured for TON Connect manifest

### 🎯 User Flow

1. User opens bot and sends `/start`
2. Clicks "🎮 Открыть Mini App"
3. Mini App loads with raffle information
4. User connects TON wallet via TON Connect
5. User pays entry fee directly from Mini App
6. Backend verifies transaction and adds participant
7. Real-time updates show new participants
8. Winner announced when minimum participants reached

### 📱 Browser Support

- ✅ Telegram iOS app
- ✅ Telegram Android app
- ✅ Telegram Desktop (with browser)
- ✅ Telegram Web

### 🛠️ Development

#### Local Frontend Development
```bash
cd frontend
./dev.sh
# or
npm install
npm run dev
```

#### Full Stack Development
```bash
# Terminal 1: Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Bot
python app/main.py
```

### 📦 Dependencies

#### Frontend
- vue@^3.4.21
- @tonconnect/ui@^2.0.5
- @ton/ton@^13.11.2
- @ton/core@^0.56.3
- @telegram-apps/sdk@^1.1.3
- vite@^5.2.6
- typescript@^5.4.3

#### Backend (New)
- fastapi@0.110.0
- uvicorn[standard]@0.27.1
- pydantic@2.6.3
- sqlalchemy@2.0.27
- asyncpg@0.29.0

### 🔄 Migration Guide

For existing installations:

1. **Backup** your current `.env` and database
2. **Pull** latest changes
3. **Update** `.env` with new Mini App variables
4. **Configure** `tonconnect-manifest.json`
5. **Build** with `./deploy.sh`
6. **Setup** nginx configuration
7. **Test** Mini App in Telegram

### ⚠️ Breaking Changes

None! The Mini App is an addition. All existing bot functionality remains unchanged.

### 🐛 Known Issues

None currently reported.

### 📝 TODO

- [ ] Add WebSocket support for real-time raffle updates
- [ ] Add raffle history view in Mini App
- [ ] Add user profile page
- [ ] Add leaderboard
- [ ] Add animations for winner announcement
- [ ] Add PWA support
- [ ] Add analytics integration

### 🙏 Credits

- Vue.js team for the amazing framework
- TON Connect team for wallet integration
- Telegram team for Mini Apps platform
- FastAPI team for the backend framework

---

**Version**: 2.0.0
**Release Date**: 2024
**Status**: ✅ Production Ready
