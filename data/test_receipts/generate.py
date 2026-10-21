"""Makes fictional traffic-fine receipt photos for testing the upload flow.

Layout copies a real POS receipt. Every name, number and address is made up (no black marks: the personal fields
are filled with obviously fictional values), and each receipt carries a "SAMPLE" footer. The expected outcomes come from the dataset in data/source/.
Run:  python3 generate.py     (needs Pillow)
"""
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).parent
MONO = "/System/Library/Fonts/Menlo.ttc"
BANGLA = "/System/Library/Fonts/Supplemental/Bangla Sangam MN.ttc"

# file name, offence text, amount, occurrence, last payment, seized docs, vehicle, notes, expected result
CASES = [
    ("01_valid_speeding_s87", "87. Exceeding speed limit", "5,000.00", "MAR 02, 2026", "01-Apr-26", "D/L", "Dhaka Metro-Ga 11-0001", None, "VALID: Tk 5,000 is within the Tk 10,000 limit of s.87"),
    ("02_too_high_speeding_s87", "87. Exceeding speed limit", "15,000.00", "MAR 09, 2026", "08-Apr-26", "D/L", "Dhaka Metro-Ha 11-0002", None, "INVALID_FINE_TOO_HIGH: Tk 15,000 is above the Tk 10,000 limit of s.87"),
    ("03_valid_fitness_s75", "75. b. Fitness Date Expire", "10,000.00", "FEB 16, 2025", "09-Mar-25", "D/L,F/C", "Dhaka Metro-Ta 11-0003", None, "VALID: within the Tk 25,000 limit of s.75 (same wording as the reference photo)"),
    ("04_too_high_parking_s90", "90. Illegal parking / loading", "12,000.00", "APR 11, 2026", "10-May-26", "D/L", "Chattogram Metro-Ka 11-0004", None, "INVALID_FINE_TOO_HIGH: above the Tk 5,000 limit of s.90"),
    ("05_exception_ambulance_s77", "77. Operating without route permit", "15,000.00", "MAY 03, 2026", "02-Jun-26", "R/P", "Dhaka Metro-Chha 11-0005", "Vehicle: AMBULANCE. Driver states emergency duty.", "VALID_BUT_EXCEPTION_POSSIBLE: ambulances are exempt from route permits (s.30)"),
    ("06_review_extortion_s83", "83. Prohibited extortion", "20,000.00", "MAY 20, 2026", "19-Jun-26", "D/L", "Dhaka Metro-Gha 11-0006", None, "NEEDS_MANUAL_REVIEW: s.83 has no Taka ceiling"),
    ("07_too_high_overload_s86", "86. Overloading vehicle", "150,000.00", "JUN 07, 2026", "06-Jul-26", "D/L,F/C", "Gazipur Metro-Ma 11-0007", None, "INVALID_FINE_TOO_HIGH: above the Tk 1 lakh limit of s.86"),
    ("08_valid_signal_s85_bangla", "৮৫. ট্রাফিক সংকেত অমান্য", "8,000.00", "JUN 21, 2026", "20-Jul-26", "D/L", "Dhaka Metro-Ka 11-0008", None, "VALID: within the Tk 10,000 limit of s.85 (Bangla offence text)"),
    ("09_review_below_min_workshop_s97", "97. Unlicensed repair workshop", "10,000.00", "JUL 02, 2026", "01-Aug-26", "-", "Workshop (n/a)", None, "NEEDS_MANUAL_REVIEW: below the Tk 25,000 minimum of s.97"),
    ("10_review_unknown_offence", "Throwing litter from vehicle", "3,000.00", "JUL 14, 2026", "13-Aug-26", "D/L", "Dhaka Metro-Ga 11-0010", None, "NEEDS_MANUAL_REVIEW: offence not in the dataset"),
    ("11_too_high_no_licence_s66", "66. Driving without licence", "40,000.00", "AUG 01, 2026", "31-Aug-26", "-", "Rajshahi Metro-Ha 11-0011", None, "INVALID_FINE_TOO_HIGH: above the Tk 25,000 limit of s.66"),
    ("12_valid_tax_token_s76_boundary", "76. No valid tax token", "10,000.00", "AUG 15, 2026", "14-Sep-26", "D/L", "Dhaka Metro-Ba 11-0012", None, "VALID: exactly the Tk 10,000 limit of s.76"),
    ("13_too_high_unregistered_s72", "72. Driving unregistered vehicle", "60,000.00", "AUG 22, 2026", "21-Sep-26", "D/L", "Khulna Metro-Ta 11-0013", None, "INVALID_FINE_TOO_HIGH: above the Tk 50,000 limit of s.72"),
    ("14_valid_fare_chart_s80", "80. Fare chart not displayed", "7,500.00", "AUG 29, 2026", "28-Sep-26", "D/L", "Dhaka Metro-Chha 11-0014", None, "VALID: within the Tk 10,000 limit of s.80"),
    ("15_valid_air_horn_s88_first", "88. Illegal air horn", "2,000.00", "SEP 01, 2026", "01-Oct-26", "D/L", "Sylhet Metro-Ka 11-0015", None, "VALID: first s.88 offence, within the Tk 10,000 limit. Upload this BEFORE receipt 16"),
    ("16_too_high_air_horn_s88_repeat", "88. Illegal air horn", "5,000.00", "OCT 06, 2026", "05-Nov-26", "D/L", "Sylhet Metro-Ka 11-0015", None, "INVALID_FINE_TOO_HIGH: a repeat of receipt 15 may be fined at most twice the previous fine (Tk 4,000), even though Tk 5,000 is under the Tk 10,000 limit. Upload AFTER receipt 15, same account"),
    ("17_too_high_flammable_s93", "93. Carrying flammable substances unsafely", "30,000.00", "SEP 12, 2026", "12-Oct-26", "D/L,F/C", "Narayanganj Metro-Da 11-0017", None, "INVALID_FINE_TOO_HIGH: above the Tk 25,000 limit of s.93"),
    ("18_valid_obstruct_inspection_s101_bangla", "১০১. পরিদর্শনে বাধা প্রদান", "5,000.00", "SEP 19, 2026", "19-Oct-26", "D/L", "Dhaka Metro-Ga 11-0018", None, "VALID: within the Tk 10,000 limit of s.101 (Bangla offence text)"),
    ("19_review_reckless_death_s105", "105. Reckless driving causing death", "500,000.00", "SEP 26, 2026", "26-Oct-26", "D/L,F/C", "Dhaka Metro-Ha 11-0019", None, "VALID: Tk 5 lakh is exactly the s.105 fine ceiling (the law may also impose up to 5 years in prison; only the fine is checked)"),
    ("20_exception_fire_service_s77", "77. Operating without route permit", "12,000.00", "OCT 03, 2026", "02-Nov-26", "R/P", "Dhaka Metro-Ta 11-0020", "Vehicle: FIRE SERVICE truck, responding to a call.", "VALID_BUT_EXCEPTION_POSSIBLE: fire-service vehicles are exempt from route permits (s.30)"),
]

# Made-up people, phone numbers (placeholder 01700-000xxx range) and places, one set per receipt.
NAMES = ["Karim Test Uddin", "Rahima Sample Begum", "Jamal Demo Hossain", "Nasrin Example Akter", "Sohel Mock Rana",
         "Farhana Trial Islam", "Imran Dummy Sheikh", "Shirin Sample Khatun", "Tarek Test Mia", "Mitu Demo Sultana",
         "Anwar Example Ali", "Lipi Mock Khan", "Rubel Trial Das", "Salma Sample Parvin", "Habib Demo Talukder",
         "Josna Example Roy", "Mizan Mock Chowdhury", "Poly Trial Nahar", "Liton Sample Biswas", "Ruma Test Haque"]
FATHERS = ["Abdul Test Uddin", "Kamal Sample Mia", "Nurul Demo Haque", "Shafiq Example Ali", "Mokbul Mock Sheikh"]
AREAS = ["Farmgate, Dhaka", "Mirpur 10, Dhaka", "Gulshan 2, Dhaka", "Motijheel, Dhaka", "Uttara Sector 7, Dhaka",
         "Banani, Dhaka", "Tejgaon, Dhaka", "Jatrabari, Dhaka", "Mohakhali, Dhaka", "Shahbag, Dhaka"]


def details(i):
    r = random.Random(1000 + i)
    return {
        "officer": f"DMP-TEST-{r.randint(1000, 9999)}",
        "trace": f"TR{r.randint(10**9, 10**10 - 1)}",
        "case_id": f"C-2026-{r.randint(100000, 999999)}",
        "person": NAMES[i % len(NAMES)],
        "father": FATHERS[i % len(FATHERS)],
        "cell": f"01700-000{r.randint(100, 999)}",
        "address": f"House {r.randint(1, 80)}, Road {r.randint(1, 30)}, Test Area",
        "location": AREAS[i % len(AREAS)],
    }


def font(path, size, index=0):
    return ImageFont.truetype(path, size, index=index)


def receipt(case, seed):
    p = details(seed)
    name, offence, amount, when, last, seized, vehicle, notes, _ = case
    rnd = random.Random(seed)
    W, f = 560, font(MONO, 21)
    small, big = font(MONO, 17), font(MONO, 26)
    bn = font(BANGLA, 22) if any(ord(c) > 2000 for c in offence) else None
    img = Image.new("RGB", (W, 1500), (250, 250, 247))
    d = ImageDraw.Draw(img)
    ink = (28, 28, 30)
    y = 30
    d.ellipse((W // 2 - 55, y, W // 2 + 55, y + 110), outline=ink, width=4)  # generic badge, not a real emblem
    d.regular_polygon((W // 2, y + 55, 34), 5, fill=ink)
    y += 135

    def line(text, fnt=f, x=34, dy=33):
        nonlocal y
        d.text((x, y), text, font=fnt, fill=ink)
        y += dy

    line("DHAKA METROPOLITAN POLICE POS", f)
    line(f"Officer ID Number: {p['officer']}", small)
    line("Div: Sample Zone, 00 Test Road", small)
    line("SAMPLE, DHAKA-1000", small)
    line("The Road Transport Act 2018", small, dy=40)
    line(f"Trace No.: {p['trace']}", small)
    line(f"Case ID: {p['case_id']}", small)
    line("Accused Person:", small, dy=26)
    line(p["person"])
    line("Father/ Spouse:", small, dy=26)
    line(p["father"])
    line(f"Cell Number: {p['cell']}", small, dy=34)
    line("Address of Owner / Driver:", small, dy=26)
    line(p["address"], small, dy=34)
    line("Vehicle Reg. No:", small, dy=26)
    line(vehicle)
    line("Offence/Offences:", small, dy=26)
    if bn:
        d.text((34, y - 2), offence, font=bn, fill=ink)
        y += 38
    else:
        line(offence)
    line("Location:", small, dy=26)
    line(p["location"])
    line("Seized Docs:" + seized, small)
    line("Occurrence Date & Time:", small, dy=26)
    line(when)
    line("Last Date of Payment:", small, dy=26)
    line(last)
    line("Witness:video")
    if notes:
        line("Remarks:", small, dy=26)
        for part in notes.replace(". ", ".\n").split("\n"):
            line(part, small, dy=26)
        y += 6
    y += 14
    line("Total Fine Amount TK:", small, dy=34)
    d.text((W - 34, y), amount, font=big, fill=ink, anchor="ra")
    y += 70
    d.line((34, y, W - 34, y), fill=ink, width=1)
    line("SIGN X", small, dy=24)
    line("Signature of the Receiving", small, dy=22)
    line("Officer / Complainant", small, dy=40)
    line("PLEASE MAKE A PHOTOCOPY OF THE RECEIPT", small, dy=22)
    line("AS PRINT MAY DISAPPEAR AFTER 4 WEEKS", small, dy=34)
    line("SAMPLE - NOT A REAL RECEIPT", small, dy=24)
    return img.crop((0, 0, W, y + 30))


def photo(strip, seed):
    rnd = random.Random(seed)
    W, H = 1000, 1400
    bg = Image.new("RGB", (W, H), (118, 116, 112))
    px = bg.load()
    for _ in range(90000):  # concrete speckle
        x, yy = rnd.randrange(W), rnd.randrange(H)
        v = rnd.randint(-28, 28)
        r, g, b = px[x, yy]
        px[x, yy] = (max(0, min(255, r + v)), max(0, min(255, g + v)), max(0, min(255, b + v)))
    bg = bg.filter(ImageFilter.GaussianBlur(1.2))
    scale = 1150 / strip.height
    s = strip.resize((int(strip.width * scale), int(strip.height * scale)), Image.LANCZOS)
    s = s.convert("RGBA").rotate(rnd.uniform(-4, 4), expand=True, resample=Image.BICUBIC)  # corners stay transparent
    shadow = Image.new("RGBA", (s.width + 80, s.height + 80), (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 120), (46, 56), s.getchannel("A"))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    ox, oy = (W - s.width) // 2 + rnd.randint(-30, 30), (H - s.height) // 2
    bg.paste(shadow, (ox - 40, oy - 40), shadow)
    bg.paste(s, (ox, oy), s)
    return bg.filter(ImageFilter.GaussianBlur(0.6))


if __name__ == "__main__":
    lines = ["Test receipts (all fictional, no black marks). Expected result for each, from the dataset in data/source/.\nUpload each from the same account; receipts 15 and 16 are a repeat-offence pair (15 first).\n"]
    for i, case in enumerate(CASES):
        photo(receipt(case, i), i).save(OUT / f"{case[0]}.jpg", quality=88)
        lines.append(f"{case[0]}.jpg\n    -> {case[-1]}")
    (OUT / "EXPECTED_RESULTS.txt").write_text("\n".join(lines) + "\n")
    print("made", len(CASES), "receipts")
