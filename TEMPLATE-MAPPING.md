# 證書模板 ↔ 資料庫欄位 對應表（review 用）

## 模板總覽（14 個 .docx）

| # | 檔名 | 對應 category | MERGEFIELD 數 | 註 |
|---:|---|---|---:|---|
| 1 | A2電腦伴唱機證書-正面.docx | `COMPUTER_KARAOKE` | 12 | 主模板 |
| 2 | A2電腦伴唱機證書-背面.docx | `COMPUTER_KARAOKE` | 0 | 純合約文字、無變數 |
| 3 | A2電腦伴唱機證書-正面(單張).docx | `COMPUTER_KARAOKE` | 0 | ⚠️ 似乎還沒設 MERGEFIELD |
| 4 | B1自助式KTV證書-正面.docx | `SELF_SERVICE_KTV` | 10 |  |
| 5 | B2自助式KTV證書-背面.docx | `SELF_SERVICE_KTV` | 0 | 純合約文字 |
| 6 | D2單場次表演證書-正面.docx | `SINGLE_EVENT` | 15 |  |
| 7 | D2單場次表演證書-後面.docx | `SINGLE_EVENT` | 0 | 純合約文字 |
| 8 | E1街頭藝人授權證書-正面.docx | `STREET_ARTIST` | 9 |  |
| 9 | E2街頭藝人授權證書-背面.docx | `STREET_ARTIST` | 0 | 純合約文字 |
| 10 | F4競選活動證書-正面.docx | `ELECTION` | 12 |  |
| 11 | F4競選活動證書-背面.docx | `ELECTION` | 0 | 純合約文字 |
| 12 | H1交通運輸工具證書-正面.docx | `TRANSPORT` | 10 |  |
| 13 | H1交通運輸工具證書-背面.docx | `TRANSPORT` | 0 | 純合約文字 |
| 14 | 公開傳輸證書-正面.docx | `PUBLIC_TRANSMIT` | 12 |  |
| 15 | 公開傳輸證書-背面.docx | `PUBLIC_TRANSMIT` | 0 | 純合約文字 |
| 16 | 音樂著作公開播送授權證書 -大廳、客房、宴會廳-正面.docx | `HALL_ROOM` | 10 |  |
| 17 | 音樂著作公開播送授權證書 -大廳、客房、宴會廳-背面.docx | `HALL_ROOM` | 0 | 純合約文字 |
| 18 | 音樂著作公開播送授權證書-坪數及顯示器.docx | `AREA_DISPLAY` | 10 | 只有單面 |

> 還缺三個 category 的模板：`COMMUNITY_BOARD` / `PUBLIC_KARAOKE` / `FUNERAL`

> 「正面+背面」概念：實務上每張證書 = 正面卡 + 背面卡（合約文字）疊在一起列印。背面沒變數，永遠是同樣文字。系統實作會把正面 + 背面合併成一份 .docx 給你。

---

## 變數 → DB 欄位 對應

### 共通變數

| MERGEFIELD | DB 欄位 | 說明 |
|---|---|---|
| `證書編號` / `證號` | `cert_no` | 兩個都是證書編號 |
| `持證者` / `持證人` | `holder_name` |  |
| `起年` | `period_start` 的民國年 | (date.year - 1911) |
| `起月` | `period_start` 的月 | 零填補兩位（01-12）|
| `起日` | `period_start` 的日 | 零填補兩位 |
| `終年` / `迄年` | `period_end` 的民國年 |  |
| `終月` / `迄月` | `period_end` 的月 |  |
| `終日` / `迄日` | `period_end` 的日 |  |

### 各模板專屬變數

#### 1. A2電腦伴唱機 (`COMPUTER_KARAOKE`)
| MERGEFIELD | DB 欄位 |
|---|---|
| `營業地址` | `use_address` |
| `廠牌名稱` | `brand` |
| `台數` | `qty` |
| `機號` | `serial_no` |

#### 2. B1自助式KTV (`SELF_SERVICE_KTV`)
| MERGEFIELD | DB 欄位 |
|---|---|
| `營業地址` | `use_address` |
| `台數` | `qty`（含義：包廂數）|

#### 3. D2單場次表演 (`SINGLE_EVENT`) — 變數最多
| MERGEFIELD | DB 欄位 | 說明 |
|---|---|---|
| `演出曲目` | `extra.songs` |  |
| `首` | `extra.song_count` | 總曲數 |
| `節目名稱` | `extra.event_name` |  |
| `活動地點` | `extra.venue` |  |
| `地點地址` | `extra.venue_address` |  |
| `每場活動場` | ❓ | ⚠️ 不確定，請確認 |
| `特定曲目場` | ❓ | ⚠️ 不確定，請確認 |

❓ `每場活動場` 和 `特定曲目場` 在 Excel 來源資料找不到對應欄位。請問：
- 這兩個是表演形式的場次計算嗎？（例：總場次 vs 演自己曲目場次）
- 對應到 records 表的哪個欄位？還是要新增到 `extra`？或目前在 Excel 也都空著？

#### 4. E1街頭藝人 (`STREET_ARTIST`)
| MERGEFIELD | DB 欄位 |
|---|---|
| `藝人證號` | `extra.street_cert_no` |

#### 5. F4競選活動 (`ELECTION`)
| MERGEFIELD | DB 欄位 |
|---|---|
| `演出曲目` | `extra.songs` |
| `首` | `extra.song_count` |
| `活動地點` | `extra.venue` |
| `地點地址` | `extra.venue_address` |

#### 6. H1交通運輸工具 (`TRANSPORT`)
| MERGEFIELD | DB 欄位 |
|---|---|
| `營業地址` | `use_address` |
| `車牌號碼` | `serial_no`（交通工具用這欄存車號）|

#### 7. 公開傳輸 (`PUBLIC_TRANSMIT`)
| MERGEFIELD | DB 欄位 |
|---|---|
| `曲目` | `extra.songs` |
| `總曲數` | `extra.song_count` |
| `平台名稱` | `extra.platform_name` |
| `網址` | `extra.platform_url` |

#### 8. 大廳、客房、宴會廳 (`HALL_ROOM`)
| MERGEFIELD | DB 欄位 | 說明 |
|---|---|---|
| `使用地址` | `use_address` |  |
| `客房書` | `qty` | ⚠️ 應該是「客房數」，模板上是「客房書」可能是手誤 |

#### 9. 坪數及顯示器 (`AREA_DISPLAY`)
| MERGEFIELD | DB 欄位 |
|---|---|
| `使用地址` | `use_address` |
| `坪數` | `extra.floor_area` |

---

## 三個你要確認的事

### ❶ 「每場活動場」與「特定曲目場」是什麼意思？
這兩個只出現在 D2 單場次表演正面模板。Excel 來源資料沒有對應欄位。請說明它們的意義。

### ❷ A2電腦伴唱機-正面(單張) 為什麼沒設 MERGEFIELD？
這份是新版／舊版／半成品？要納入系統嗎？

### ❸ `COMMUNITY_BOARD`（社區管委會）、`PUBLIC_KARAOKE`（公益伴唱機）、`FUNERAL`（告別式）三個 category 沒提供模板
- 是因為這三類**沒有獨立模板**（用其他 category 的模板？例如社區管委會也用 A2 電腦伴唱機證書）
- 還是**待補檔**

---

## 我接下來會做的事（確認後執行）

1. **寫轉換腳本**：把每個 .docx 內的 `MERGEFIELD <var>` 轉成 `{{ <英文 jinja key> }}`
   - 例：`MERGEFIELD 持證者` → `{{ holder_name }}`
   - 把轉好的 .docx 存到 `app/backend/templates_jinja/`
2. **建 templates 資料表 seed**：每個模板的 id、name、適用 category、檔案路徑
3. **後端**：`POST /api/records/{id}/generate?template_id=X` → 用 docxtpl 填值 → 回傳 .docx
4. **後端**：自動合併「正面 + 背面」（用 docxcompose 已在 requirements）
5. **前端**：證書管理頁／在 records 表加「核發」按鈕
6. **稽核**：每次產生在 `generated_files` 表留紀錄

---

請回覆 ❶❷❸，或不確定的話直接說「先用推測值跑跑看」，我把不確定的標 ⚠️ 之後再回頭調。
