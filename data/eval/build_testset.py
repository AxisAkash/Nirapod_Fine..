"""Builds the labelled test set used to evaluate Nirapod Fine (for the paper).

Run:  python3 build_testset.py            (needs Pillow and Google Chrome; images are optional: --no-images)

Writes, next to this file:
  cases.csv            every case, with the correct section and verdict
  receipts/*.jpg       a stratified subset rendered as receipt pictures (clean / photo / blurry / dim, English / Bangla)
  receipts/manifest.json   the correct fields for each picture (same format scripts/eval_extraction.py reads)

WHERE THE CORRECT ANSWERS COME FROM
The correct section and verdict of each case are NOT produced by the engine. They are written here from the figures in
data/source/Bangladesh_Road_Transport_Act_2018_Traffic_Fines.pdf (the maximum fine of each section, typed in LIMITS below)
and from data/source/Bangladesh_Traffic_Law_Exceptions_and_Exemptions.pdf (which exceptions exist and what they do not
cover). The offence wordings were written independently of the engine's alias lists, so wordings the engine has never
seen are included on purpose ("paraphrase" and "bangla" groups). Every fine, name, number and place is invented.

The labels were written by the author of this repository's tooling, not by a legal expert. For a paper, have a person
who knows the Act check cases.csv (and add real receipts) before reporting results.
"""

from __future__ import annotations

import csv
import html
import json
import random
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

def _arg(name: str, default: str) -> str:
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


HERE = Path(_arg("--out", str(Path(__file__).resolve().parent)))  # --out DIR writes the set somewhere else (a held-out set)
HERE.mkdir(parents=True, exist_ok=True)
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
RNG = random.Random(int(_arg("--seed", "20261023")))  # --seed N makes a different set with the same recipe

# section: (maximum fine in Tk from the fines PDF, canonical wording, paraphrase, Bangla wording)
LIMITS: dict[str, tuple[int, str, str, str]] = {
    "66": (25_000, "Driving without a driving licence", "No valid licence while driving", "ড্রাইভিং লাইসেন্স ছাড়া গাড়ি চালানো"),
    "67": (5_000, "Unlawful transfer of a driving licence", "Lent his driving licence to another person", "অবৈধভাবে ড্রাইভিং লাইসেন্স হস্তান্তর"),
    "70": (25_000, "Driving despite licence suspension", "Driving while the licence was cancelled", "লাইসেন্স বাতিল থাকা অবস্থায় গাড়ি চালানো"),
    "71": (5_000, "Working as a conductor without a licence", "Bus conductor with no conductor licence", "লাইসেন্স ছাড়া কন্ডাক্টরের কাজ"),
    "72": (50_000, "Driving an unregistered vehicle", "Vehicle has no registration", "নিবন্ধন ছাড়া গাড়ি চালানো"),
    "74": (5_000, "Failure to register after ownership transfer", "Ownership changed but registration not updated", "মালিকানা পরিবর্তনের পর নিবন্ধন না করা"),
    "75": (25_000, "Driving without a valid fitness certificate", "Fitness Date Expire", "ফিটনেস সনদ ছাড়া গাড়ি চালানো"),
    "76": (10_000, "Driving without a valid tax token", "Tax token expired", "ট্যাক্স টোকেন ছাড়া গাড়ি চালানো"),
    "77": (20_000, "Operating without a route permit", "No route permit for this transport vehicle", "রুট পারমিট ছাড়া গাড়ি চালানো"),
    "79": (25_000, "Violating restrictions on commercial use of a vehicle", "Private car used for commercial purpose", "ব্যক্তিগত গাড়ি বাণিজ্যিক কাজে ব্যবহার"),
    "80": (10_000, "Failing to display the fare chart", "Charging more than the fixed fare", "ভাড়ার তালিকা প্রদর্শন না করা"),
    "81": (50_000, "Tampering with a taxi meter or overcharging passengers", "Overcharged passengers with a tampered meter", "মিটারে কারসাজি করে অতিরিক্ত ভাড়া আদায়"),
    "84": (300_000, "Violating technical specifications of a motor vehicle", "Vehicle modified against its technical specification", "যানবাহনের কারিগরি বৈশিষ্ট্য লঙ্ঘন"),
    "85": (10_000, "Violating traffic signals", "Jumped the red light", "ট্রাফিক সংকেত অমান্য"),
    "86": (100_000, "Overloading a vehicle", "Carrying more weight than permitted", "অতিরিক্ত মালামাল বহন"),
    "87": (10_000, "Exceeding the speed limit", "Driving too fast", "অতিরিক্ত গতিতে গাড়ি চালানো"),
    "88": (10_000, "Illegal use of horn", "Blowing a loud horn in a silent zone", "নিষিদ্ধ হর্ন ব্যবহার"),
    "90": (5_000, "Illegal parking", "Parked in a no parking zone", "নিষিদ্ধ স্থানে গাড়ি পার্কিং"),
    "91": (5_000, "Violating highway rules for fast-moving vehicles", "Slow vehicle in the fast lane of the highway", "মহাসড়কে দ্রুতগামী যানের নিয়ম লঙ্ঘন"),
    "93": (25_000, "Transporting flammable substances improperly", "Carrying explosives inside a passenger bus", "দাহ্য পদার্থ অনিরাপদে পরিবহন"),
    "95": (20_000, "Failure to give treatment to an accident victim", "Did not take the injured person to hospital", "দুর্ঘটনায় আহতকে চিকিৎসা না দেওয়া"),
    "96": (100_000, "Running a driving training school unlawfully", "Unlicensed driving school", "অনুমোদন ছাড়া ড্রাইভিং স্কুল পরিচালনা"),
    "101": (10_000, "Obstructing an inspection", "Refused to let the officer inspect the vehicle", "পরিদর্শনে বাধা প্রদান"),
    "102": (10_000, "Failure to obey an order or give required information", "Did not give the information the officer asked for", "আদেশ অমান্য বা তথ্য না দেওয়া"),
    "103": (10_000, "Aggressive behaviour against public order", "Rude and aggressive conduct on the road", "জনশৃঙ্খলা বিরোধী আক্রমণাত্মক আচরণ"),
    "104": (20_000, "Violating government orders on transport", "Ignored a government directive on vehicles", "সরকারি আদেশ লঙ্ঘন"),
    "105": (500_000, "Reckless driving causing death", "Negligent driving, a pedestrian died", "বেপরোয়া গাড়ি চালিয়ে মৃত্যু ঘটানো"),
}

# Offences that are not in the fines guide at all: the correct outcome is manual review, with no section.
UNKNOWN = [
    "Throwing litter from a vehicle window", "Jaywalking by a pedestrian", "Not wearing a helmet", "Smoking inside a bus",
    "Playing loud music at home", "Selling fruit on the footpath", "Late return of a library book", "Expired passport",
    "Cutting a roadside tree", "Using a mobile phone while walking", "গাড়ির জানালা দিয়ে ময়লা ফেলা", "রাস্তায় থুথু ফেলা",
]

VEHICLES = ["Motorcycle", "Car", "Bus", "Truck", "CNG auto-rickshaw", "Microbus", "Pickup", "Rickshaw van"]
PLACES = ["Farmgate, Dhaka", "Mirpur, Dhaka", "Gulshan, Dhaka", "Motijheel, Dhaka", "Uttara, Dhaka", "Dhanmondi, Dhaka",
          "Chattogram", "Sylhet", "Rajshahi", "Khulna", "Gazipur", "Narayanganj"]

STATUS = {
    "VALID": "VALID", "HIGH": "INVALID_FINE_TOO_HIGH", "EXC": "VALID_BUT_EXCEPTION_POSSIBLE",
    "NOEXC": "INVALID_EXCEPTION_NOT_APPLICABLE", "MISMATCH": "INVALID_REASON_MISMATCH", "REVIEW": "NEEDS_MANUAL_REVIEW",
}

cases: list[dict] = []


def add(group: str, reason: str, amount: int | None, truth_section: str, truth_verdict: str, *, cited: str = "", notes: str = "",
        vehicle: str | None = None, lang: str = "en") -> None:
    cases.append(dict(
        id=f"C{len(cases) + 1:03d}", group=group, lang=lang, reason=reason, amount="" if amount is None else amount,
        section_cited=cited, vehicle=vehicle or RNG.choice(VEHICLES), notes=notes,
        true_section=truth_section, true_verdict=truth_verdict,
        location=RNG.choice(PLACES), date=(date(2026, 1, 1) + timedelta(days=RNG.randrange(280))).isoformat(),
        receipt_number=f"DMP-{RNG.randrange(1000, 9999)}",
    ))


def within(m: int) -> int:
    return max(500, int(m * RNG.uniform(0.3, 0.9) / 500) * 500)


def over(m: int) -> int:
    return int(m * RNG.uniform(1.2, 2.0) / 1000 + 1) * 1000


def cite(section: str) -> str:
    return section if RNG.random() < 0.5 else ""


for sec, (mx, canonical, paraphrase, bangla) in LIMITS.items():
    add("standard", canonical, within(mx), sec, STATUS["VALID"], cited=cite(sec))
    add("standard", canonical, over(mx), sec, STATUS["HIGH"], cited=cite(sec))
    add("boundary", canonical, mx, sec, STATUS["VALID"], cited=cite(sec))
    add("paraphrase", paraphrase, within(mx), sec, STATUS["VALID"], cited=cite(sec))
    add("paraphrase", paraphrase, over(mx), sec, STATUS["HIGH"], cited=cite(sec))
    add("bangla", bangla, within(mx), sec, STATUS["VALID"], cited=cite(sec), lang="bn")
    if RNG.random() < 0.5:
        add("bangla", bangla, over(mx), sec, STATUS["HIGH"], cited=cite(sec), lang="bn")

for text in UNKNOWN:
    add("unknown", text, RNG.choice([500, 1000, 2000, 3000, 5000]), "none", STATUS["REVIEW"], lang="bn" if ord(text[0]) > 2000 else "en")

for sec, amount in [("87", None), ("90", None), ("85", None), ("76", None)]:
    add("no_amount", LIMITS[sec][1], amount, sec, STATUS["REVIEW"])

for amount in (20_000, 50_000, 120_000, 5_000):  # section 83 has no Taka ceiling in the source
    add("no_ceiling", "Prohibited extortion related to transport", amount, "83", STATUS["REVIEW"], cited=cite("83"))

# section 97 (repair workshop) has a minimum of Tk 25,000 and a maximum of Tk 1 lakh
for amount in (5_000, 10_000, 20_000):
    add("below_minimum", "Operating a vehicle repair workshop unlawfully", amount, "97", STATUS["REVIEW"])
add("boundary", "Operating a vehicle repair workshop unlawfully", 30_000, "97", STATUS["VALID"])
add("boundary", "Operating a vehicle repair workshop unlawfully", 120_000, "97", STATUS["HIGH"])

# the receipt cites one section but the offence written on it belongs to another
for reason_sec, cited_sec in [("87", "90"), ("90", "85"), ("85", "87"), ("76", "75"), ("75", "76"), ("86", "87"),
                              ("88", "85"), ("101", "102"), ("80", "81"), ("66", "70")]:
    add("mismatch", LIMITS[reason_sec][1], within(LIMITS[reason_sec][0]), reason_sec, STATUS["MISMATCH"], cited=cited_sec)

# exceptions. The exceptions guide: route-permit exemptions exist for ambulance, fire service, government and
# calamity cases (s.30); it says no general exemption was found for speeding, red lights or parking in an emergency.
for notes, vehicle in [
    ("Ambulance on emergency duty, carrying a patient", "Ambulance"), ("Fire service truck responding to a fire", "Fire service truck"),
    ("Government-owned vehicle carrying relief goods", "Truck"), ("Bus took a different route because the road was flooded", "Bus"),
    ("Vehicle belongs to a recognised driving training centre", "Microbus"), ("Mobile library van", "Van"),
]:
    add("exception", "Operating without a route permit", 15_000, "77", STATUS["EXC"], notes=notes, vehicle=vehicle)
for reason, sec, notes in [
    ("Exceeding the speed limit", "87", "Ambulance rushing a patient, driver claims emergency"),
    ("Exceeding the speed limit", "87", "Driver says it was an emergency"),
    ("Violating traffic signals", "85", "Part of a VIP convoy"),
    ("Violating traffic signals", "85", "Police escort, driver claims exemption"),
    ("Illegal parking", "90", "Stopped for an emergency"),
    ("Illegal parking", "90", "Doctor on call, claims exemption"),
]:
    add("exception_rejected", reason, within(LIMITS[sec][0]), sec, STATUS["NOEXC"], notes=notes)


# ---------------------------------------------------------------------------------------------------------- pictures
BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


def receipt_page(c: dict) -> str:
    bn = c["lang"] == "bn"
    d = lambda s: str(s).translate(BN_DIGITS) if bn else str(s)  # noqa: E731
    day = date.fromisoformat(c["date"])
    labels = (dict(title="ট্রাফিক মামলা রশিদ", no="রশিদ নং", date="তারিখ", place="স্থান", vehicle="যানবাহন", offence="অপরাধ", fine="জরিমানা", notes="মন্তব্য", tk="টাকা")
              if bn else dict(title="Traffic Case Receipt", no="Receipt no.", date="Date", place="Location", vehicle="Vehicle", offence="Offence", fine="Total Fine (Tk)", notes="Remarks", tk=""))
    offence = f"{d(c['section_cited'])}. {c['reason']}" if c["section_cited"] else c["reason"]
    rows = [(labels["no"], c["receipt_number"]), (labels["date"], d(day.strftime("%d/%m/%Y"))), (labels["place"], c["location"]), (labels["vehicle"], c["vehicle"])]
    if c["notes"]:
        rows.append((labels["notes"], c["notes"]))
    body = "".join(f"<div class=ln><span>{html.escape(k)}</span><b>{html.escape(v)}</b></div>" for k, v in rows)
    fine = f"{int(c['amount']):,}" if c["amount"] != "" else "&mdash;"
    return f"""<!doctype html><meta charset=utf8><style>
body{{margin:0;background:#dcd8cc;font-family:'Noto Sans Bengali','Bangla Sangam MN','Menlo',monospace}}
.paper{{width:500px;margin:26px;padding:26px 30px;background:#fffefa;color:#1c1c1e;font-size:18px;line-height:1.5}}
h1{{font-size:21px;text-align:center;margin:0 0 2px}} .sub{{text-align:center;font-size:13px;color:#666;margin-bottom:14px}}
.ln{{display:flex;justify-content:space-between;gap:16px}} .ln span{{color:#555}} .ln b{{text-align:right;font-weight:600}}
hr{{border:0;border-top:1px dashed #999;margin:10px 0}} .fine{{font-size:23px}}</style>
<div class=paper><h1>{labels['title']}</h1><div class=sub>{'মেট্রোপলিটন ট্রাফিক ম্যাজিস্ট্রেট' if bn else 'Metropolitan Traffic Magistrate, mobile court'}</div>{body}<hr>
<div class=ln><span>{labels['offence']}</span><b>{html.escape(offence)}</b></div><hr>
<div class='ln fine'><span>{labels['fine']}</span><b>{d(fine) if c['amount'] != '' else fine} {labels['tk']}</b></div></div>"""


def degrade(img, style: str, seed: str):
    from PIL import Image, ImageFilter, ImageOps

    rnd = random.Random(seed)
    if style == "clean":
        return img
    if style == "photo":  # a phone photo: slight rotation, shading, noise
        img = img.rotate(rnd.uniform(-5, 5), expand=True, fillcolor=(120, 110, 95))
        shade = Image.linear_gradient("L").resize(img.size).point(lambda v: 150 + v // 3)
        img = Image.composite(img, Image.new("RGB", img.size, (60, 55, 50)), shade)
        noise = Image.effect_noise(img.size, 18).convert("RGB")
        return ImageOps.autocontrast(Image.blend(img, noise, 0.08).filter(ImageFilter.GaussianBlur(0.8)), cutoff=1)
    if style == "blurry":
        return img.resize((img.width // 4, img.height // 4)).filter(ImageFilter.GaussianBlur(1.8)).resize(img.size)
    # dim: a dark, low-contrast photo
    img = img.rotate(rnd.uniform(-3, 3), expand=True, fillcolor=(70, 66, 60))
    return ImageOps.autocontrast(img.point(lambda v: int(v * 0.45)), cutoff=0).filter(ImageFilter.GaussianBlur(0.9))


def render_pictures(subset: list[dict]) -> list[dict]:
    from PIL import Image

    out = HERE / "receipts"
    out.mkdir(exist_ok=True)
    manifest = []
    styles = ["clean", "photo", "blurry", "dim"]
    with tempfile.TemporaryDirectory() as t:
        for i, c in enumerate(subset):
            style = styles[i % len(styles)]
            page = Path(t) / f"{c['id']}.html"
            page.write_text(receipt_page(c), encoding="utf8")
            png = Path(t) / f"{c['id']}.png"
            subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=600,520", f"--screenshot={png}", f"file://{page}"],
                           check=True, capture_output=True, timeout=60)
            img = degrade(Image.open(png).convert("RGB"), style, c["id"])
            name = f"{c['id']}_{style}_{c['lang']}.jpg"
            img.save(out / name, quality=84)
            manifest.append(dict(
                file=name, case_id=c["id"], kind=style, lang=c["lang"],
                expect=dict(reason=c["reason"], amount=int(c["amount"]) if c["amount"] != "" else None, section=c["section_cited"] or None,
                            vehicle=c["vehicle"], location=c["location"], date=c["date"], receipt_number=c["receipt_number"], notes=c["notes"] or None),
            ))
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf8")
    return manifest


def pick_for_pictures() -> list[dict]:
    """About 56 cases spread over every group, kept in a fixed order so quality and language rotate evenly."""
    chosen: list[dict] = []
    for group, n in [("standard", 14), ("paraphrase", 10), ("bangla", 12), ("boundary", 4), ("exception", 6), ("exception_rejected", 3),
                     ("mismatch", 4), ("unknown", 3)]:
        pool = [c for c in cases if c["group"] == group]
        chosen += RNG.sample(pool, min(n, len(pool)))
    return chosen


def main() -> None:
    with (HERE / "cases.csv").open("w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=list(cases[0]))
        w.writeheader()
        w.writerows(cases)
    by_group: dict[str, int] = {}
    for c in cases:
        by_group[c["group"]] = by_group.get(c["group"], 0) + 1
    print(f"wrote {len(cases)} cases to cases.csv:", ", ".join(f"{g} {n}" for g, n in by_group.items()))
    if "--no-images" not in sys.argv:
        manifest = render_pictures(pick_for_pictures())
        print(f"rendered {len(manifest)} receipt pictures to receipts/")


if __name__ == "__main__":
    main()
