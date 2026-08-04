# API Specification

> Kontrak antara frontend, backend, dan AI agent yang mengerjakan endpoint. Konsistensi format di sini WAJIB diikuti.

## Konvensi Umum
- Base URL: `https://api.example.com/v1`
- Format response sukses:
```json
{ "success": true, "data": {}, "message": "" }
```
- Format response error:
```json
{ "success": false, "error": { "code": "", "message": "" } }
```
- Autentikasi: Bearer Token (JWT) di header `Authorization`

## Daftar Endpoint

### Auth
| Method | Endpoint | Deskripsi | Auth Required |
|---|---|---|---|
| POST | /auth/register | Registrasi user baru | Tidak |
| POST | /auth/login | Login, return token | Tidak |

**POST /auth/login**
Request:
```json
{ "email": "string", "password": "string" }
```
Response 200:
```json
{ "success": true, "data": { "token": "string", "user": {} } }
```
Response 401:
```json
{ "success": false, "error": { "code": "INVALID_CREDENTIALS", "message": "Email atau password salah" } }
```

### [Tambahkan resource lain, misal: Orders, Products, dsb]
| Method | Endpoint | Deskripsi | Auth Required |
|---|---|---|---|
| | | | |

### Data Profiling

`GET /datasets/{dataset_id}` mengembalikan `columns[]` dengan field kompatibel lama
(`inferred_type`, `completeness`, `uniqueness`, `consistency`, `null_count`,
`unique_count`, `top_values`, `stats`) dan detail profiling berikut:

- `top_values[]`: `value`, `count`, dan `percentage` dari nilai non-missing.
- `stats.physical_type`, `stats.length.{min,max,mean,median}` untuk structure discovery.
- `stats.null_count`, `stats.blank_count`, `stats.non_missing_count`,
  `stats.duplicate_count`, dan `stats.is_candidate_key`.
- Numerik: `stats.{min,max,mean,median,std,q1,q3}`; tanggal: `stats.{min,max}`.
- Teks: `stats.patterns[]` berisi `regex`, `signature`, `count`, `percentage`, dan `example`.

NULL dan string kosong/whitespace sama-sama dianggap missing untuk `completeness` dan
`null_count` tingkat atas; rinciannya tetap dipisahkan di dalam `stats`.

### Relationship Discovery

`POST /cross-dataset-rules/{rule_id}/run` untuk rule `referential_integrity`
menambahkan `relationship_profile` pada respons:

```json
{
  "relationship_profile": {
    "matched": 95,
    "key_overlap": 0.95,
    "orphan_count": 5,
    "orphan_rate": 0.05
  }
}
```

## Error Codes Global
| Code | HTTP Status | Arti |
|---|---|---|
| VALIDATION_ERROR | 400 | Input tidak valid |
| UNAUTHORIZED | 401 | Token tidak valid/expired |
| FORBIDDEN | 403 | Tidak punya akses |
| NOT_FOUND | 404 | Resource tidak ditemukan |
| SERVER_ERROR | 500 | Kesalahan server |

## Pagination Standard
```
GET /resource?page=1&limit=20
```
```json
{ "data": [], "pagination": { "page": 1, "limit": 20, "total": 100 } }
```
