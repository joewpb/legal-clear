#!/usr/bin/env python3
"""
Legal Clear — Full Auto-Fill Pipeline
Downloads forms, extracts fields, interviews users, fills PDFs.

Usage:
    python3 auto_fill.py divorce-with-children
    python3 auto_fill.py child-custody-timesharing
    python3 auto_fill.py domestic-violence-injunction
    python3 auto_fill.py name-change-adult
    python3 auto_fill.py --list
"""

import subprocess, json, sys, re, tempfile
from pathlib import Path
from datetime import datetime
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parent.parent
FORMS_DIR = REPO_ROOT / "raw" / "forms"
CATALOG_PATH = FORMS_DIR / "full_catalog.json"

# Load catalog
with open(CATALOG_PATH) as f:
    catalog = json.load(f)

# ── Case → Forms Mapping ──────────────────────────────────────
CASE_FORM_MAP = {
    "divorce-with-children": {
        "forms": ["12.901(b)(1)", "12.902(d)", "12.902(e)", "12.995(a)", "12.932"],
        "alternates": {"12.902(b)": "income_under_50k", "12.902(c)": "income_over_50k"},
        "optional": ["12.902(f)(1)", "12.990(b)(1)"],
        "filing_fee": "$408.00",
        "court": "Circuit Court (Family Division)",
    },
    "divorce-without-children": {
        "forms": ["12.901(b)(2)"],
        "alternates": {"12.902(b)": "income_under_50k", "12.902(c)": "income_over_50k"},
        "optional": ["12.901(a)", "12.902(f)(2)", "12.990(a)"],
        "filing_fee": "$408.00",
        "court": "Circuit Court (Family Division)",
    },
    "child-custody-timesharing": {
        "forms": ["12.983(a)", "12.902(d)", "12.902(e)", "12.995(a)"],
        "alternates": {"12.902(b)": "income_under_50k", "12.902(c)": "income_over_50k"},
        "filing_fee": "$300.00",
        "court": "Circuit Court (Family Division)",
    },
    "child-support-modification": {
        "forms": ["12.905", "12.902(e)"],
        "alternates": {"12.902(b)": "income_under_50k", "12.902(c)": "income_over_50k"},
        "filing_fee": "Varies ($0–$300 depending on method)",
        "court": "Circuit Court or DOR Administrative",
    },
    "domestic-violence-injunction": {
        "forms": [],  # County-specific DV forms, not in catalog
        "filing_fee": "$0 (no fee for protection injunctions)",
        "court": "Circuit Court",
        "county_specific": True,
        "note": "DIY Florida covers this. Go to myflcourtaccess.com DIY tab. Or visit your local courthouse — clerks have these forms at the counter. No filing fee.",
    },
    "eviction-landlord": {
        "forms": [],
        "filing_fee": "$185–$300 (varies by county)",
        "court": "County Court",
        "county_specific": True,
        "note": "DIY Florida handles this. Go to myflcourtaccess.com → DIY tab → Landlord Tenant. It auto-fills and e-files.",
    },
    "eviction-tenant": {
        "forms": [],
        "filing_fee": "$0 to file answer (deposit may be required)",
        "court": "County Court",
        "county_specific": True,
        "note": "You have only 5 BUSINESS DAYS to respond. Contact your local legal aid office immediately. DIY Florida may have defense forms.",
    },
    "small-claims": {
        "forms": ["7.340"],  # Summons/notice is standard
        "filing_fee": "$55–$300 (varies by amount and county)",
        "court": "County Court",
        "county_specific": True,
        "note": "DIY Florida handles this. Go to myflcourtaccess.com → DIY tab → Small Claims.",
    },
    "name-change-adult": {
        "forms": ["12.982(a)"],
        "optional": ["12.982(d)"],
        "filing_fee": "$414.00",
        "court": "Circuit Court",
        "note": "Requires fingerprinting and background check BEFORE filing. Contact your county clerk for local name change packet.",
    },
    "probate-small-estate": {
        "forms": [],
        "filing_fee": "$232–$345 (varies by county)",
        "court": "Circuit Court (Probate Division)",
        "county_specific": True,
        "note": "For estates under $75,000. Visit your county clerk's probate division for the county-specific small estate packet. DIY Florida does NOT cover this.",
    },
    "probate-full": {
        "forms": [],
        "filing_fee": "$400.00",
        "court": "Circuit Court (Probate Division)",
        "county_specific": True,
        "note": "Formal probate is complex. An attorney is STRONGLY recommended. Visit your county clerk for county-specific forms.",
    },
    "guardianship": {
        "forms": [],
        "filing_fee": "$400.00",
        "court": "Circuit Court (Probate/Guardianship Division)",
        "county_specific": True,
        "note": "Requires background check, credit check, and guardianship education. Attorney strongly recommended. Visit your county clerk for forms.",
    },
    "expungement-sealing": {
        "forms": [],
        "filing_fee": "$42.00 sealing + $75.00 FDLE fee",
        "court": "Circuit or County Court (where case was filed)",
        "county_specific": True,
        "note": "STEP 1: Apply for FDLE Certificate of Eligibility first (2-4 months). You cannot file without it. Go to fdle.state.fl.us for the application.",
    },
}

# Form file patterns for fill_forms()
CASE_FORM_PATTERNS = {
    "divorce-with-children": ["12.901(b)(1)", "12.902", "12.902(d)", "12.902(e)", "12.995", "12.932", "12.990(b)(1)"],
    "divorce-without-children": ["12.901(b)(2)", "12.902", "12.990(a)", "12.901(a)"],
    "child-custody-timesharing": ["12.983", "12.902", "12.902(d)", "12.902(e)", "12.995"],
    "child-support-modification": ["12.905", "12.902", "12.902(e)"],
    "name-change-adult": ["12.982"],
    "small-claims": ["7.340", "7.343"],
}


# ── Interview Functions ───────────────────────────────────────

def _basic_party_info(case_type: str) -> dict:
    """Collect info about both parties — shared across most case types."""
    d = {}
    print("── ABOUT YOU (the person filing) ──")
    d["petitioner_full_name"] = input("  Your full legal name: ").strip()
    d["petitioner_address"] = input("  Your street address: ").strip()
    d["petitioner_city"] = input("  City: ").strip()
    d["petitioner_state"] = input("  State [FL]: ").strip() or "FL"
    d["petitioner_zip"] = input("  ZIP: ").strip()
    d["petitioner_phone"] = input("  Phone: ").strip()
    d["petitioner_email"] = input("  Email: ").strip()
    d["petitioner_dob"] = input("  Date of birth (MM/DD/YYYY): ").strip()
    d["petitioner_dl"] = input("  Driver's license #: ").strip()

    if case_type in ("divorce-with-children", "divorce-without-children"):
        d["petitioner_is"] = input("  Are you the [W]ife or [H]usband? ").strip().upper()
        preg = input("  Are you pregnant? [y/N]: ").strip().lower()
        d["petitioner_pregnant"] = (preg == "y")
        if preg == "y":
            d["petitioner_due_date"] = input("  Due date: ").strip()

    print()
    print("── ABOUT THE OTHER PARTY ──")
    d["respondent_full_name"] = input("  Other party's full legal name: ").strip()
    d["respondent_address"] = input("  Their street address: ").strip()
    d["respondent_city"] = input("  City: ").strip()
    d["respondent_state"] = input("  State [FL]: ").strip() or "FL"
    d["respondent_zip"] = input("  ZIP: ").strip()
    d["respondent_phone"] = input("  Phone (if known): ").strip()
    d["respondent_dob"] = input("  Date of birth (if known): ").strip()

    if case_type in ("divorce-with-children", "divorce-without-children"):
        d["respondent_is"] = "H" if d.get("petitioner_is") == "W" else "W"
        preg = input("  Is the other party pregnant? [y/N]: ").strip().lower()
        d["respondent_pregnant"] = (preg == "y")

    return d


def _marriage_info() -> dict:
    """Collect marriage details for divorce cases."""
    d = {}
    print()
    print("── ABOUT THE MARRIAGE ──")
    d["marriage_date"] = input("  Date of marriage (MM/DD/YYYY): ").strip()
    d["marriage_city"] = input("  City of marriage: ").strip()
    d["marriage_county"] = input("  County of marriage: ").strip()
    d["marriage_state"] = input("  State of marriage: ").strip()
    d["separation_date"] = input("  Date separated (MM/DD/YYYY): ").strip()
    d["jurisdiction"] = input("  Do you live in the county you're filing? [Y/n]: ").strip().lower()
    return d


def _children_info() -> dict:
    """Collect child information."""
    d = {"children": []}
    print()
    print("── ABOUT THE CHILDREN ──")
    num = input("  Number of minor children together: ").strip()
    try:
        num = int(num)
    except ValueError:
        num = 0
    for i in range(num):
        print(f"\n  Child {i+1}:")
        name = input("    Full name: ").strip()
        dob = input("    Date of birth (MM/DD/YYYY): ").strip()
        age = input("    Age: ").strip()
        sex = input("    Sex [M/F]: ").strip().upper()
        d["children"].append({"name": name, "dob": dob, "age": age, "sex": sex})
    return d


def _financial_info() -> dict:
    """Collect financial data."""
    d = {}
    print()
    print("── FINANCES ──")
    d["petitioner_income"] = input("  Your gross annual income: $").strip()
    d["respondent_income"] = input("  Their gross annual income: $").strip()
    d["income_under_50k"] = input("  Is your income under $50K/year? [Y/n]: ").strip().lower() != "n"
    print("  Monthly expenses (approximate):")
    d["expense_housing"] = input("    Housing (rent/mortgage): $").strip()
    d["expense_utilities"] = input("    Utilities: $").strip()
    d["expense_food"] = input("    Food: $").strip()
    d["expense_medical"] = input("    Medical/dental: $").strip()
    d["expense_transportation"] = input("    Transportation: $").strip()
    d["expense_childcare"] = input("    Childcare: $").strip()
    d["expense_insurance"] = input("    Health insurance (your portion): $").strip()
    d["assets_home"] = input("  Home value (if you own): $").strip()
    d["assets_vehicles"] = input("  Vehicle(s) value: $").strip()
    d["assets_bank"] = input("  Bank accounts total: $").strip()
    d["assets_retirement"] = input("  Retirement accounts: $").strip()
    d["debts_mortgage"] = input("  Mortgage balance: $").strip()
    d["debts_credit"] = input("  Credit card debt: $").strip()
    d["debts_loans"] = input("  Other loans: $").strip()
    return d


def _parenting_plan() -> dict:
    """Collect parenting plan details."""
    d = {}
    print()
    print("── PARENTING PLAN ──")
    d["primary_residence"] = input("  Primary residence: [P]etitioner / [R]espondent / [B]oth equally: ").strip().upper()
    d["weekend_schedule"] = input("  Weekend schedule (describe): ").strip()
    d["weekday_schedule"] = input("  Weekday schedule (describe): ").strip()
    d["holiday_schedule"] = input("  Holiday schedule (describe): ").strip()
    d["summer_schedule"] = input("  Summer schedule (describe): ").strip()
    d["pickup_location"] = input("  Exchange/pickup location: ").strip()
    return d


def interview_divorce_with_children() -> dict:
    d: dict = defaultdict(str)
    d["_case_type"] = "divorce-with-children"
    d["_date"] = datetime.now().strftime("%Y-%m-%d")
    _print_header("DIVORCE WITH CHILDREN")
    d.update(_basic_party_info("divorce-with-children"))
    d.update(_marriage_info())
    d.update(_children_info())
    d.update(_financial_info())
    d.update(_parenting_plan())
    return dict(d)


def interview_divorce_without_children() -> dict:
    d: dict = defaultdict(str)
    d["_case_type"] = "divorce-without-children"
    d["_date"] = datetime.now().strftime("%Y-%m-%d")
    _print_header("DIVORCE WITHOUT CHILDREN")
    d.update(_basic_party_info("divorce-without-children"))
    d.update(_marriage_info())
    d.update(_financial_info())
    return dict(d)


def interview_custody() -> dict:
    d: dict = defaultdict(str)
    d["_case_type"] = "child-custody-timesharing"
    d["_date"] = datetime.now().strftime("%Y-%m-%d")
    _print_header("CHILD CUSTODY / TIME-SHARING")
    d.update(_basic_party_info("child-custody-timesharing"))
    d.update(_children_info())
    d.update(_financial_info())
    d.update(_parenting_plan())
    return dict(d)


def interview_support_mod() -> dict:
    d: dict = defaultdict(str)
    d["_case_type"] = "child-support-modification"
    d["_date"] = datetime.now().strftime("%Y-%m-%d")
    _print_header("CHILD SUPPORT MODIFICATION")
    d["petitioner_full_name"] = input("  Your full legal name: ").strip()
    d["respondent_full_name"] = input("  Other parent's full legal name: ").strip()
    d["change_reason"] = input("  What changed? (job loss, income change, child's needs): ").strip()
    d.update(_financial_info())
    return dict(d)


def interview_dv() -> dict:
    d: dict = defaultdict(str)
    d["_case_type"] = "domestic-violence-injunction"
    d["_date"] = datetime.now().strftime("%Y-%m-%d")
    _print_header("DOMESTIC VIOLENCE INJUNCTION")
    print("NOTE: Filing fee is $0 for protection injunctions.")
    print()
    d["petitioner_full_name"] = input("  Your full legal name: ").strip()
    d["respondent_full_name"] = input("  Abuser's full legal name: ").strip()
    d["relationship"] = input("  Relationship [family/dating/cohabitant]: ").strip()
    d["most_recent_incident"] = input("  Date of most recent incident: ").strip()
    d["describe_threat"] = input("  Describe the violence or threat (brief): ").strip()
    d["weapons_involved"] = input("  Were weapons involved? [y/N]: ").strip().lower() == "y"
    hide = input("  Keep your address confidential? [Y/n]: ").strip().lower()
    d["hide_address"] = (hide != "n")
    print()
    case = CASE_FORM_MAP["domestic-violence-injunction"]
    _print_county_resource(case)
    return dict(d)


def interview_name_change() -> dict:
    d: dict = defaultdict(str)
    d["_case_type"] = "name-change-adult"
    d["_date"] = datetime.now().strftime("%Y-%m-%d")
    _print_header("ADULT NAME CHANGE")
    _basic_party_info("name-change-adult")
    print()
    print("── NAME CHANGE ──")
    d["new_first"] = input("  New first name: ").strip()
    d["new_middle"] = input("  New middle name: ").strip()
    d["new_last"] = input("  New last name: ").strip()
    d["reason"] = input("  Reason for name change: ").strip()
    print()
    print("⚠️  You MUST get fingerprinted before filing.")
    print("    Contact your county clerk for the local name change packet.")
    print("    Filing fee: $414.00")
    return dict(d)


def interview_county_only(case_type: str) -> dict:
    """Informational interview for county-specific cases."""
    d: dict = defaultdict(str)
    d["_case_type"] = case_type
    d["_date"] = datetime.now().strftime("%Y-%m-%d")
    _print_header(case_type.replace("-", " ").upper())
    
    case = CASE_FORM_MAP.get(case_type, {})
    print(f"Court: {case.get('court', 'Unknown')}")
    print(f"Filing Fee: {case.get('filing_fee', 'Unknown')}")
    print()
    print(f"📋 {case.get('note', '')}")
    print()
    d["county"] = input("  What county are you in? ").strip()
    d["petitioner_full_name"] = input("  Your full legal name: ").strip()
    _print_county_resource(case)
    return dict(d)


def _print_header(title: str):
    print()
    print("=" * 60)
    print(f"  LEGAL CLEAR — {title}")
    print("=" * 60)
    print()
    print("This interview collects everything needed to fill your forms.")
    print("Press Enter to skip optional questions.")
    print()


def _print_county_resource(case: dict):
    print("─" * 60)
    print("📋 RECOMMENDED NEXT STEPS:")
    print(f"   1. Visit your county clerk's website for {case.get('court', 'your court')}")
    if case.get("county_specific"):
        print("   2. Ask for the specific form packet for your case type")
    print("   3. Register at myflcourtaccess.com as 'Self-Represented Litigant'")
    if case.get("filing_fee"):
        print(f"   4. Filing fee: {case['filing_fee']}")
    print("─" * 60)


def interview(case_type: str) -> dict:
    """Route to the correct interview function."""
    interviews = {
        "divorce-with-children": interview_divorce_with_children,
        "divorce-without-children": interview_divorce_without_children,
        "child-custody-timesharing": interview_custody,
        "child-support-modification": interview_support_mod,
        "domestic-violence-injunction": interview_dv,
        "name-change-adult": interview_name_change,
    }
    
    if case_type in interviews:
        return interviews[case_type]()
    else:
        return interview_county_only(case_type)


# ── Field Mapping ─────────────────────────────────────────────

def map_fields(data: dict, field_name: str, field_type: str) -> str | bool | None:
    """Map interview data to a form field. Returns None if no mapping."""
    d = data
    fn = field_name.lower().strip()

    # Court info
    if "county" in fn and ("name" in fn or "county" in fn):
        county = d.get("county", "")
        return f"{county}".upper() + " COUNTY, FLORIDA" if county else None
    if "circuit" in fn:
        return f"{d.get('county', '')} COUNTY, FLORIDA" if d.get("county") else None
    if "division" in fn:
        ct = d.get("_case_type", "")
        if "divorce" in ct or "custody" in ct or "support" in ct:
            return "FAMILY"
        elif "probate" in ct or "guardianship" in ct:
            return "PROBATE"
        return None

    # Petitioner
    if fn in ("petitioner", "full legal name", "your full name"):
        return d.get("petitioner_full_name")
    if "petitioner" in fn and "address" in fn:
        return d.get("petitioner_address")
    if "petitioner" in fn and "city" in fn:
        return d.get("petitioner_city")
    if "petitioner" in fn and "state" in fn:
        return d.get("petitioner_state", "FL")
    if "petitioner" in fn and "zip" in fn:
        return d.get("petitioner_zip")
    if "petitioner" in fn and "phone" in fn:
        return d.get("petitioner_phone")
    if "petitioner" in fn and "email" in fn:
        return d.get("petitioner_email")
    if "petitioner" in fn and ("birth" in fn or "dob" in fn):
        return d.get("petitioner_dob")
    if "petitioner" in fn and "driver" in fn:
        return d.get("petitioner_dl")
    if ("wife" in fn or "husband" in fn) and "petitioner" in fn:
        if d.get("petitioner_is") == "W":
            return "wife" in fn
        elif d.get("petitioner_is") == "H":
            return "husband" in fn

    # Respondent
    if fn in ("respondent", "respondent's full name"):
        return d.get("respondent_full_name")
    if "respondent" in fn and "address" in fn:
        return d.get("respondent_address")
    if "respondent" in fn and "city" in fn:
        return d.get("respondent_city")
    if "respondent" in fn and "state" in fn:
        return d.get("respondent_state", "FL")
    if "respondent" in fn and "zip" in fn:
        return d.get("respondent_zip")
    if "respondent" in fn and "phone" in fn:
        return d.get("respondent_phone")
    if "respondent" in fn and ("birth" in fn or "dob" in fn):
        return d.get("respondent_dob")

    # Marriage
    if "marriage" in fn and "date" in fn:
        return d.get("marriage_date")
    if "marriage" in fn and "place" in fn:
        parts = [d.get("marriage_city", ""), d.get("marriage_county", ""), d.get("marriage_state", "")]
        return ", ".join(filter(None, parts))
    if "separation" in fn and "date" in fn:
        return d.get("separation_date")

    # Pregnant
    if "petitioner" in fn and "pregnant" in fn:
        return d.get("petitioner_pregnant", False)
    if "respondent" in fn and "pregnant" in fn:
        return d.get("respondent_pregnant", False)

    # Jurisdiction
    if "jurisdiction" in fn and "petitioner" in fn:
        return d.get("jurisdiction") in ("y", "yes", "")
    if "jurisdiction" in fn and "respondent" in fn:
        return False

    # Children
    children = d.get("children", [])
    if "minor child" in fn and "common" in fn:
        return len(children) > 0
    for i, child in enumerate(children):
        child_key = f"child {i+1}"
        if child_key in fn.lower() or f"child{i+1}" in fn.lower():
            if "name" in fn:
                return child.get("name")
            if "birth" in fn or "dob" in fn:
                return child.get("dob")
            if "age" in fn:
                return child.get("age")
            if "sex" in fn:
                return child.get("sex")

    # Financial
    mapping = {
        "petitioner_income": "petitioner" in fn and "income" in fn,
        "respondent_income": "respondent" in fn and "income" in fn,
        "expense_housing": ("housing" in fn or ("mortgage" in fn and "expense" in fn)),
        "expense_utilities": ("utility" in fn or "utilities" in fn),
        "expense_food": "food" in fn and "expense" in fn,
        "expense_medical": "medical" in fn and "expense" in fn,
        "expense_transportation": "transport" in fn,
        "expense_childcare": ("childcare" in fn or "child care" in fn),
        "expense_insurance": "health insurance" in fn and ("cost" in fn or "expense" in fn),
        "assets_home": "home" in fn and "value" in fn,
        "assets_vehicles": "vehicle" in fn and ("value" in fn or "asset" in fn),
        "assets_bank": "bank" in fn and "account" in fn,
        "assets_retirement": "retirement" in fn,
        "debts_mortgage": "mortgage" in fn and "debt" in fn,
        "debts_credit": "credit" in fn and "debt" in fn,
        "debts_loans": "loan" in fn and "debt" in fn,
    }
    for key, condition in mapping.items():
        if condition:
            return d.get(key)

    # Parenting
    parenting_map = {
        "primary_residence": "primary" in fn and "residence" in fn,
        "weekend_schedule": "weekend" in fn,
        "weekday_schedule": "weekday" in fn,
        "holiday_schedule": "holiday" in fn,
        "summer_schedule": "summer" in fn,
        "pickup_location": ("pickup" in fn or "exchange" in fn),
    }
    for key, condition in parenting_map.items():
        if condition:
            val = d.get(key)
            if key == "primary_residence" and val:
                pmap = {"P": d.get("petitioner_full_name"), "R": d.get("respondent_full_name"), "B": "Both parents equally"}
                return pmap.get(val, val)
            return val

    # DV
    if "hide" in fn or "confidential" in fn:
        return d.get("hide_address", False)
    if "describe" in fn and ("violence" in fn or "threat" in fn):
        return d.get("describe_threat")

    # Name change
    if "new" in fn and "first" in fn:
        return d.get("new_first")
    if "new" in fn and "middle" in fn:
        return d.get("new_middle")
    if "new" in fn and "last" in fn:
        return d.get("new_last")
    if "reason" in fn and "change" in fn:
        return d.get("reason")

    # Child support modification
    if "change" in fn and "reason" in fn:
        return d.get("change_reason")

    return None


# ── Form Filling ──────────────────────────────────────────────

def fill_forms(data: dict, output_dir: Path) -> list:
    """Find and fill all forms for the case type."""
    case_type = data["_case_type"]
    patterns = CASE_FORM_PATTERNS.get(case_type, [])

    if not patterns:
        print(f"  ℹ️  {case_type}: forms are county-specific, no PDFs in catalog.")
        print(f"  → See the interview output for next steps.")
        print(f"  → Output saved to {output_dir}/interview_data.json")
        return []

    all_forms = list(FORMS_DIR.glob("*.pdf"))
    filled = []

    for pdf_file in sorted(all_forms):
        if pdf_file.stat().st_size < 1000:
            continue
        name = pdf_file.name

        matches = False
        for pat in patterns:
            clean = pat.replace("(", "").replace(")", "")
            if clean in name.replace("-", "").replace("_", ""):
                matches = True
                break
        if not matches:
            continue

        form_info = catalog.get("forms", {}).get(pdf_file.stem, {})
        fields = form_info.get("fields", [])
        if not fields:
            continue

        field_values = {}
        for field in fields:
            val = map_fields(data, field["name"], field.get("type_name", "text"))
            if val is not None:
                field_values[field["name"]] = val

        if not field_values:
            print(f"  {name}: no fields matched, skipping")
            continue

        out_path = output_dir / name
        success = fill_pdf(str(pdf_file), str(out_path), field_values)
        if success:
            filled.append(out_path.name)
            print(f"  ✓ {name}: {len(field_values)} fields filled")

    return filled


def fill_pdf(src: str, dst: str, values: dict) -> bool:
    """Fill a PDF using pymupdf subprocess."""
    values_json = json.dumps(values)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(values_json)
        tmp = f.name

    code = f'''
import pymupdf, json, sys
with open("{tmp}") as f:
    values = json.load(f)
doc = pymupdf.open("{src}")
fc = 0
ec = 0
for page in doc:
    for w in page.widgets():
        n = w.field_name.strip() if w.field_name else ""
        if n in values:
            try:
                if w.field_type == 2:
                    w.field_value = bool(values[n])
                elif w.field_type == 3:
                    w.field_value = values[n]
                else:
                    w.field_value = str(values[n])
                w.update()
                fc += 1
            except:
                ec += 1
doc.save("{dst}")
doc.close()
print(f"OK {{fc}} {{ec}}")
'''
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
    Path(tmp).unlink(missing_ok=True)
    return result.returncode == 0


# ── Main ──────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--list" in sys.argv:
        print("Case types available:")
        for ct, cfg in CASE_FORM_MAP.items():
            forms = ", ".join(cfg.get("forms", []) or ["county-specific"])
            cs = " ⚠️ county-specific" if cfg.get("county_specific") else ""
            print(f"  {ct}: {forms}{cs}")
        sys.exit(0)

    if len(sys.argv) < 2:
        print("Usage: python3 auto_fill.py <case-type>")
        print()
        print("Case types:")
        for ct in CASE_FORM_MAP:
            print(f"  {ct}")
        print()
        print("Use --list for details on each case type.")
        sys.exit(1)

    case = sys.argv[1]
    if case not in CASE_FORM_MAP:
        print(f"Unknown case type: {case}")
        print(f"Available: {', '.join(CASE_FORM_MAP.keys())}")
        sys.exit(1)

    data = interview(case)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(f"/tmp/legal_clear_{ts}")
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "interview_data.json", "w") as f:
        json.dump(dict(data), f, indent=2)

    print()
    print(f"Filling forms for {case}...")
    print()
    filled = fill_forms(data, out_dir)

    print()
    print("=" * 60)
    if filled:
        print(f"  COMPLETE: {len(filled)} forms filled")
        print(f"  Output directory: {out_dir}")
        print(f"  Next step: Upload files to myflcourtaccess.com")
    else:
        print(f"  COMPLETE: interview saved")
        print(f"  Output directory: {out_dir}")
        case_info = CASE_FORM_MAP.get(case, {})
        if case_info.get("note"):
            print(f"  📋 {case_info['note']}")
    print("=" * 60)
