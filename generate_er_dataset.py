"""Generate a ~1M row entity-resolution torture dataset with ground-truth labels.

Output columns:
    source_system, record_id, nik, full_name, gender, dob, alamat, phone_number,
    last_updated, use_case, expected_match, true_entity_id, pair_group_id, variant

`use_case` marks which scenario a row belongs to (`normal_data` when it is a
plain singleton). `true_entity_id` is the ground truth: rows sharing it are the
same human being, so precision/recall can be measured without manual labelling.

Usage:
    python generate_er_dataset.py                 # 1_000_000 rows + 200k ER-ready subset
    python generate_er_dataset.py --rows 50000    # smaller run for quick iteration
"""
from __future__ import annotations

import argparse
import csv
import os
import random
import tempfile
from datetime import date, timedelta

# --------------------------------------------------------------------------- #
# Reference data (Indonesian flavoured, hand curated so perturbations stay
# realistic instead of random noise).
# --------------------------------------------------------------------------- #

FIRST_NAMES_MALE = [
    "Raffi", "Reza", "Ahmad", "Muhammad", "Budi", "Agus", "Dwi", "Eko", "Bayu",
    "Rizki", "Fajar", "Hendra", "Iwan", "Joko", "Krisna", "Lukman", "Andi",
    "Bagus", "Cahyo", "Dimas", "Erwin", "Ferry", "Gilang", "Hafiz", "Ilham",
    "Jefri", "Kevin", "Yusuf", "Naufal", "Oki", "Panji", "Rangga", "Satria",
    "Taufik", "Wahyu", "Yoga", "Zaki", "Arif", "Bambang", "Candra", "Dedi",
    "Faisal", "Galih", "Herman", "Irfan", "Kurniawan", "Maulana", "Nugroho",
]
FIRST_NAMES_FEMALE = [
    "Siti", "Dewi", "Ayu", "Putri", "Rina", "Sari", "Fitri", "Indah", "Lestari",
    "Maya", "Nisa", "Okta", "Puspita", "Ratna", "Sinta", "Tiara", "Utami",
    "Wulan", "Yuni", "Zahra", "Anggun", "Bella", "Citra", "Diah", "Endah",
    "Farida", "Gita", "Hana", "Intan", "Jihan", "Kartika", "Laila", "Melati",
    "Novita", "Rahma", "Salsabila", "Tantri", "Vina", "Widya", "Yasmin",
]
MIDDLE_NAMES = [
    "Ainul", "Nur", "Dwi", "Tri", "Adi", "Bagus", "Cahya", "Eka", "Fitria",
    "Hidayat", "Kurnia", "Mulya", "Prasetya", "Rahmat", "Setia", "Wijaya",
    "Anugrah", "Bakti", "Daffa", "Fahmi", "Gunawan", "Hadi", "Iman", "Jaya",
]
LAST_NAMES = [
    "Afif", "Santoso", "Wijaya", "Nugroho", "Saputra", "Hidayat", "Kusuma",
    "Pratama", "Ramadhan", "Setiawan", "Utomo", "Wibowo", "Yudhoyono", "Halim",
    "Napitupulu", "Simbolon", "Sitorus", "Tanjung", "Hutapea", "Ginting",
    "Situmorang", "Panjaitan", "Lubis", "Harahap", "Siregar", "Nasution",
    "Prayoga", "Maulida", "Rahmawati", "Anggraini", "Puspitasari", "Handayani",
    "Suryani", "Wulandari", "Firmansyah", "Kurniawan", "Permana", "Gunawan",
    "Salim", "Tjahjono", "Soesanto", "Hartono", "Iskandar", "Mahendra",
]

# Phonetic spellings that Indonesian data entry genuinely produces.
PHONETIC_VARIANTS = {
    "muhammad": ["Muhamad", "Mohammad", "Mochamad", "Muchammad", "M."],
    "ahmad": ["Achmad", "Akhmad", "Ahmat"],
    "rizki": ["Rizky", "Riski", "Risky", "Rezki"],
    "raffi": ["Rafi", "Raffy", "Rafhi"],
    "reza": ["Reja", "Riza"],
    "yusuf": ["Jusuf", "Yusup", "Joesoef"],
    "wahyu": ["Wahju", "Wayu"],
    "cahya": ["Tjahja", "Cahaya"],
    "fitri": ["Fitry", "Fithri"],
    "dewi": ["Dewie", "Devi"],
    "putri": ["Putry", "Poetri"],
    "siti": ["Sitti", "Syiti"],
    "santoso": ["Soesanto", "Santosa"],
    "hartono": ["Hartana", "Hartonoh"],
    "salim": ["Saleem", "Halim"],
    "zahra": ["Zahrah", "Sahra"],
    "hidayat": ["Hidajat", "Hidayah"],
    "setiawan": ["Setyawan", "Setiyawan"],
    "kurniawan": ["Kurnyawan", "Koerniawan"],
}

# (region_code, city, province, city_abbrev, postcode_prefix)
REGIONS = [
    ("3171", "Jakarta Selatan", "DKI Jakarta", "JKT", "129"),
    ("3172", "Jakarta Timur", "DKI Jakarta", "JAKTIM", "134"),
    ("3173", "Jakarta Pusat", "DKI Jakarta", "JKT PST", "104"),
    ("3174", "Jakarta Barat", "DKI Jakarta", "JAKBAR", "114"),
    ("3175", "Jakarta Utara", "DKI Jakarta", "JAKUT", "142"),
    ("3273", "Bandung", "Jawa Barat", "BDG", "401"),
    ("3276", "Depok", "Jawa Barat", "DPK", "164"),
    ("3216", "Bekasi", "Jawa Barat", "BKS", "171"),
    ("3674", "Tangerang Selatan", "Banten", "TANGSEL", "154"),
    ("3374", "Semarang", "Jawa Tengah", "SMG", "501"),
    ("3578", "Surabaya", "Jawa Timur", "SBY", "602"),
    ("3573", "Malang", "Jawa Timur", "MLG", "651"),
    ("3402", "Sleman", "DI Yogyakarta", "YK", "555"),
    ("5171", "Denpasar", "Bali", "DPS", "802"),
    ("1275", "Medan", "Sumatera Utara", "MDN", "201"),
    ("1471", "Pekanbaru", "Riau", "PKU", "282"),
    ("7371", "Makassar", "Sulawesi Selatan", "MKS", "902"),
    ("6371", "Banjarmasin", "Kalimantan Selatan", "BJM", "701"),
]

# (abbreviated form, fully expanded form)
STREETS = [
    ("Jend. Sudirman", "Jenderal Sudirman"),
    ("Jend. A. Yani", "Jenderal Ahmad Yani"),
    ("Jend. Gatot Subroto", "Jenderal Gatot Subroto"),
    ("Dr. Djunjunan", "Dokter Djunjunan"),
    ("Dr. Sutomo", "Dokter Sutomo"),
    ("Prof. Dr. Satrio", "Profesor Doktor Satrio"),
    ("H. Agus Salim", "Haji Agus Salim"),
    ("K.H. Wahid Hasyim", "Kyai Haji Wahid Hasyim"),
    ("K.H. Ahmad Dahlan", "Kyai Haji Ahmad Dahlan"),
    ("Ir. H. Juanda", "Insinyur Haji Juanda"),
    ("Letjen S. Parman", "Letnan Jenderal Slamet Parman"),
    ("Kol. Sugiono", "Kolonel Sugiono"),
    ("R.A. Kartini", "Raden Ajeng Kartini"),
    ("Ry. Bogor", "Raya Bogor"),
    ("Ry. Serpong", "Raya Serpong"),
    ("Diponegoro", "Diponegoro"),
    ("Merdeka Barat", "Merdeka Barat"),
    ("Pemuda", "Pemuda"),
    ("Cendrawasih", "Cendrawasih"),
    ("Melati Indah", "Melati Indah"),
    ("Kebon Jeruk", "Kebon Jeruk"),
    ("Pahlawan", "Pahlawan"),
    ("Veteran", "Veteran"),
    ("Rasuna Said", "Rasuna Said"),
    ("Mampang Prapatan", "Mampang Prapatan"),
]
# region_code -> (kelurahan options, kecamatan options). Keeps a generated
# address geographically plausible, which matters because UC4 reuses one address
# across a whole household.
REGION_AREAS = {
    "3171": (["Karet", "Kuningan Barat", "Pela Mampang", "Cilandak Barat"],
             ["Setiabudi", "Mampang Prapatan", "Tebet", "Cilandak"]),
    "3172": (["Cipinang", "Rawamangun", "Klender"], ["Pulo Gadung", "Duren Sawit", "Jatinegara"]),
    "3173": (["Gondangdia", "Kebon Sirih", "Petojo Utara"], ["Menteng", "Gambir", "Tanah Abang"]),
    "3174": (["Kembangan Selatan", "Grogol", "Tomang"], ["Kembangan", "Grogol Petamburan", "Palmerah"]),
    "3175": (["Kelapa Gading Barat", "Sunter Jaya", "Pegangsaan Dua"], ["Kelapa Gading", "Tanjung Priok", "Koja"]),
    "3273": (["Cipaganti", "Sukajadi", "Lebak Gede"], ["Coblong", "Sukajadi", "Cidadap"]),
    "3276": (["Beji", "Pondok Cina", "Cinere"], ["Beji", "Cimanggis", "Limo"]),
    "3216": (["Jaka Sampurna", "Margahayu", "Harapan Indah"], ["Bekasi Barat", "Bekasi Timur", "Medan Satria"]),
    "3674": (["Lengkong Gudang", "Pondok Jagung", "Serua"], ["Serpong", "Serpong Utara", "Ciputat"]),
    "3374": (["Tembalang", "Pleburan", "Sampangan"], ["Tembalang", "Semarang Selatan", "Gajahmungkur"]),
    "3578": (["Wonokromo", "Sukolilo", "Rungkut Kidul"], ["Wonokromo", "Gubeng", "Rungkut"]),
    "3573": (["Klojen", "Lowokwaru", "Sawojajar"], ["Klojen", "Lowokwaru", "Blimbing"]),
    "3402": (["Condongcatur", "Caturtunggal", "Maguwoharjo"], ["Depok", "Ngaglik", "Mlati"]),
    "5171": (["Sanur Kaja", "Renon", "Ubung"], ["Denpasar Selatan", "Denpasar Timur", "Denpasar Utara"]),
    "1275": (["Polonia", "Petisah Tengah", "Padang Bulan"], ["Medan Baru", "Medan Petisah", "Medan Polonia"]),
    "1471": (["Simpang Baru", "Tangkerang", "Sukajadi"], ["Bukit Raya", "Tampan", "Sukajadi"]),
    "7371": (["Gunung Sari", "Karunrung", "Mappala"], ["Rappocini", "Panakkukang", "Tamalate"]),
    "6371": (["Kertak Baru", "Teluk Dalam", "Sungai Miai"], ["Banjarmasin Tengah", "Banjarmasin Utara", "Banjarmasin Barat"]),
}
COMPLEX_NAMES = [
    "Perumahan Indah", "Taman Sari Residence", "Griya Asri", "Bumi Serpong",
    "Villa Melati Mas", "Citra Garden", "Puri Indah", "Green Lake City",
    "Cluster Anggrek", "Kosan Makmur", "Apartemen Sudirman", "Grand Wisata",
]
NUMBER_WORDS = {
    1: "Satu", 2: "Dua", 3: "Tiga", 4: "Empat", 5: "Lima",
    6: "Enam", 7: "Tujuh", 8: "Delapan", 9: "Sembilan", 10: "Sepuluh",
}

# source_system -> (record_id prefix style, gender coding, date style)
SOURCE_SYSTEMS = {
    "web_app": ("WEB", "MF", "iso"),
    "crm": ("CRM", "LP", "iso_time"),
    "offline_store": ("OFF", "long", "slash"),
    "marketing_db": ("MKT", "MF", "iso"),
    "billing": ("BIL", "LP", "iso_time"),
    "shipping": ("SHP", "long", "slash"),
    "call_center": ("CC", "MF", "iso"),
    "mobile_app": ("MOB", "MF", "iso_time"),
    "loyalty": ("LOY", "LP", "iso"),
    "legacy_erp": ("ERP", "long", "compact"),
}
SOURCE_NAMES = list(SOURCE_SYSTEMS)

USE_CASES = {
    "uc1_fuzzy_typo_format": "MATCH",
    "uc2_missing_nik": "MATCH",
    "uc3_address_variation": "MATCH",
    "uc4_family_false_positive": "NO_MATCH",
    "uc5_entity_evolution": "MATCH",
    "normal_data": "SINGLE",
}

HEADER = [
    "source_system", "record_id", "nik", "full_name", "gender", "dob", "alamat",
    "phone_number", "last_updated", "use_case", "expected_match",
    "true_entity_id", "pair_group_id", "variant",
]


# --------------------------------------------------------------------------- #
# Primitives
# --------------------------------------------------------------------------- #

TODAY = date(2026, 8, 6)
# Clamp target for "last seen" timestamps: keeps the iso_time variant strictly
# in the past even when it lands on the newest possible day.
LAST_SEEN = TODAY - timedelta(days=1)


def later(base: date, rng: random.Random, max_days: int) -> date:
    """A date after `base` but never in the future."""
    return min(base + timedelta(days=rng.randint(1, max_days)), LAST_SEEN)


def make_district(rng: random.Random) -> str:
    """2-digit kecamatan code completing the 6-digit NIK region prefix."""
    return f"{rng.randint(1, 20):02d}"


def make_nik(rng: random.Random, region_code: str, district: str, dob: date,
             female: bool) -> str:
    """16 digits: 4 prov+kota + 2 kecamatan + DDMMYY (+40 on day for female) + 4 serial."""
    day = dob.day + 40 if female else dob.day
    return (f"{region_code}{district}{day:02d}{dob.month:02d}{dob.year % 100:02d}"
            f"{rng.randint(1, 9999):04d}")


def random_dob(rng: random.Random, min_age: int = 18, max_age: int = 70) -> date:
    today = TODAY
    days = rng.randint(min_age * 365, max_age * 365)
    return today - timedelta(days=days)


def make_name(rng: random.Random, female: bool, last_name: str | None = None) -> dict:
    first = rng.choice(FIRST_NAMES_FEMALE if female else FIRST_NAMES_MALE)
    middle = rng.choice(MIDDLE_NAMES) if rng.random() < 0.55 else ""
    last = last_name or rng.choice(LAST_NAMES)
    return {"first": first, "middle": middle, "last": last}


def render_name(parts: dict) -> str:
    return " ".join(p for p in (parts["first"], parts["middle"], parts["last"]) if p)


def make_phone(rng: random.Random) -> str:
    """Canonical local form; formatting variants are applied later."""
    prefix = rng.choice(["811", "812", "813", "815", "816", "817", "818",
                         "819", "821", "822", "838", "852", "856", "857",
                         "858", "877", "878", "895", "896", "899"])
    return "0" + prefix + "".join(str(rng.randint(0, 9)) for _ in range(rng.choice([7, 8])))


def make_address(rng: random.Random, region: tuple) -> dict:
    region_code, city, province, city_abbrev, postcode_prefix = region
    kelurahan_pool, kecamatan_pool = REGION_AREAS[region_code]
    return {
        "kind": rng.choice(["street", "street", "street", "complex"]),
        "street": rng.choice(STREETS),
        "number": rng.randint(1, 220),
        "kavling": rng.randint(1, 10) if rng.random() < 0.25 else None,
        "unit": f"{rng.randint(1, 25)}{rng.choice('ABCDEF')}" if rng.random() < 0.3 else None,
        "complex": rng.choice(COMPLEX_NAMES),
        "block": f"{rng.choice('ABCDEFGH')}/{rng.randint(1, 60)}",
        "rt": rng.randint(1, 15),
        "rw": rng.randint(1, 12),
        "has_rt": rng.random() < 0.4,
        "kelurahan": rng.choice(kelurahan_pool),
        "kecamatan": rng.choice(kecamatan_pool),
        "city": city,
        "city_abbrev": city_abbrev,
        "province": province,
        "postcode": postcode_prefix + f"{rng.randint(0, 99):02d}",
    }


def render_address(addr: dict, style: str) -> str:
    """style: 'abbrev' (Jl., Kav., JKT) | 'expanded' (Jalan, Kavling, Jakarta) | 'plain'."""
    parts: list[str] = []
    if addr["kind"] == "street":
        street = addr["street"][0] if style == "abbrev" else addr["street"][1]
        road = {"abbrev": "Jl.", "expanded": "Jalan", "plain": "Jalan"}[style]
        head = f"{road} {street}"
        if addr["kavling"] is not None:
            if style == "abbrev":
                head += f" Kav. {addr['kavling']}"
            elif style == "expanded":
                head += f" Kavling {NUMBER_WORDS[addr['kavling']]}"
            else:
                head += f" Kavling {addr['kavling']}"
        no = {"abbrev": "No.", "expanded": "Nomor", "plain": "No"}[style]
        head += f" {no} {addr['number']}"
        parts.append(head)
    else:
        complex_name = addr["complex"]
        if style == "abbrev":
            complex_name = (complex_name.replace("Perumahan", "Perum.")
                            .replace("Apartemen", "Apt.")
                            .replace("Cluster", "Clst."))
            parts.append(f"{complex_name} Blok {addr['block']}")
        elif style == "expanded":
            block, number = addr["block"].split("/")
            parts.append(f"{complex_name} Blok {block} Nomor {number}")
        else:
            parts.append(f"{complex_name} Blok {addr['block']}")

    if addr["unit"]:
        label = {"abbrev": "Apt.", "expanded": "Apartemen", "plain": "Unit"}[style]
        parts.append(f"{label} {addr['unit']}")
    if addr["has_rt"]:
        if style == "abbrev":
            parts.append(f"RT {addr['rt']:03d}/RW {addr['rw']:03d}")
        else:
            parts.append(f"RT {addr['rt']} RW {addr['rw']}")
    if style == "abbrev":
        parts.append(f"Kel. {addr['kelurahan']}")
        parts.append(f"Kec. {addr['kecamatan']}")
        parts.append(f"{addr['city_abbrev']} {addr['postcode']}")
    elif style == "expanded":
        parts.append(f"Kelurahan {addr['kelurahan']}")
        parts.append(f"Kecamatan {addr['kecamatan']}")
        parts.append(f"{addr['city']}, {addr['province']} {addr['postcode']}")
    else:
        parts.append(addr["kelurahan"])
        parts.append(addr["kecamatan"])
        parts.append(f"{addr['city']} {addr['postcode']}")
    return ", ".join(parts)


# --------------------------------------------------------------------------- #
# Perturbations
# --------------------------------------------------------------------------- #

CHAR_SUBS = {
    "f": "v", "v": "f", "b": "p", "p": "b", "s": "z", "z": "s", "i": "y",
    "y": "i", "k": "c", "c": "k", "u": "o", "o": "u", "a": "e", "e": "a",
    "d": "t", "t": "d", "m": "n", "n": "m",
}


def typo(rng: random.Random, word: str) -> str:
    """One realistic keyboard/spelling slip inside a single word."""
    if len(word) < 3:
        return word
    kind = rng.choice(["sub", "drop", "double", "swap"])
    i = rng.randrange(1, len(word) - 1)
    if kind == "sub":
        low = word[i].lower()
        if low in CHAR_SUBS:
            repl = CHAR_SUBS[low]
            return word[:i] + (repl.upper() if word[i].isupper() else repl) + word[i + 1:]
        return word
    if kind == "drop":
        return word[:i] + word[i + 1:]
    if kind == "double":
        return word[:i] + word[i] + word[i:]
    return word[:i] + word[i + 1] + word[i] + word[i + 2:]


def perturb_name(rng: random.Random, parts: dict) -> tuple[str, str]:
    """Return (rendered name, variant tag)."""
    kind = rng.choices(
        ["typo", "phonetic", "initial_middle", "initial_last", "title",
         "reversed", "case", "extra_space", "drop_middle"],
        weights=[26, 18, 14, 8, 8, 6, 6, 6, 8],
    )[0]
    p = dict(parts)

    if kind == "typo":
        target = rng.choice(["first", "last"] + (["middle"] if p["middle"] else []))
        p[target] = typo(rng, p[target])
        return render_name(p), "name_typo"
    if kind == "phonetic":
        for key in ("first", "middle", "last"):
            options = PHONETIC_VARIANTS.get(p[key].lower())
            if options:
                p[key] = rng.choice(options)
                return render_name(p), "name_phonetic"
        p["first"] = typo(rng, p["first"])
        return render_name(p), "name_typo"
    if kind == "initial_middle" and p["middle"]:
        p["middle"] = p["middle"][0] + "."
        return render_name(p), "name_middle_initial"
    if kind == "initial_last":
        p["last"] = p["last"][0] + "."
        return render_name(p), "name_last_initial"
    if kind == "title":
        title = rng.choice(["Bpk.", "Ibu", "Bapak", "Sdr.", "H.", "Dr."])
        return f"{title} {render_name(p)}", "name_with_title"
    if kind == "reversed":
        head = " ".join(x for x in (p["first"], p["middle"]) if x)
        return f"{p['last']}, {head}", "name_reversed"
    if kind == "case":
        return render_name(p).upper(), "name_uppercase"
    if kind == "extra_space":
        joined = "   ".join(x for x in (p["first"], p["middle"], p["last"]) if x)
        return f"  {joined} ", "name_extra_space"
    p["middle"] = ""
    return render_name(p), "name_drop_middle"


DOB_FORMATS = ["iso", "slash_dmy", "dash_dmy", "slash_mdy", "long_id", "compact", "dot_dmy"]
MONTHS_ID = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
             "Agustus", "September", "Oktober", "November", "Desember"]


def format_dob(d: date, style: str) -> str:
    if style == "iso":
        return d.isoformat()
    if style == "slash_dmy":
        return f"{d.day:02d}/{d.month:02d}/{d.year}"
    if style == "dash_dmy":
        return f"{d.day:02d}-{d.month:02d}-{d.year}"
    if style == "slash_mdy":                      # ambiguous on purpose
        return f"{d.month:02d}/{d.day:02d}/{d.year}"
    if style == "long_id":
        return f"{d.day} {MONTHS_ID[d.month - 1]} {d.year}"
    if style == "compact":
        return f"{d.year}{d.month:02d}{d.day:02d}"
    return f"{d.day:02d}.{d.month:02d}.{d.year}"


PHONE_FORMATS = ["local", "e164", "e164_dash", "spaced", "no_leading_zero",
                 "country_no_plus", "paren", "dotted"]


def format_phone(phone: str, style: str) -> str:
    body = phone[1:]                               # strip leading 0
    if style == "local":
        return phone
    if style == "e164":
        return "+62" + body
    if style == "e164_dash":
        return f"+62{body[:3]}-{body[3:7]}-{body[7:]}"
    if style == "spaced":
        return f"{phone[:4]} {phone[4:8]} {phone[8:]}"
    if style == "no_leading_zero":
        return body
    if style == "country_no_plus":
        return "62" + body
    if style == "paren":
        return f"({phone[:4]}){phone[4:]}"
    return ".".join([phone[:4], phone[4:8], phone[8:]])


def format_gender(female: bool, coding: str) -> str:
    if coding == "MF":
        return "F" if female else "M"
    if coding == "LP":
        return "P" if female else "L"
    return "Perempuan" if female else "Laki-laki"


def format_updated(d: date, style: str, rng: random.Random) -> str:
    if style == "iso":
        return d.isoformat()
    if style == "iso_time":
        return f"{d.isoformat()} {rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}:{rng.randint(0, 59):02d}"
    if style == "slash":
        return f"{d.day:02d}/{d.month:02d}/{d.year}"
    return f"{d.year}{d.month:02d}{d.day:02d}"


def make_record_id(rng: random.Random, source: str, counter: int) -> str:
    prefix = SOURCE_SYSTEMS[source][0]
    if source == "offline_store":
        return f"{prefix}-{counter:07d}-{rng.randrange(16**4):04X}"
    if source == "legacy_erp":
        return f"{prefix}{counter:09d}"
    return f"{prefix}-{counter:08d}"


# --------------------------------------------------------------------------- #
# Row assembly
# --------------------------------------------------------------------------- #

class Builder:
    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.counter = 0
        self.entity_seq = 0
        self.group_seq = 0

    def next_entity(self) -> str:
        self.entity_seq += 1
        return f"E{self.entity_seq:07d}"

    def next_group(self) -> str:
        self.group_seq += 1
        return f"G{self.group_seq:07d}"

    def row(self, *, source: str, nik: str | None, name: str, female: bool,
            dob: date | None, addr_text: str | None, phone: str | None,
            updated: date, use_case: str, entity_id: str, group_id: str,
            variant: str, dob_style: str | None = None,
            phone_style: str | None = None) -> list:
        self.counter += 1
        _, gender_coding, date_style = SOURCE_SYSTEMS[source]
        rng = self.rng
        return [
            source,
            make_record_id(rng, source, self.counter),
            nik or "",
            name,
            format_gender(female, gender_coding) if rng.random() > 0.02 else "",
            format_dob(dob, dob_style or "iso") if dob else "",
            addr_text or "",
            format_phone(phone, phone_style or "local") if phone else "",
            format_updated(updated, date_style, rng),
            use_case,
            USE_CASES[use_case],
            entity_id,
            group_id,
            variant,
        ]


def two_sources(rng: random.Random) -> tuple[str, str]:
    a, b = rng.sample(SOURCE_NAMES, 2)
    return a, b


def gen_normal(b: Builder) -> list[list]:
    """A single clean-ish record that must stay its own entity."""
    rng = b.rng
    female = rng.random() < 0.5
    region = rng.choice(REGIONS)
    dob = random_dob(rng)
    parts = make_name(rng, female)
    addr = make_address(rng, region)
    phone = make_phone(rng)
    source = rng.choice(SOURCE_NAMES)
    # Real-world incompleteness even in "normal" rows.
    nik = make_nik(rng, region[0], make_district(rng), dob, female) if rng.random() > 0.06 else None
    return [b.row(
        source=source, nik=nik, name=render_name(parts), female=female,
        dob=dob if rng.random() > 0.03 else None,
        addr_text=render_address(addr, rng.choice(["abbrev", "plain", "expanded"]))
        if rng.random() > 0.05 else None,
        phone=phone if rng.random() > 0.08 else None,
        updated=random_recent(rng), use_case="normal_data",
        entity_id=b.next_entity(), group_id=b.next_group(), variant="singleton",
        dob_style=rng.choice(DOB_FORMATS), phone_style=rng.choice(PHONE_FORMATS),
    )]


def random_recent(rng: random.Random) -> date:
    return LAST_SEEN - timedelta(days=rng.randint(0, 1200))


def gen_uc1(b: Builder) -> list[list]:
    """UC1: identical NIK, typo'd name, different dob/phone formatting."""
    rng = b.rng
    female = rng.random() < 0.5
    region = rng.choice(REGIONS)
    dob = random_dob(rng)
    parts = make_name(rng, female)
    nik = make_nik(rng, region[0], make_district(rng), dob, female)
    addr = make_address(rng, region)
    phone = make_phone(rng)
    src_a, src_b = two_sources(rng)
    entity, group = b.next_entity(), b.next_group()
    updated_a = random_recent(rng)
    updated_b = later(updated_a, rng, 500)

    name_b, name_variant = perturb_name(rng, parts)
    dob_style_b = rng.choice([f for f in DOB_FORMATS if f != "iso"])
    phone_style_b = rng.choice([f for f in PHONE_FORMATS if f != "local"])
    variant = f"same_nik+{name_variant}+dob_{dob_style_b}+phone_{phone_style_b}"

    rows = [
        b.row(source=src_a, nik=nik, name=render_name(parts), female=female, dob=dob,
              addr_text=render_address(addr, "abbrev"), phone=phone, updated=updated_a,
              use_case="uc1_fuzzy_typo_format", entity_id=entity, group_id=group,
              variant=variant, dob_style="iso", phone_style="local"),
        b.row(source=src_b, nik=nik, name=name_b, female=female, dob=dob,
              addr_text=render_address(addr, "plain"), phone=phone, updated=updated_b,
              use_case="uc1_fuzzy_typo_format", entity_id=entity, group_id=group,
              variant=variant, dob_style=dob_style_b, phone_style=phone_style_b),
    ]
    if rng.random() < 0.12:                        # occasional third sighting
        name_c, extra = perturb_name(rng, parts)
        rows.append(b.row(
            source=rng.choice(SOURCE_NAMES), nik=nik, name=name_c, female=female, dob=dob,
            addr_text=render_address(addr, "expanded"), phone=phone,
            updated=later(updated_b, rng, 300),
            use_case="uc1_fuzzy_typo_format", entity_id=entity, group_id=group,
            variant=f"{variant}+3rd_{extra}", dob_style=rng.choice(DOB_FORMATS),
            phone_style=rng.choice(PHONE_FORMATS)))
    return rows


def gen_uc2(b: Builder) -> list[list]:
    """UC2: one side has no NIK — must match on name + dob + phone."""
    rng = b.rng
    female = rng.random() < 0.5
    region = rng.choice(REGIONS)
    dob = random_dob(rng)
    parts = make_name(rng, female)
    nik = make_nik(rng, region[0], make_district(rng), dob, female)
    addr = make_address(rng, region)
    phone = make_phone(rng)
    src_a, src_b = two_sources(rng)
    entity, group = b.next_entity(), b.next_group()
    updated_a = random_recent(rng)

    name_a, name_variant = perturb_name(rng, parts)
    phone_style_a = rng.choice(PHONE_FORMATS)
    both_null = rng.random() < 0.18                # neither system captured the NIK
    variant = f"nik_null_{'both' if both_null else 'one_side'}+{name_variant}"

    return [
        b.row(source=src_a, nik=None, name=name_a, female=female, dob=dob,
              addr_text=render_address(addr, "abbrev"), phone=phone, updated=updated_a,
              use_case="uc2_missing_nik", entity_id=entity, group_id=group,
              variant=variant, dob_style="iso", phone_style=phone_style_a),
        b.row(source=src_b, nik=None if both_null else nik, name=render_name(parts),
              female=female, dob=dob,
              addr_text=render_address(addr, "plain"), phone=phone,
              updated=later(updated_a, rng, 400),
              use_case="uc2_missing_nik", entity_id=entity, group_id=group,
              variant=variant, dob_style=rng.choice(DOB_FORMATS),
              phone_style=rng.choice(PHONE_FORMATS)),
    ]


def gen_uc3(b: Builder) -> list[list]:
    """UC3: no NIK on either side; only the address style differs (extremely)."""
    rng = b.rng
    female = rng.random() < 0.5
    region = rng.choice(REGIONS)
    dob = random_dob(rng)
    parts = make_name(rng, female)
    addr = make_address(rng, region)
    phone = make_phone(rng)
    src_a, src_b = two_sources(rng)
    entity, group = b.next_entity(), b.next_group()
    updated_a = random_recent(rng)

    keep_dob = rng.random() < 0.6
    keep_phone = rng.random() < 0.5
    hard = rng.random() < 0.25                     # also drop the phone on side A
    variant = (f"nik_null_both+addr_abbrev_vs_expanded"
               f"+dob_{'same' if keep_dob else 'missing_one_side'}"
               f"+phone_{'same' if keep_phone else 'missing'}")

    return [
        b.row(source=src_a, nik=None, name=render_name(parts), female=female, dob=dob,
              addr_text=render_address(addr, "abbrev"),
              phone=None if hard or not keep_phone else phone, updated=updated_a,
              use_case="uc3_address_variation", entity_id=entity, group_id=group,
              variant=variant, dob_style="iso", phone_style="local"),
        b.row(source=src_b, nik=None, name=render_name(parts), female=female,
              dob=dob if keep_dob else None,
              addr_text=render_address(addr, "expanded"),
              phone=phone if keep_phone else None,
              updated=later(updated_a, rng, 400),
              use_case="uc3_address_variation", entity_id=entity, group_id=group,
              variant=variant, dob_style=rng.choice(DOB_FORMATS),
              phone_style=rng.choice([f for f in PHONE_FORMATS if f != "local"])),
    ]


def gen_uc4(b: Builder) -> list[list]:
    """UC4: same household / same name, DIFFERENT people. Must NOT merge."""
    rng = b.rng
    region = rng.choice(REGIONS)
    addr = make_address(rng, region)
    district = make_district(rng)          # one kecamatan for the whole household
    household_phone = make_phone(rng)
    group = b.next_group()
    flavour = rng.choices(["sibling", "twin", "parent_child", "namesake"],
                          weights=[42, 15, 25, 18])[0]
    rows: list[list] = []

    if flavour == "namesake":
        # Identical full name, unrelated people, different city and dob.
        female = rng.random() < 0.5
        parts = make_name(rng, female)
        for i in range(2):
            r = rng.choice(REGIONS)
            dob_i = random_dob(rng)
            rows.append(b.row(
                source=rng.choice(SOURCE_NAMES),
                nik=make_nik(rng, r[0], make_district(rng), dob_i, female),
                name=render_name(parts),
                female=female, dob=dob_i,
                addr_text=render_address(make_address(rng, r), rng.choice(["abbrev", "plain"])),
                phone=make_phone(rng), updated=random_recent(rng),
                use_case="uc4_family_false_positive", entity_id=b.next_entity(),
                group_id=group, variant="namesake_different_person",
                dob_style=rng.choice(DOB_FORMATS), phone_style=rng.choice(PHONE_FORMATS)))
        return rows

    shared_last = rng.choice(LAST_NAMES)
    shared_middle = rng.choice(MIDDLE_NAMES)
    members: list[tuple[dict, date, bool]] = []

    if flavour == "twin":
        dob = random_dob(rng, 18, 40)
        for _ in range(2):
            female = rng.random() < 0.5
            parts = make_name(rng, female, shared_last)
            parts["middle"] = shared_middle          # same middle + last name
            members.append((parts, dob, female))     # identical dob: hardest case
    elif flavour == "sibling":
        base = random_dob(rng, 18, 40)
        n = 3 if rng.random() < 0.25 else 2
        for i in range(n):
            female = rng.random() < 0.5
            parts = make_name(rng, female, shared_last)
            parts["middle"] = shared_middle
            members.append((parts, base - timedelta(days=rng.randint(400, 2600) * (i + 1)), female))
    else:                                            # parent_child
        parent_female = rng.random() < 0.5
        parent = make_name(rng, parent_female, shared_last)
        parent["middle"] = shared_middle
        parent_dob = random_dob(rng, 45, 65)
        members.append((parent, parent_dob, parent_female))
        child_female = rng.random() < 0.5
        child = make_name(rng, child_female, shared_last)
        child["middle"] = shared_middle
        members.append((child, parent_dob + timedelta(days=rng.randint(25, 35) * 365), child_female))

    style_pool = ["abbrev", "plain", "expanded"]
    for parts, dob_i, female in members:
        rows.append(b.row(
            source=rng.choice(SOURCE_NAMES),
            nik=make_nik(rng, region[0], district, dob_i, female),
            name=render_name(parts), female=female, dob=dob_i,
            addr_text=render_address(addr, rng.choice(style_pool)),   # same address
            phone=household_phone if rng.random() < 0.7 else make_phone(rng),
            updated=random_recent(rng), use_case="uc4_family_false_positive",
            entity_id=b.next_entity(), group_id=group,
            variant=f"{flavour}_same_address_same_surname",
            dob_style=rng.choice(DOB_FORMATS), phone_style=rng.choice(PHONE_FORMATS)))
    return rows


def gen_uc5(b: Builder) -> list[list]:
    """UC5: same person over time — address and phone change, NIK is the anchor."""
    rng = b.rng
    female = rng.random() < 0.5
    region = rng.choice(REGIONS)
    dob = random_dob(rng)
    parts = make_name(rng, female)
    nik = make_nik(rng, region[0], make_district(rng), dob, female)
    entity, group = b.next_entity(), b.next_group()
    n = 3 if rng.random() < 0.42 else 2
    years = sorted(rng.sample([2021, 2022, 2023, 2024, 2025, 2026], n))
    married = female and rng.random() < 0.2
    rows = []

    for i, year in enumerate(years):
        addr = make_address(rng, rng.choice(REGIONS) if i else region)
        name_parts = dict(parts)
        if married and i == len(years) - 1:
            name_parts["last"] = f"{parts['last']} {rng.choice(LAST_NAMES)}"
        moved = "moved" if i else "origin"
        rows.append(b.row(
            source=rng.choice(SOURCE_NAMES), nik=nik, name=render_name(name_parts),
            female=female, dob=dob,
            addr_text=render_address(addr, rng.choice(["abbrev", "plain", "expanded"])),
            phone=make_phone(rng),                    # new number each snapshot
            updated=min(date(year, rng.randint(1, 12), rng.randint(1, 28)), LAST_SEEN),
            use_case="uc5_entity_evolution", entity_id=entity, group_id=group,
            variant=f"same_nik+{moved}+new_phone" + ("+surname_changed" if married and i == len(years) - 1 else ""),
            dob_style=rng.choice(DOB_FORMATS), phone_style=rng.choice(PHONE_FORMATS)))
    return rows


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

# Share of the *total row count* allocated to each scenario.
MIX = [
    ("uc1_fuzzy_typo_format", gen_uc1, 0.12),
    ("uc2_missing_nik", gen_uc2, 0.09),
    ("uc3_address_variation", gen_uc3, 0.08),
    ("uc4_family_false_positive", gen_uc4, 0.085),
    ("uc5_entity_evolution", gen_uc5, 0.085),
]


def generate(total_rows: int, out_path: str, subset_path: str | None,
             subset_rows: int, seed: int) -> dict:
    rng = random.Random(seed)
    b = Builder(rng)
    stats: dict[str, int] = {name: 0 for name, _, _ in MIX}
    stats["normal_data"] = 0
    entities_per_case: dict[str, set] = {k: set() for k in stats}

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".csv", prefix="er_unshuffled_")
    os.close(tmp_fd)
    subset_groups: list[list[list]] = []
    subset_count = 0
    subset_rate = subset_rows / total_rows if subset_path else 0.0
    written = 0

    with open(tmp_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        for name, fn, share in MIX:
            target = int(total_rows * share)
            while stats[name] < target:
                rows = fn(b)
                writer.writerows(rows)
                stats[name] += len(rows)
                written += len(rows)
                for r in rows:
                    entities_per_case[name].add(r[11])
                if subset_path and subset_count < subset_rows and rng.random() < subset_rate:
                    subset_groups.append(rows)
                    subset_count += len(rows)

        while written < total_rows:
            rows = gen_normal(b)
            writer.writerows(rows)
            stats["normal_data"] += len(rows)
            written += len(rows)
            entities_per_case["normal_data"].add(rows[0][11])
            if subset_path and subset_count < subset_rows and rng.random() < subset_rate:
                subset_groups.append(rows)
                subset_count += len(rows)

    print(f"Shuffling {written:,} rows...")
    with open(tmp_path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()
    rng.shuffle(lines)
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        fh.write(",".join(HEADER) + "\n")
        fh.writelines(lines)
    os.remove(tmp_path)

    if subset_path:
        rng.shuffle(subset_groups)
        with open(subset_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(HEADER)
            for rows in subset_groups:
                writer.writerows(rows)

    return {
        "rows": written,
        "stats": stats,
        "entities": {k: len(v) for k, v in entities_per_case.items()},
        "subset_rows": subset_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=1_000_000)
    parser.add_argument("--out", default="samples/er_dataset_1m.csv")
    parser.add_argument("--subset", default="samples/er_dataset_200k.csv",
                        help="ER-ready subset with every match group kept intact "
                             "(the backend truncates at er_max_rows=200_000)")
    parser.add_argument("--subset-rows", type=int, default=200_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-subset", action="store_true")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    subset = None if args.no_subset else args.subset
    subset_rows = min(args.subset_rows, args.rows)

    print(f"Generating {args.rows:,} rows -> {args.out}")
    result = generate(args.rows, args.out, subset, subset_rows, args.seed)

    print(f"\nDone. {result['rows']:,} rows written to {args.out}")
    print(f"{'use_case':<32}{'rows':>12}{'entities':>12}{'expected':>12}")
    for key in list(dict.fromkeys([n for n, _, _ in MIX] + ["normal_data"])):
        print(f"{key:<32}{result['stats'][key]:>12,}{result['entities'][key]:>12,}"
              f"{USE_CASES[key]:>12}")
    if subset:
        print(f"\nER-ready subset: {subset} ({result['subset_rows']:,} rows, "
              "all match groups intact)")
    print("\nReminder: read NIK as text -> pd.read_csv(path, dtype={'nik': str, "
          "'phone_number': str})")


if __name__ == "__main__":
    main()
