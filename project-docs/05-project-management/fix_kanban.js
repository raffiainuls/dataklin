const fs = require('fs');

let content = fs.readFileSync('kanban_board.html', 'utf8');

const newTicket = `  {
    id:"VD-310", title:"[Feature] Perluasan Statistik Profiling (Min/Max & Format Regex)",
    description:"Informasi profil kolom saat ini hanya menampilkan Completeness dan Uniqueness. Diperlukan penambahan metrik statistik lanjutan seperti Nilai Minimum, Nilai Maksimum (untuk angka/tanggal), dan deteksi/distribusi variasi pola string (Regex format) untuk melihat ragam format data dalam satu kolom.",
    acceptance:["UI Detail Dataset menampilkan metrik Min dan Max untuk kolom numerik/tanggal","UI menampilkan daftar ragam pattern regex (contoh: format tanggal yang tercampur) beserta distribusinya","Worker backend menghitung metrik ini saat proses profiling"],
    priority:"Medium", estimate:"M", assignee:"Unassigned", dependencies:"-",
    status:"backlog", blocker:"",
    log:[{ts:"2026-07-25 17:35", note:"Ticket dibuat berdasarkan request user untuk profiling lanjutan"}]
  },
`;

// Insert after VD-305
content = content.replace(
  /id:"VD-305"[\s\S]*?log:\[.*?\]\n  \},/g,
  (match) => match + "\n" + newTicket
);

fs.writeFileSync('kanban_board.html', content);
console.log("Kanban board updated");
