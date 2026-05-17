# TMCA 音樂版權授權系統

> 社團法人台灣音樂著作權集體管理協會 — 內部作業系統
> 對應 ADR-001 / ADR-002 / SYSTEM-DESIGN.md

## 技術堆疊

| 層級 | 技術 |
|---|---|
| 前端 | React 18 + Vite + TypeScript + TailwindCSS + Univer（試算表 UI） |
| 後端 | Python 3.11 + FastAPI + SQLAlchemy 2.0 + Alembic |
| 資料庫 | PostgreSQL 15 |
| 反向代理 | Caddy 2（自動 HTTPS） |
| 部署 | Docker Compose |

## 快速啟動（本機開發）

需先安裝：
- Docker Desktop（Mac/Windows）或 Docker Engine（Linux）

```bash
# 1. 複製環境變數範本
cp .env.example .env

# 2. 啟動全部服務
docker compose up --build

# 3. 第一次啟動後在另一個視窗跑遷移與種子
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed_users.py
```

開啟瀏覽器：
- **前端首頁**：http://localhost
- **後端 API**：http://localhost/api/health
- **API 文件（OpenAPI）**：http://localhost/api/docs
- **PostgreSQL**：localhost:5432（帳號 `tmca` / 密碼見 `.env`）

## Phase 進度

- [x] **Phase 0** — 專案骨架（本次交付）
- [ ] Phase 1 — 認證 + 4 角色
- [ ] Phase 2 — Excel 匯入（110-115年 總表.xlsx）
- [ ] Phase 3 — Univer 主總表介面（12 個 tab × 41 欄）
- [ ] Phase 4 — 續約偵測 + 狀態燈
- [ ] Phase 5 — 核發 Word 套印（27 個證書模板）
- [ ] Phase 6 — 承辦寄信檔（Word + 信封）
- [ ] Phase 7 — 搜尋 + 報表
- [ ] Phase 8 — 部署 SOP + Caddy HTTPS

## 目錄結構

```
app/
├── docker-compose.yml         # 4 個 service 編排
├── Caddyfile                  # 反向代理設定
├── .env.example               # 環境變數範本
├── backend/                   # FastAPI 後端
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/               # 資料庫遷移
│   ├── app/
│   │   ├── main.py            # FastAPI app entry
│   │   ├── config.py          # Settings
│   │   ├── database.py        # SQLAlchemy session
│   │   ├── models/            # ORM models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── api/               # REST endpoints
│   │   ├── core/              # security, permissions
│   │   └── utils/             # roc_date 等小工具
│   └── scripts/               # 一次性腳本（seed, import）
└── frontend/                  # React + Vite 前端
    ├── Dockerfile
    ├── package.json
    ├── nginx.conf             # production serve
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── pages/
        ├── components/
        └── api/
```

## 常用指令

```bash
# 重啟特定服務
docker compose restart backend

# 跑遷移
docker compose exec backend alembic upgrade head

# 建立新遷移
docker compose exec backend alembic revision -m "describe change" --autogenerate

# 進 Postgres
docker compose exec db psql -U tmca -d tmca

# 看 log
docker compose logs -f backend

# 全砍重來（含資料）
docker compose down -v
```

## 帳號

預設帳號（跑完 `seed_users.py` 後）：

| 角色 | username | 密碼 | 用途 |
|---|---|---|---|
| 承辦 A（男）單場次 | `officer_a` | `Tmca0001!` | STAGE 1 — 單場次表演 |
| 承辦 B（女）其他 | `officer_b` | `Tmca0001!` | STAGE 1 — 其餘 11 類 |
| 會計 | `accountant` | `Tmca0001!` | STAGE 2 — 開立發票 |
| 核發 | `issuer` | `Tmca0001!` | STAGE 3 — 證書套印 |
| Admin | `admin` | `Tmca0001!` | 使用者 / 模板管理 |

> ⚠️ 上線前務必改密碼。
