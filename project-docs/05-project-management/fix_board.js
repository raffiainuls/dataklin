const fs = require('fs');
let content = fs.readFileSync('project-docs/05-project-management/kanban_board.html', 'utf8');

// Fix missing comma
content = content.replace(/\}\s*\{(\s*id:"VD-306")/g, "},\n  {\n$1");

// Add urgent ticket
const newTicket = `  {
    id:"VD-311", title:"[URGENT] Pembuatan Comprehensive Test Dataset untuk Seluruh Use Case",
    description:"Buat dataset dummy berukuran cukup besar yang secara sengaja mencakup seluruh use case platform: entitas duplikat (exact & fuzzy), anomali (outlier statistik), missing values, PII leakage, referential integrity lintas-dataset, drift data, dan pelanggaran berbagai tipe business rules (lintas-kolom, regex, range). Sangat mendesak untuk simulasi demo, E2E testing (Playwright), serta validasi unjuk kerja algoritma probabilitas Dataklin.",
    acceptance:["Script generator atau file CSV master tersedia","Dataset mencakup duplikasi data dengan noise/typo (Fuzzy)","Dataset memiliki baris anomali statistik", "Dataset memicu rule PII dan Cross-Column", "Dataset siap di-load oleh script testing"],
    priority:"High", estimate:"S", assignee:"QA / Data Engineer", dependencies:"-",
    status:"todo", blocker:"",
    log:[{ts:"2026-07-26 10:00", note:"Tiket urgent ditambahkan sesuai permintaan prioritas untuk testing menyeluruh"}]
  },
`;
content = content.replace(
  /let tickets = \[\n/g,
  "let tickets = [\n" + newTicket
);

fs.writeFileSync('project-docs/05-project-management/kanban_board.html', content);
console.log("Board fixed");
