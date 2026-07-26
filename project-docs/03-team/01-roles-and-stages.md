# Role & Stage Project

> Menjelaskan siapa/apa yang berperan di tiap tahap project, termasuk pembagian kerja antar AI agent kalau memakai multi-agent.

## 1. Tahapan Project (Stage)
| Stage | Tujuan | Deliverable | Kriteria Pindah ke Stage Berikutnya |
|---|---|---|---|
| 1. Discovery & Planning | Menyusun PRD, riset kebutuhan | PRD, Risk Register | PRD di-approve stakeholder |
| 2. Design | Menyusun arsitektur, wireframe, design system | Architecture doc, wireframe, design system | Desain di-review & disetujui |
| 3. Development | Implementasi fitur sesuai ticket | Kode, unit test | Semua ticket P0 selesai |
| 4. Testing & QA | Uji fungsional, edge case, performa | Test report, bug list | Kritikal bug = 0 |
| 5. Deployment | Rilis ke production | Release notes | Sistem stabil di production |
| 6. Maintenance | Monitoring, perbaikan, iterasi | Changelog, bugfix | - |

## 2. Role dalam Project

### Role Manusia
| Role | Tanggung Jawab |
|---|---|
| Product Owner | Menentukan prioritas fitur, approve requirement |
| Project Manager | Mengatur timeline, koordinasi tim |
| Reviewer/QA Manusia | Review hasil kerja AI agent sebelum merge/deploy |

### Role AI Agent
| Nama Agent | Tanggung Jawab | Input yang Dibutuhkan | Output yang Dihasilkan |
|---|---|---|---|
| Agent-Planner | Memecah PRD jadi ticket kanban | PRD | kanban_board.html terisi |
| Agent-Backend | Implementasi API & logic server | API spec, data model | Kode backend + test |
| Agent-Frontend | Implementasi UI sesuai wireframe | Wireframe, design system | Kode frontend |
| Agent-QA | Testing fungsional & edge case | Edge case doc, acceptance criteria | Test report |
| Agent-DevOps | Setup deployment & CI/CD | Architecture doc, tech stack | Pipeline & environment |

> Sesuaikan jumlah dan nama agent dengan kebutuhan project kamu. Tidak semua project butuh semua role di atas.

## 3. Matriks Tanggung Jawab (RACI) — opsional
| Aktivitas | Responsible | Accountable | Consulted | Informed |
|---|---|---|---|---|
| | | | | |
