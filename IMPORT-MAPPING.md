# Excel 匯入欄位對應表（review 用）

> 來源：`110-115年 總表.xlsx` — 12 個 sheet
> 目的：把 Excel 每欄對應到 `records` 表的 SQLAlchemy 欄位，未對應到的塞 `extra` JSONB。
> 「資料起始列」：公開傳輸 = R2；其餘 11 個 sheet = R3

## 共同欄位（所有 sheet col 1–10 都一樣，名稱有微差異視為同義）

| Excel col | 標題（含異名） | DB 欄位 | 型態 | 備註 |
|---:|---|---|---|---|
| 1 | NO. / 序 | — | — | 跳過（流水號） |
| 2 | 發證日 / 發證日期 | `issued_date` | date | 民國年 |
| 3 | 註記 / 備註 | `note` | text |  |
| 4 | 證書編號 / 證號 | `cert_no` | string | 唯一鍵 |
| 5 | 發票日期 | `invoice_date` | date | 民國年 |
| 6 | 發票形式 / 形式 | `invoice_type` | string | 二聯式/三聯式 |
| 7 | 發票抬頭 | `invoice_title` | string |  |
| 8 | 統一編號 | `tax_id` | string |  |
| 9 | 發票號碼 | `invoice_no` | string | 有值→`issuance_status=綠` |
| 10 | 金額(含稅) | `amount` | int |  |

---

## 1. 電腦伴唱機（9629 筆，41 欄）`category_code=karaoke`

| col | 標題 | DB 欄位 | 備註 |
|---:|---|---|---|
| 11 | 提報 | `source` | 承辦/自辦 |
| 12 | 承辦人 | `officer` |  |
| 13 | 辦理項目 | `action_type` | 新申辦/續約/授權延長/補發 |
| 14 | 申請日期 | `apply_date` | date |
| 15 | 申請人 | `applicant_name` |  |
| 16 | 身分證字號 | `applicant_id` |  |
| 17 | 行動 | `applicant_mobile` |  |
| 18 | 電話 | `applicant_phone` |  |
| 19 | 傳真 | `applicant_fax` |  |
| 20 | 持證者 | `holder_name` | 續約比對關鍵 |
| 21 | 性質 | `holder_type` | 餐廳/咖啡廳/… |
| 22 | 郵遞區號 | `use_zip` |  |
| 23 | 使用地址 | `use_address` |  |
| 24 | 現場聯絡人 | `onsite_name` |  |
| 25 | 手機 | `onsite_mobile` |  |
| 26 | 電話 | `onsite_phone` |  |
| 27 | 分機 | `onsite_ext` |  |
| 28 | 傳真 | `onsite_fax` |  |
| 29 | 台數 | `qty` | int |
| 30 | 廠牌 | `brand` |  |
| 31 | 機號 | `serial_no` |  |
| 32-37 | 授權期間/起年起月起日迄年迄月迄日 | `period_start`、`period_end` | 6 欄合併 |
| 38 | 寄證地址/郵區 | `mail_zip` |  |
| 39 | 寄證地址/地址 | `mail_address` |  |
| 40 | 寄證地址/收件人 | `mail_recipient` |  |
| 41 | 寄證地址/收件人電話 | `mail_phone` |  |

## 2. 社區管委會（180 筆，41 欄）`category_code=community`
**欄位完全同電腦伴唱機**

## 3. 公益伴唱機（2550 筆，42 欄）`category_code=charity_karaoke`
**欄位同電腦伴唱機**，col 42 為多出的空白欄（跳過）

## 4. 自助KTV（499 筆，38 欄）`category_code=self_ktv`
和電腦伴唱機差異：少了「身分證/行動/性質/現場聯絡人」獨立欄位，多了「包廂數」

| col | 標題 | DB 欄位 | 備註 |
|---:|---|---|---|
| 11 | 提報 | `source` |  |
| 12 | 承辦人 | `officer` |  |
| 13 | 辦理項目 | `action_type` |  |
| 14 | 申請日期 | `apply_date` |  |
| 15 | 申請人 | `applicant_name` |  |
| 16 | 身分證號 | `applicant_id` |  |
| 17 | 手機 | `applicant_mobile` |  |
| 18 | 電話 | `applicant_phone` |  |
| 19 | 傳真 | `applicant_fax` |  |
| 20 | 持證者 | `holder_name` |  |
| 21 | 聯絡人 | `onsite_name` |  |
| 22 | 手機 | `onsite_mobile` |  |
| 23 | 電話 | `onsite_phone` |  |
| 24 | 分機 | `onsite_ext` |  |
| 25 | 傳真 | `onsite_fax` |  |
| 26 | 郵遞區號 | `use_zip` |  |
| 27 | 使用地址 | `use_address` |  |
| 28 | 包廂數 | `qty` | int（含義為包廂數）|
| 29-34 | 授權期間 | `period_start/end` |  |
| 35-38 | 寄證地址 | `mail_zip/address/recipient/phone` |  |

## 5. 街頭藝人（600 筆，34 欄）`category_code=street_performer`

| col | 標題 | DB 欄位 | 備註 |
|---:|---|---|---|
| 11 | 提報 | `source` |  |
| 12 | 承辦人 | `officer` |  |
| 13 | 辦理項目 | `action_type` |  |
| 14 | 申請日期 | `apply_date` |  |
| 15 | 申請人 | `applicant_name` |  |
| 16 | 手機 | `applicant_mobile` |  |
| 17 | 電話 | `applicant_phone` |  |
| 18 | 傳真 | `applicant_fax` |  |
| 19 | E-mail | `extra.email` |  |
| 20 | 持證者 | `holder_name` |  |
| 21 | 發證單位 | `extra.cert_issuer` |  |
| 22 | 街頭藝人證號 | `extra.street_cert_no` |  |
| 23 | 證號到期日 | `extra.street_cert_expiry` | 民國年 date |
| 24 | 表演場地 | `use_address` |  |
| 25-30 | 授權期間 | `period_start/end` |  |
| 31-34 | 寄證地址 | `mail_zip/address/recipient/phone` |  |

## 6. 交通運輸工具（80 筆，38 欄）`category_code=transport`

| col | 標題 | DB 欄位 | 備註 |
|---:|---|---|---|
| 11 | 提報 | `source` |  |
| 12 | 承辦人 | `officer` |  |
| 13 | 辦理項目 | `action_type` |  |
| 14 | 申請日期 | `apply_date` |  |
| 15 | 申請人 | `applicant_name` |  |
| 16 | 手機 | `applicant_mobile` |  |
| 17 | 電話 | `applicant_phone` |  |
| 18 | 傳真 | `applicant_fax` |  |
| 19 | 持證者 | `holder_name` |  |
| 20 | 郵區 | `use_zip` |  |
| 21 | 營業地址 | `use_address` |  |
| 22 | 聯絡人 | `onsite_name` |  |
| 23 | 手機 | `onsite_mobile` |  |
| 24 | 電話 | `onsite_phone` |  |
| 25 | 分機 | `onsite_ext` |  |
| 26 | 傳真 | `onsite_fax` |  |
| 27 | 車輛數 | `qty` |  |
| 28 | 車輛號碼 | `serial_no` |  |
| 29-34 | 授權期間 | `period_start/end` |  |
| 35-38 | 寄證地址 | `mail_zip/address/recipient/phone` |  |

## 7. 單場次表演（1303 筆，41 欄）`category_code=single_event` ← officer_a 專屬

| col | R1/R2 標題 | DB 欄位 | 備註 |
|---:|---|---|---|
| 11 | 申請人/主辦單位/持證者 → 申請日期 | `apply_date` |  |
| 12 | → 主辦單位(持證人) | `holder_name` |  |
| 13 | → 統一編號 | `extra.holder_tax_id` | 已有 col 8 是發票統編 |
| 14 | → 電話 | `applicant_phone` |  |
| 15 | → 傳真 | `applicant_fax` |  |
| 16 | → 地址 | `use_address` |  |
| 17 | 節目/活動資料 → 節目名稱 | `extra.event_name` |  |
| 18 | → 演出曲目 | `extra.songs` |  |
| 19 | → 總曲數 | `extra.song_count` |  |
| 20 | → 活動地點 | `extra.venue` |  |
| 21 | → 地址 | `extra.venue_address` |  |
| 22 | → 場次 | `qty` | 場次數 |
| 23 | → 人數 | `extra.audience_size` |  |
| 24-29 | 授權期間 | `period_start/end` |  |
| 30 | 業務承辦人 → 所屬單位 | `extra.contact_org` |  |
| 31 | → 姓名 | `onsite_name` |  |
| 32 | → 職稱 | `extra.contact_title` |  |
| 33 | → 手機 | `onsite_mobile` |  |
| 34 | → 電話 | `onsite_phone` |  |
| 35 | → 分機 | `onsite_ext` |  |
| 36 | → 傳真 | `onsite_fax` |  |
| 37 | → 信箱 | `extra.contact_email` |  |
| 38-41 | 寄證地址 | `mail_zip/address/recipient/phone` |  |

## 8. 公開傳輸（200 筆，35 欄）`category_code=public_transmission` ※ 資料從 R2 開始

| col | 標題 | DB 欄位 | 備註 |
|---:|---|---|---|
| 11 | 申請日期 | `apply_date` |  |
| 12 | 持證人 | `holder_name` |  |
| 13 | 代表人 | `applicant_name` |  |
| 14 | 聯絡人 | `onsite_name` |  |
| 15 | 電話 | `applicant_phone` |  |
| 16 | 傳真 | `applicant_fax` |  |
| 17 | E-mail | `extra.email` |  |
| 18 | 郵區 | `use_zip` |  |
| 19 | 地址 | `use_address` |  |
| 20 | 使用類型 | `holder_type` |  |
| 21 | 營收/來源 | `extra.has_revenue` |  |
| 22 | 平台名稱 | `extra.platform_name` |  |
| 23 | 網址 | `extra.platform_url` |  |
| 24 | 公開傳輸曲目 | `extra.songs` |  |
| 25 | (空) | — | 跳過 |
| 26-31 | 起年/起月/起日/迄年/迄月/迄日 | `period_start/end` | 平面結構 |
| 32 | 郵區 | `mail_zip` |  |
| 33 | 收件地址 | `mail_address` |  |
| 34 | 收件人 | `mail_recipient` |  |
| 35 | (空) | — | 跳過 |

⚠️ 沒有 `source`、`officer`、`action_type` 欄位 — 是否需要補進？

## 9. 告別式（40 筆，39 欄）`category_code=funeral`

| col | 標題 | DB 欄位 | 備註 |
|---:|---|---|---|
| 11 | 申請日期 | `apply_date` |  |
| 12 | 申請人 | `applicant_name` |  |
| 13 | 手機 | `applicant_mobile` |  |
| 14 | 電話 | `applicant_phone` |  |
| 15 | 傳真 | `applicant_fax` |  |
| 16 | 持證者 | `holder_name` |  |
| 17 | 儀式名稱 | `extra.ceremony_name` |  |
| 18 | 演出曲目 | `extra.songs` |  |
| 19 | 語言別 | `extra.language` |  |
| 20 | 總曲數 | `extra.song_count` |  |
| 21 | 儀式地點 | `extra.venue` |  |
| 22 | 地址 | `use_address` |  |
| 23 | 場次 | `qty` |  |
| 24-29 | 授權期間 | `period_start/end` |  |
| 30 | 禮儀公司/公司名 | `extra.funeral_company` |  |
| 31 | → 姓名 | `onsite_name` |  |
| 32 | → 手機 | `onsite_mobile` |  |
| 33 | → 電話 | `onsite_phone` |  |
| 34 | → 傳真 | `onsite_fax` |  |
| 35 | → 信箱 | `extra.contact_email` |  |
| 36-39 | 寄證地址 | `mail_zip/address/recipient/phone` |  |

⚠️ 沒有 `source`、`officer`、`action_type` 欄位

## 10. 坪數-顯示器（90 筆，33 欄）`category_code=display`

| col | 標題 | DB 欄位 | 備註 |
|---:|---|---|---|
| 11 | 申請日期 | `apply_date` |  |
| 12 | 單位名稱/持證者 | `holder_name` |  |
| 13 | 電話 | `applicant_phone` |  |
| 14 | 分機 | `extra.applicant_ext` |  |
| 15 | 傳真 | `applicant_fax` |  |
| 16 | 聯絡人 | `applicant_name` |  |
| 17 | Email | `extra.email` |  |
| 18 | 活動名稱 | `extra.event_name` |  |
| 19 | 使用地址 | `use_address` |  |
| 20 | 坪數 | `extra.floor_area` | int |
| 21 | 顯示器 | `qty` | int（顯示器數）|
| 22-27 | 授權期間 | `period_start/end` |  |
| 28 | 使用歌曲 | `extra.songs` |  |
| 29 | 語言 | `extra.language` |  |
| 30-33 | 寄證地址 | `mail_zip/address/recipient/phone` |  |

⚠️ 沒有 `source`、`officer`、`action_type` 欄位

## 11. 大廳-宴會廳-客房（50 筆，34 欄）`category_code=hotel`

| col | 標題 | DB 欄位 | 備註 |
|---:|---|---|---|
| 11 | 辦理項目 | `action_type` |  |
| 12 | 申請日期 | `apply_date` |  |
| 13 | 持證者 | `holder_name` |  |
| 14 | 負責人 | `applicant_name` |  |
| 15 | 電話 | `applicant_phone` |  |
| 16 | 分機 | `extra.applicant_ext` |  |
| 17 | 傳真 | `applicant_fax` |  |
| 18 | 聯絡人 | `onsite_name` |  |
| 19 | 手機 | `onsite_mobile` |  |
| 20 | Email | `extra.email` |  |
| 21 | 使用地址 | `use_address` |  |
| 22 | 授權內容 | `holder_type` | 大廳/宴會廳/客房 |
| 23 | 坪數 | `extra.floor_area` |  |
| 24 | 客房數 | `qty` |  |
| 25-30 | 授權期間 | `period_start/end` |  |
| 31-34 | 寄證地址 | `mail_zip/address/recipient/phone` |  |

⚠️ 沒有 `source`、`officer` 欄位

## 12. 競選活動（23 筆，42 欄）`category_code=campaign`

| col | R1/R2 標題 | DB 欄位 | 備註 |
|---:|---|---|---|
| 11 | 申請人/主辦單位/持證者 → 申請日期 | `apply_date` |  |
| 12 | → 主辦單位 | `holder_name` |  |
| 13 | → 統一編號 | `extra.holder_tax_id` |  |
| 14 | → 電話 | `applicant_phone` |  |
| 15 | → 傳真 | `applicant_fax` |  |
| 16 | → 地址 | `use_address` |  |
| 17 | 競選/活動資料 → 活動名稱 | `extra.event_name` |  |
| 18 | → 活動地點 | `extra.venue` |  |
| 19 | → 活動地址 | `extra.venue_address` |  |
| 20 | → 授權內容 | `holder_type` | 宣傳車/造勢/晚會… |
| 21 | → 宣傳車輛數 | `qty` |  |
| 22 | → 演出曲目 | `extra.songs` |  |
| 23 | → 語言別 | `extra.language` |  |
| 24 | → 總曲數 | `extra.song_count` |  |
| 25-30 | 授權期間(活動期間) | `period_start/end` |  |
| 31 | 業務承辦人 → 所屬單位 | `extra.contact_org` |  |
| 32 | → 姓名 | `onsite_name` |  |
| 33 | → 職稱 | `extra.contact_title` |  |
| 34 | → 手機 | `onsite_mobile` |  |
| 35 | → 電話 | `onsite_phone` |  |
| 36 | → 分機 | `onsite_ext` |  |
| 37 | → 傳真 | `onsite_fax` |  |
| 38 | → E-mail | `extra.contact_email` |  |
| 39-42 | 寄證地址 | `mail_zip/address/recipient/phone` |  |

⚠️ 沒有 `source`、`officer`、`action_type` 欄位

---

## 需要你確認的決定

### ❶ 12 種 `category_code` 命名
我用了英文 code（`karaoke`、`single_event`…）— 因為 `records.category_code` 是 ForeignKey 到 `categories.code`，看你想：
- (a) 用英文代碼：`karaoke / community / charity_karaoke / self_ktv / street_performer / transport / single_event / public_transmission / funeral / display / hotel / campaign`
- (b) 直接用中文 sheet 名稱當 code

### ❷ 缺欄位的處理
公開傳輸 / 告別式 / 坪數-顯示器 / 大廳客房 / 競選 這幾個 sheet **沒有「提報、承辦人、辦理項目」** 欄位。
- (a) 匯入時這 3 欄留 NULL（**推薦**）
- (b) 設 default 值（如 `source='自辦'`、`action_type='新申辦'`）

### ❸ 同一筆有兩個「統一編號」（單場次表演、競選活動）
col 8 是發票統一編號（給會計開發票用），col 13 R2 也叫統一編號（屬於主辦單位/持證人）。實務上多半一樣，但可能不同。
- (a) col 8 → `tax_id`，col 13 → `extra.holder_tax_id`（**推薦**，保留兩份）
- (b) 統一用 col 8，忽略 col 13

### ❹ 日期欄位（民國年）容錯
有些 sheet 的 `發證日`、`申請日期` 是空的（如電腦伴唱機 R3 的發證日為空）。
- (a) 空就 NULL（**推薦**）
- (b) 強制要求每筆都要有

### ❺ `holder_type`（性質）的對應
電腦伴唱機 col 21 是「性質」（餐廳/咖啡廳/網咖…），我對到 `holder_type`。
公開傳輸 col 20 「使用類型」（網路直播平台等）也對到 `holder_type`。
大廳客房 col 22 「授權內容」（大廳/宴會廳/客房）也對到 `holder_type`。
3 種 sheet 的「holder_type」意義其實不太一樣，但同欄位 OK 嗎？還是要分到 extra？

### ❻ extra 欄位命名
我用英文 key（`event_name`、`songs`、`language`...）。你要不要改用中文 key（`活動名稱`、`演出曲目`...）？英文 key 寫程式較順、中文 key 對使用者直覺。
- (a) 英文 key（**推薦**）
- (b) 中文 key

---

**請逐項回覆 ❶~❻，或直接「都照推薦」**。確認後我寫 `import_excel.py`。
