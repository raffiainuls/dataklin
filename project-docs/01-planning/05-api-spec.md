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
