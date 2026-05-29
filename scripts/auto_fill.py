#!/usr/bin/env python3
"""
Legal Clear — Full Auto-Fill Pipeline (Phase 3)
Downloads forms, extracts fields, interviews users, fills PDFs.

Usage:
    python3 auto_fill.py divorce-with-children
    python3 auto_fill.py divorce-without-children
    python3 auto_fill.py paternity-custody
    python3 auto_fill.py domestic-violence
    python3 auto_fill.py name-change
"""

import subprocess, json, sys, re, tempfile
from pathlib import Path
from datetime import datetime
from collections import defaultdict

VENV = "/home/hermes/wiki/venv/bin/python3"
FORMS_DIR = Path("/home/hermes/wiki/raw/forms")
CATALOG_PATH = FORMS_DIR / "full_catalog.json"

# Load catalog
with open(CATALOG_PATH) as f:
    catalog = json.load(f)

# ── Interview Questions ──
def interview(case_type: str) -> dict:
    """Conduct a comprehensive interview and return structured data."""
    d: dict = defaultdict(str)
    d["_case_type"] = case_type
    d["_date"] = datetime.now().strftime("%Y-%m-%d")
    
    print()
    print("=" * 60)
    print(f"  LEGAL CLEAR — {case_type.replace('-', ' ').upper()}")
    print("=" * 60)
    print()
    print("This interview will collect everything needed to fill your forms.")
    print("The filled PDFs will be saved to /tmp/legal_clear_output/")
    print("Then upload them to myflcourtaccess.com to e-file.")
    print()
    
    # ── Court Info ──
    print("── WHERE YOU'RE FILING ──")
    d["county"] = input("  County: ").strip()
    d["circuit"] = input("  Judicial Circuit (e.g., '11th'): ").strip()
    
    # ── Petitioner ──
    print()
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
    
    # ── Respondent ──
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
        d["respondent_is"] = "H" if d["petitioner_is"] == "W" else "W"
        preg = input("  Is the other party pregnant? [y/N]: ").strip().lower()
        d["respondent_pregnant"] = (preg == "y")
    
    # ── Marriage (divorce only) ──
    if case_type.startswith("divorce"):
        print()
        print("── ABOUT THE MARRIAGE ──")
        d["marriage_date"] = input("  Date of marriage (MM/DD/YYYY): ").strip()
        d["marriage_city"] = input("  City of marriage: ").strip()
        d["marriage_county"] = input("  County of marriage: ").strip()
        d["marriage_state"] = input("  State of marriage: ").strip()
        d["separation_date"] = input("  Date separated (MM/DD/YYYY): ").strip()
        d["jurisdiction"] = input("  Do you live in the county you're filing? [Y/n]: ").strip().lower()
    
    # ── Children ──
    if case_type in ("divorce-with-children", "paternity-custody"):
        print()
        print("── ABOUT THE CHILDREN ──")
        d["children"] = []
        num = input("  Number of minor children together: ").strip()
        try:
            num = int(num)
        except:
            num = 0
        
        for i in range(num):
            print(f"\n  Child {i+1}:")
            name = input("    Full name: ").strip()
            dob = input("    Date of birth (MM/DD/YYYY): ").strip()
            age = input("    Age: ").strip()
            sex = input("    Sex [M/F]: ").strip().upper()
            d["children"].append({"name": name, "dob": dob, "age": age, "sex": sex})
    
    # ── Financial ──
    if case_type.startswith("divorce") or case_type == "paternity-custody":
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
    
    # ── Parenting Plan ──
    if case_type in ("divorce-with-children", "paternity-custody"):
        print()
        print("── PARENTING PLAN ──")
        print("  Who will the children primarily live with?")
        d["primary_residence"] = input("  [P]etitioner / [R]espondent / [B]oth equally: ").strip().upper()
        d["weekend_schedule"] = input("  Weekend schedule (describe): ").strip()
        d["weekday_schedule"] = input("  Weekday schedule (describe): ").strip()
        d["holiday_schedule"] = input("  Holiday schedule (describe): ").strip()
        d["summer_schedule"] = input("  Summer schedule (describe): ").strip()
        d["pickup_location"] = input("  Exchange/pickup location: ").strip()
    
    # ── Domestic Violence specifics ──
    if case_type == "domestic-violence":
        print()
        print("── ABOUT THE VIOLENCE ──")
        d["relationship"] = input("  Relationship to abuser [family/dating/cohabitant]: ").strip()
        d["most_recent_incident"] = input("  Date of most recent incident: ").strip()
        d["describe_threat"] = input("  Describe the threat or violence (brief): ").strip()
        d["weapons_involved"] = input("  Were weapons involved? [y/N]: ").strip().lower() == "y"
        hide = input("  Do you need your address kept confidential? [Y/n]: ").strip().lower()
        d["hide_address"] = (hide != "n")
    
    # ── Name Change specifics ──
    if case_type == "name-change":
        print()
        print("── NAME CHANGE ──")
        d["current_name"] = d["petitioner_full_name"]
        d["new_first"] = input("  New first name: ").strip()
        d["new_middle"] = input("  New middle name: ").strip()
        d["new_last"] = input("  New last name: ").strip()
        d["reason"] = input("  Reason for name change: ").strip()
    
    return d


# ── Field Mapping ──
def map_fields(data: dict, field_name: str, field_type: str) -> str | bool | None:
    """Map interview data to a specific form field. Returns None if no mapping."""
    d = data
    fn = field_name.lower().strip()
    
    # Court info
    if "county" in fn and "name" in fn:
        return f"{d.get('county', '')}".upper() if d.get("county") else None
    if "circuit" in fn:
        return f"{d.get('circuit', '')} JUDICIAL CIRCUIT" if d.get("circuit") else None
    if "division" in fn:
        return "FAMILY" if d.get("_case_type", "").startswith("divorce") else None
    
    # Petitioner identity
    if fn in ("petitioner", "full legal name", "your full name"):
        return d.get("petitioner_full_name")
    if fn == "petitioner's address" or ("petitioner" in fn and "address" in fn):
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
    
    # Respondent identity
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
    
    # Pregnant checkboxes
    if "petitioner" in fn and "pregnant" in fn:
        return d.get("petitioner_pregnant", False)
    if "respondent" in fn and "pregnant" in fn:
        return d.get("respondent_pregnant", False)
    if ("wife" in fn or "husband" in fn) and field_type in ("checkbox", "radio"):
        if d.get("petitioner_is") == "W":
            return "wife" in fn
        elif d.get("petitioner_is") == "H":
            return "husband" in fn
    
    # Jurisdiction checkboxes
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
    if "petitioner" in fn and "income" in fn:
        return d.get("petitioner_income")
    if "respondent" in fn and "income" in fn:
        return d.get("respondent_income")
    if "housing" in fn or ("mortgage" in fn and "expense" in fn):
        return d.get("expense_housing")
    if "utility" in fn or "utilities" in fn:
        return d.get("expense_utilities")
    if "food" in fn and "expense" in fn:
        return d.get("expense_food")
    if "medical" in fn and "expense" in fn:
        return d.get("expense_medical")
    if "transport" in fn:
        return d.get("expense_transportation")
    if "childcare" in fn or "child care" in fn:
        return d.get("expense_childcare")
    if "health insurance" in fn and ("cost" in fn or "expense" in fn):
        return d.get("expense_insurance")
    
    # Assets
    if "home" in fn and "value" in fn:
        return d.get("assets_home")
    if "vehicle" in fn and ("value" in fn or "asset" in fn):
        return d.get("assets_vehicles")
    if "bank" in fn and "account" in fn:
        return d.get("assets_bank")
    if "retirement" in fn:
        return d.get("assets_retirement")
    if "mortgage" in fn and "debt" in fn:
        return d.get("debts_mortgage")
    if "credit" in fn and "debt" in fn:
        return d.get("debts_credit")
    if "loan" in fn and "debt" in fn:
        return d.get("debts_loans")
    
    # Parenting
    if "primary" in fn and "residence" in fn:
        m = {"P": d.get("petitioner_full_name"), "R": d.get("respondent_full_name"), "B": "Both parents equally"}
        return m.get(d.get("primary_residence", ""), "")
    if "weekend" in fn:
        return d.get("weekend_schedule")
    if "weekday" in fn:
        return d.get("weekday_schedule")
    if "holiday" in fn:
        return d.get("holiday_schedule")
    if "summer" in fn:
        return d.get("summer_schedule")
    if "pickup" in fn or "exchange" in fn:
        return d.get("pickup_location")
    
    # DV
    if "hide" in fn or "confidential" in fn:
        return d.get("hide_address", False)
    if "describe" in fn and ("violence" in fn or "threat" in fn or "incident" in fn):
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
    
    return None


def fill_forms(data: dict, output_dir: Path):
    """Find and fill all forms for the case type."""
    case_type = data["_case_type"]
    
    # Find form files that match this case type
    all_forms = list(FORMS_DIR.glob("*.pdf"))
    
    # Forms needed per case type
    case_form_patterns = {
        "divorce-with-children": ["12.901(b)(1)", "12.902", "12.902(d)", "12.902(e)", "12.995(a)"],
        "divorce-without-children": ["12.901(b)(2)", "12.902"],
        "paternity-custody": ["12.983", "12.902", "12.902(d)", "12.902(e)", "12.995"],
        "domestic-violence": ["12.980"],
        "name-change": ["12.982"],
    }
    
    patterns = case_form_patterns.get(case_type, [])
    filled = []
    
    for pdf_file in sorted(all_forms):
        if pdf_file.stat().st_size < 1000:
            continue
        
        name = pdf_file.name
        
        # Check if this form matches our case
        matches = False
        for pat in patterns:
            if pat.replace("(", "").replace(")", "") in name.replace("-", "").replace("_", ""):
                matches = True
                break
        if not matches:
            continue
        
        # Get form fields from catalog
        form_info = catalog["forms"].get(pdf_file.stem, {})
        fields = form_info.get("fields", [])
        
        if not fields:
            continue
        
        # Map fields
        field_values = {}
        for field in fields:
            val = map_fields(data, field["name"], field["type_name"])
            if val is not None:
                field_values[field["name"]] = val
        
        if not field_values:
            print(f"  {name}: no fields matched, skipping")
            continue
        
        # Fill the form
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
    result = subprocess.run([VENV, "-c", code], capture_output=True, text=True, timeout=30)
    Path(tmp).unlink(missing_ok=True)
    return result.returncode == 0


# ── Main ──
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 auto_fill.py <case-type>")
        print()
        print("Case types:")
        for ct in ["divorce-with-children", "divorce-without-children", "paternity-custody", "domestic-violence", "name-change"]:
            print(f"  {ct}")
        sys.exit(1)
    
    case = sys.argv[1]
    data = interview(case)
    
    # Save interview data
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
    print(f"  COMPLETE: {len(filled)} forms filled")
    print(f"  Output directory: {out_dir}")
    print(f"  Next step: Upload files to myflcourtaccess.com")
    print(f"  Register as 'Self-Represented Litigant' at:")
    print(f"  https://www.myflcourtaccess.com")
    print("=" * 60)
