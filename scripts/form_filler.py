#!/usr/bin/env python3
"""
Legal Clear — PDF Auto-Fill Engine
Extracts form fields, maps them to interview questions, and generates filled PDFs.

Usage:
    python3 form_filler.py --case divorce-with-children --output /tmp/filled.pdf
    python3 form_filler.py --interactive
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime

VENV_PYTHON = "/home/hermes/wiki/venv/bin/python3"
FORMS_DIR = Path("/home/hermes/wiki/raw/forms")
FIELDS_FILE = FORMS_DIR / "form_fields.json"

# ── Load form field catalog ──
with open(FIELDS_FILE) as f:
    form_fields_data = json.load(f)

# ── Case → Forms Mapping (which forms needed for each case type) ──
CASE_FORM_MAP = {
    "divorce-with-children": {
        "forms": ["12.901(b)(1)", "12.902(d)", "12.902(e)", "12.995(a)"],
        "alternates": {"12.902(b)": "income_under_50k", "12.902(c)": "income_over_50k"},
        "filing_fee": "$408.00",
    },
    "divorce-without-children": {
        "forms": ["12.901(b)(2)"],
        "alternates": {"12.902(b)": "income_under_50k", "12.902(c)": "income_over_50k"},
        "filing_fee": "$408.00",
    },
}

# ── Interview Questions → Field Maps ──
# Maps plain-English question identifiers → form field names
INTERVIEW_MAP = {
    # Court info
    "court_circuit": ["NAME OF CIRCUIT COURT"],
    "court_county": ["NAME OF COUNTY"],
    "case_number": ["Case No"],
    "division": ["Division"],
    
    # Petitioner info
    "petitioner_name": ["Petitioner", "full legal name"],
    "petitioner_is_wife": ["check if petitioner is"],
    "petitioner_is_husband": [],  # inferred from above
    "petitioner_pregnant": ["check if petitioner is pregnant", "Baby is due on date"],
    
    # Respondent info
    "respondent_name": ["Respondent"],
    "respondent_is_wife": ["check if repondent is"],
    "respondent_pregnant": ["check if respondent is pregnant", "Baby is due on date-2"],
    
    # Marriage info
    "marriage_date": ["Date of marriage month day year"],
    "separation_date": ["date of separation1"],
    "separation_approximate": ["check if date is approximate"],
    "marriage_place": ["Place of marriage county state country"],
    
    # Jurisdiction
    "jurisdiction_petitioner_lives_here": ["check jurisdiction if petitioner"],
    "jurisdiction_respondent_lives_here": ["check jurisdiction if respondent"],
    "jurisdiction_both_live_here": ["check jurisdiction if petitioner and respondent"],
    
    # Children
    "has_minor_children": ["check if minor child common to both"],
    "has_non_common_children": ["check if child not common to both parties"],
    "child_name_dob": [
        "name and date of birth child 1", "name and date of birth child 2",
        "name and date of birth child 3", "name and date of birth child 4",
        "name and date of birth child 5", "name and date of birth child 6",
    ],
    
    # Financial (12.902b)
    "income_amount": [],
    "employer_name": [],
    "monthly_expenses": [],
    "assets_home": [],
    "assets_vehicles": [],
    "debts_credit_cards": [],
    "debts_mortgages": [],
    
    # Parenting plan (12.995a)
    "parenting_weekend_schedule": [],
    "parenting_weekday_schedule": [],
    "parenting_holiday_schedule": [],
    "parenting_summer_schedule": [],
    
    # Child support (12.902e)
    "mother_income": [],
    "father_income": [],
    "childcare_costs": [],
    "health_insurance_cost": [],
    "overnights_with_mother": [],
    "overnights_with_father": [],
}


def get_form_fields(form_id: str) -> list:
    """Get all field definitions for a form."""
    for key, data in form_fields_data.items():
        if form_id in key and data.get("field_count", 0) > 0:
            return data["fields"]
    return []


def fill_pdf(form_path: str, output_path: str, field_values: dict) -> bool:
    """Fill a PDF form with values using pymupdf."""
    import tempfile
    form_path = str(Path(form_path).resolve())
    output_path = str(Path(output_path).resolve())
    values_json = json.dumps(field_values)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(values_json)
        tmp_json = f.name
    
    code = f"""
import pymupdf, json, sys
with open("{tmp_json}") as f:
    values = json.load(f)
doc = pymupdf.open("{form_path}")
filled = 0
for page in doc:
    for widget in page.widgets():
        name = widget.field_name.strip() if widget.field_name else ""
        if name in values:
            val = values[name]
            try:
                if widget.field_type == 2:
                    widget.field_value = bool(val)
                elif widget.field_type == 3:
                    widget.field_value = val
                else:
                    widget.field_value = str(val)
                widget.update()
                filled += 1
            except Exception as e:
                print(f"  WARN: {{name}}: {{e}}", file=sys.stderr)
doc.save("{output_path}")
doc.close()
print(f"Filled {{filled}} fields")
"""
    result = subprocess.run(
        [VENV_PYTHON, "-c", code],
        capture_output=True, text=True, timeout=30
    )
    Path(tmp_json).unlink(missing_ok=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    print(result.stdout.strip())
    return True


def interview_divorce_with_children() -> dict:
    """Collect user data for divorce with children."""
    print()
    print("=" * 60)
    print("  DIVORCE WITH CHILDREN — Form Auto-Fill Interview")
    print("=" * 60)
    print()
    print("I'll ask you questions and fill out your forms automatically.")
    print("Press Enter to skip optional questions.")
    print()
    
    data = {}
    
    # ── About You (Petitioner) ──
    print("── ABOUT YOU (the person filing) ──")
    data["petitioner_name"] = input("  Your full legal name: ").strip()
    data["petitioner_role"] = input("  Are you the [W]ife or [H]usband? ").strip().upper()
    pregnant = input("  Are you pregnant? [y/N]: ").strip().lower()
    if pregnant == "y":
        data["petitioner_pregnant"] = True
        data["petitioner_due_date"] = input("  Due date (MM/DD/YYYY): ").strip()
    else:
        data["petitioner_pregnant"] = False
    
    # ── About Spouse (Respondent) ──
    print()
    print("── ABOUT YOUR SPOUSE ──")
    data["respondent_name"] = input("  Spouse's full legal name: ").strip()
    respondent_pregnant = input("  Is your spouse pregnant? [y/N]: ").strip().lower()
    if respondent_pregnant == "y":
        data["respondent_pregnant"] = True
        data["respondent_due_date"] = input("  Due date (MM/DD/YYYY): ").strip()
    
    # ── Marriage ──
    print()
    print("── ABOUT YOUR MARRIAGE ──")
    data["marriage_date"] = input("  Date of marriage (MM/DD/YYYY): ").strip()
    data["marriage_place"] = input("  Place of marriage (City, County, State): ").strip()
    data["separation_date"] = input("  Date of separation (MM/DD/YYYY, or skip): ").strip()
    data["jurisdiction"] = input("  Do you live in the county you're filing in? [Y/n]: ").strip().lower()
    
    # ── Children ──
    print()
    print("── ABOUT YOUR CHILDREN ──")
    data["children"] = []
    num = input("  How many minor children do you have together? ").strip()
    try:
        num = int(num)
    except ValueError:
        num = 0
    
    for i in range(num):
        print(f"\n  Child {i+1}:")
        name = input(f"    Full name: ").strip()
        dob = input(f"    Date of birth (MM/DD/YYYY): ").strip()
        data["children"].append({"name": name, "dob": dob})
    
    # ── Court ──
    print()
    print("── COURT INFORMATION ──")
    data["county"] = input("  County you're filing in: ").strip()
    
    # ── Financial (basic) ──
    print()
    print("── FINANCIAL (skip for now or enter basics) ──")
    income = input("  Your annual gross income (approx): $").strip()
    data["petitioner_income"] = income
    income_s = input("  Spouse's annual gross income (approx): $").strip()
    data["respondent_income"] = income_s
    data["income_under_50k"] = input("  Is your income under $50,000/year? [Y/n]: ").strip().lower() != "n"
    
    # ── Parenting Plan ──
    print()
    print("── PARENTING PLAN (basic) ──")
    data["time_sharing"] = input("  Proposed time-sharing (describe briefly): ").strip()
    
    return data


def build_form_values(interview_data: dict, form_id: str) -> dict:
    """Convert interview data to form field values."""
    fields = get_form_fields(form_id)
    values = {}
    
    d = interview_data
    
    for field in fields:
        name = field["name"]
        ftype = field["type_name"]
        
        # Court info fields
        if "CIRCUIT" in name.upper() and d.get("county"):
            # Would need county→circuit lookup
            pass
        if name == "NAME OF COUNTY" and d.get("county"):
            values[name] = d["county"].upper() + " COUNTY, FLORIDA"
        
        # Petitioner
        if name == "full legal name" and d.get("petitioner_name"):
            values[name] = d["petitioner_name"]
        if name == "Petitioner" and d.get("petitioner_name"):
            values[name] = d["petitioner_name"]
        if "check if petitioner is" in name.lower() and d.get("petitioner_role"):
            values[name] = (d["petitioner_role"] == "W")
        if name == "check if petitioner is pregnant" and "petitioner_pregnant" in d:
            values[name] = d["petitioner_pregnant"]
        if name == "Baby is due on date" and d.get("petitioner_due_date"):
            values[name] = d["petitioner_due_date"]
        
        # Respondent
        if name == "Respondent" and d.get("respondent_name"):
            values[name] = d["respondent_name"]
        if "check if repondent is" in name.lower() and d.get("respondent_pregnant"):
            pass  # skip this mapping issue
        if "check if respondent is pregnant" in name.lower() and d.get("respondent_pregnant"):
            values[name] = d.get("respondent_pregnant", False)
        if name == "Baby is due on date-2" and d.get("respondent_due_date"):
            values[name] = d["respondent_due_date"]
        
        # Marriage
        if "Date of marriage" in name and d.get("marriage_date"):
            values[name] = d["marriage_date"]
        if "Place of marriage" in name and d.get("marriage_place"):
            values[name] = d["marriage_place"]
        if "date of separation" in name.lower() and d.get("separation_date"):
            values[name] = d["separation_date"]
        
        # Jurisdiction
        if "check jurisdiction if petitioner" in name.lower() and d.get("jurisdiction") == "y":
            values[name] = True
        
        # Children
        children = d.get("children", [])
        if "check if minor child common to both" in name.lower() and children:
            values[name] = True
        for i, child in enumerate(children):
            if name == f"name and date of birth child {i+1}":
                values[name] = f"{child['name']}, DOB: {child['dob']}"
        
        # Parenting plan
        if d.get("time_sharing"):
            for n in fields:
                if "time-sharing" in n["name"].lower() or "parenting" in n["name"].lower():
                    pass  # would populate schedule fields
    
    return values


def run_auto_fill(case_id: str, output_dir: str = None):
    """Run the full auto-fill pipeline for a case type."""
    if output_dir is None:
        output_dir = f"/tmp/legal_clear_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Collect data
    if case_id == "divorce-with-children":
        data = interview_divorce_with_children()
    else:
        print(f"No interview defined for: {case_id}")
        return
    
    # Save interview data
    with open(f"{output_dir}/interview_data.json", "w") as f:
        json.dump(data, f, indent=2)
    
    # Fill each form
    case_config = CASE_FORM_MAP.get(case_id, {})
    forms = case_config.get("forms", [])
    
    # Determine financial form
    if data.get("income_under_50k", True):
        forms.append("12.902(b)")
    else:
        forms.append("12.902(c)")
    
    results = []
    for form_id in forms:
        # Find the file
        pdf_files = list(FORMS_DIR.glob(f"*{form_id.replace('(','_').replace(')','_')}*.pdf"))
        if not pdf_files:
            print(f"  ✗ Form {form_id} not downloaded yet")
            continue
        
        src = str(pdf_files[0])
        out = f"{output_dir}/{form_id.replace('(', '_').replace(')', '_')}.pdf"
        
        print(f"\nFilling {form_id}...")
        values = build_form_values(data, form_id)
        if fill_pdf(src, out, values):
            results.append(out)
            print(f"  ✓ Saved to {out}")
    
    print(f"\n{'=' * 60}")
    print(f"  COMPLETE: {len(results)} forms filled")
    print(f"  Output: {output_dir}")
    print(f"  Next: Upload these to myflcourtaccess.com to e-file")
    print(f"{'=' * 60}")
    
    return results


if __name__ == "__main__":
    if "--case" in sys.argv:
        idx = sys.argv.index("--case")
        case_id = sys.argv[idx + 1]
        output = None
        if "--output" in sys.argv:
            oidx = sys.argv.index("--output")
            output = sys.argv[oidx + 1]
        run_auto_fill(case_id, output)
    else:
        print("Usage: python3 form_filler.py --case divorce-with-children [--output /path]")
        print()
        print("Available cases:")
        for cid in CASE_FORM_MAP:
            print(f"  {cid}")
