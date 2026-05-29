#!/usr/bin/env python3
"""
Florida Pro Se Legal Form Finder — Phase 2
Decision tree interview → form recommendations with plain-English explanations.

Usage:
    python form_finder.py                    # interactive interview
    python form_finder.py --case divorce-with-children  # direct lookup
    python form_finder.py --county "Miami-Dade" --case small-claims
"""

import json
import sys
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "raw" / "articles" / "florida-court-forms-dataset.json"

# ── Load dataset ──────────────────────────────────────────────
with open(DATA_PATH) as f:
    ds = json.load(f)

# Build lookups
county_to_circuit = {}
for c in ds["circuits"]:
    for county in c["counties"]:
        county_to_circuit[county.lower()] = c

county_to_clerk = {c["county"].lower(): c for c in ds["counties"]}


# ── Plain-English Form Explanations ───────────────────────────
FORM_EXPLANATIONS = {
    # Divorce
    "12.901(b)(1)": "This starts your divorce when you have children. It tells the court who you are, basic facts about your marriage, and what you want decided about kids, money, and property.",
    "12.901(b)(2)": "This starts your divorce when you have no minor children. It's simpler — tells the court who you are, what you own and owe, and that you want a divorce.",
    "12.901(a)": "The fastest, cheapest divorce. Use this ONLY if you both agree on everything, have no minor children, neither is pregnant, and both waive trial/appeal rights.",
    "12.902(b)": "Short financial form. Use if your income is UNDER $50,000/year. Lists income, expenses, assets, and debts. Court uses this to decide alimony and child support.",
    "12.902(c)": "Long financial form. Use if your income is $50,000 OR MORE/year. More detailed than the short form.",
    "12.902(d)": "Tells the court where your children lived for the past 5 years. Required for any case with kids — confirms Florida is the right state to decide custody.",
    "12.902(e)": "Calculates child support. Fill in incomes, childcare costs, health insurance, and parenting time. The formula gives you the monthly amount.",
    "12.902(f)(1)": "If you and your spouse agree on everything — property, debts, time with kids, support — write it here. A signed agreement usually gets approved and saves time vs fighting.",
    "12.902(f)(2)": "Same as above but for couples without children — how you agree to split property and debts.",
    "12.932": "Certifies you've shared required financial documents with the other side: tax returns, pay stubs, bank statements, credit card statements.",
    "12.990(b)(1)": "The final order the judge signs to end your marriage when you have children. Submit this if your case is uncontested (you both agree).",
    "12.990(a)": "The final order the judge signs to end your marriage when you have no children.",
    # Custody
    "12.983(a)": "For unmarried parents — legally establish who the father is AND decide custody, time-sharing, and child support.",
    "12.995(a)": "Your proposed schedule for sharing time with the children: which days each parent has them, holidays, vacations, how decisions are made.",
    # Child Support
    "12.905": "Ask the court to change an existing child support order because your situation changed significantly (job loss, income change, child's needs changed).",
    # Domestic Violence
    "DV-1": "Ask the court for IMMEDIATE protection from domestic violence. The judge can order the person to stay away from you, your home, and your work, and stop all contact.",
    "DV-2": "For repeat violence from someone you don't live with and have no family/dating relationship with — neighbor, coworker, stranger.",
    "DV-3": "For violence from someone you're dating or have dated.",
    "DV-4": "For sexual violence — you don't need a prior relationship with the person.",
    "12.902(c)": "Long financial form. Use if your income is $50,000 OR MORE/year. More detailed than the short form — itemizes every asset, debt, income source, and expense.",
    "12.902(c)-DV": "Request to keep your address confidential if you fear the abuser will find you. File this alongside your injunction petition.",
    # Eviction
    "County-Specific": "Forms that vary by county. DIY Florida is the best option when available — it auto-selects and fills the correct forms. Otherwise, get forms directly from your county clerk's website or self-help center.",
    # Small Claims
    "7.330": "Start a small claims case for car accident damages — someone damaged your car and won't pay.",
    "7.331": "Start a small claims case when someone bought goods from you and never paid.",
    "7.332": "Start a small claims case when you did work or provided materials and weren't paid.",
    "7.333": "Start a small claims case when you lent someone money and they won't pay you back.",
    "7.334": "Start a small claims case when someone signed a written promise to pay (promissory note) and didn't.",
    "7.335": "Start a small claims case to get your security deposit back from a landlord who wrongfully kept it.",
    "7.340": "The official notice the court sends to the person you're suing — tells them they're being sued, by whom, for how much, and when to appear.",
    "7.343": "After you win, send this to the person who owes you. They must list their assets, bank accounts, employer, and property — so you know where to collect.",
    # Name Change
    "12.982(a)": "Ask the court to legally change your name. Requires fingerprinting and background check. Must explain why you want the change.",
    "12.982(d)": "The final order granting your name change. Use this to update your ID, Social Security, and other documents.",
    # Probate
    "Probate-Summary": "Ask the court to distribute a small estate (under $75,000) without full probate. Faster and cheaper than formal probate.",
    "Probate-Homestead": "If the deceased owned a Florida home that was their primary residence, ask the court to declare it protected homestead.",
    "Probate-Formal": "Start full probate. Name a personal representative (executor) to manage the estate. Required for estates over $75,000 or complex assets.",
    "Probate-Oath": "The executor swears under oath to faithfully carry out their duties — pay debts, file taxes, distribute assets.",
    "Probate-Letters": "The official document proving you're the executor. Show this to banks and others to prove your authority.",
    "Guardianship-Petition": "Ask the court to appoint a guardian for someone who can't care for themselves. Explain why guardianship is needed.",
    "Guardianship-Application": "Your application to be the guardian. Requires background check, credit check, and guardianship education.",
    "Guardianship-Plan": "Your detailed plan for caring for the person — where they'll live, medical care, finances. Updated annually.",
    # Expungement
    "FDLE-Form": "The FIRST step in expungement. Send this to FDLE to check if you're eligible. They issue a Certificate of Eligibility — you can't proceed without it.",
    "Seal-Expunge-Petition": "The formal court request to seal or expunge. Attach the FDLE certificate and explain why you qualify.",
    "Seal-Expunge-Affidavit": "Your sworn statement: you've never had a prior expungement, aren't under court supervision, and meet all qualifications.",
}


# ── Decision Tree ─────────────────────────────────────────────
# Maps user answers → case_type_id
DECISION_TREE = {
    "start": {
        "question": "What's your legal situation about?",
        "options": {
            "family": {"label": "Family or domestic matter (divorce, kids, protection)", "next": "family"},
            "housing": {"label": "Housing (eviction, landlord/tenant dispute)", "next": "housing"},
            "money": {"label": "Someone owes me money", "next": "money"},
            "records": {"label": "Criminal record (expunge/seal)", "next": "expungement"},
            "estate": {"label": "Estate, will, probate, or guardianship", "next": "estate"},
        }
    },
    "family": {
        "question": "What kind of family matter?",
        "options": {
            "divorce": {"label": "Divorce / ending a marriage", "next": "divorce"},
            "custody": {"label": "Child custody or time-sharing (not married)", "next": "custody"},
            "support": {"label": "Child support — change an existing order", "result": "child-support-modification"},
            "protection": {"label": "Protection from violence / restraining order", "next": "protection"},
            "name": {"label": "Change my name", "result": "name-change-adult"},
        }
    },
    "divorce": {
        "question": "Do you have minor or dependent children with your spouse?",
        "options": {
            "yes": {"next": "divorce_kids"},
            "no": {"next": "divorce_nokids"},
        }
    },
    "divorce_kids": {
        "question": "Is your divorce contested?",
        "options": {
            "contested": {"label": "Yes — we disagree on some things", "result": "divorce-with-children"},
            "uncontested": {"label": "No — we agree on everything", "result": "divorce-with-children", "note": "You can use the same forms but can also submit a Marital Settlement Agreement to speed things up."},
        }
    },
    "divorce_nokids": {
        "question": "Do you and your spouse agree on everything AND have no shared property/debts?",
        "options": {
            "yes": {"label": "Yes — completely simple divorce", "result": "divorce-without-children", "note": "You may qualify for Simplified Dissolution (DIY Florida). Fastest and cheapest option."},
            "no": {"label": "No — we have property to divide or disagree", "result": "divorce-without-children"},
        }
    },
    "custody": {
        "question": "Is paternity (legal fatherhood) already established?",
        "options": {
            "yes": {"label": "Yes — father is on birth certificate or court order exists", "next": "custody_type"},
            "no": {"label": "No — need to establish paternity first", "result": "child-custody-timesharing"},
        }
    },
    "custody_type": {
        "question": "What do you need?",
        "options": {
            "timeshare": {"label": "Set up a time-sharing (custody) schedule", "result": "child-custody-timesharing"},
            "modify": {"label": "Change an existing custody order", "result": "child-custody-timesharing"},
        }
    },
    "protection": {
        "question": "What is your relationship to the person you need protection from?",
        "options": {
            "family": {"label": "Family member or someone I live(d) with", "result": "domestic-violence-injunction"},
            "dating": {"label": "Someone I'm dating or have dated", "result": "domestic-violence-injunction"},
            "other": {"label": "No family or dating relationship (neighbor, coworker, stranger)", "result": "domestic-violence-injunction"},
        }
    },
    "housing": {
        "question": "Are you the landlord or the tenant?",
        "options": {
            "landlord": {"label": "I'm the landlord — need to evict a tenant", "result": "eviction-landlord"},
            "tenant": {"label": "I'm the tenant — being evicted or have a dispute", "result": "eviction-tenant"},
        }
    },
    "money": {
        "question": "What kind of debt or money claim?",
        "options": {
            "auto": {"label": "Car accident damage", "result": "small-claims"},
            "goods": {"label": "Someone bought goods and didn't pay", "result": "small-claims"},
            "work": {"label": "I did work or provided materials and wasn't paid", "result": "small-claims"},
            "loan": {"label": "I lent money and they won't pay back", "result": "small-claims"},
            "deposit": {"label": "Landlord kept my security deposit", "result": "small-claims"},
            "other": {"label": "Other — less than $8,000", "result": "small-claims"},
        }
    },
    "estate": {
        "question": "What do you need?",
        "options": {
            "probate_small": {"label": "Handle a small estate (under $75,000) after someone died", "result": "probate-small-estate"},
            "probate_full": {"label": "Handle a larger estate (over $75,000) after someone died", "result": "probate-full"},
            "guardianship": {"label": "Become guardian for someone who can't care for themselves", "result": "guardianship"},
        }
    },
    "expungement": {
        "question": "Do you already have the FDLE Certificate of Eligibility?",
        "options": {
            "yes": {"result": "expungement-sealing"},
            "no": {"result": "expungement-sealing", "note": "STEP 1: Apply for FDLE Certificate of Eligibility first. This takes 2-4 months. You cannot file in court without it."},
        }
    },
}


def find_case(case_id: str):
    """Get case type info by ID."""
    return ds["case_types"].get(case_id)


def get_county_info(county_name: str):
    """Get circuit and clerk info for a county."""
    key = county_name.lower().strip()
    circuit = county_to_circuit.get(key)
    clerk = county_to_clerk.get(key)
    return circuit, clerk


def format_recommendation(case_id: str, county_name: str = "") -> str:
    """Produce a full recommendation for a case type and optional county."""
    case = find_case(case_id)
    if not case:
        return f"Unknown case type: {case_id}"

    lines = []
    lines.append("=" * 68)
    lines.append(f"  LEGAL CLEAR — Form Recommendation")
    lines.append("=" * 68)
    lines.append("")
    lines.append(f"📋 Case Type: {case['name']}")
    lines.append(f"📝 What it is: {case['description']}")
    lines.append(f"🏛  Court: {case['court']}")
    lines.append(f"💰 Filing Fee: {case['filing_fee']}")
    lines.append("")

    # DIY Florida check
    if case.get("diy_florida"):
        lines.append("⭐ DIY FLORIDA IS AVAILABLE!")
        lines.append(f"   Interview: {case.get('diy_florida_interview', 'Available')}")
        lines.append(f"   Go to: {ds['centralized_sources']['diy_florida']['url']}")
        lines.append(f"   Register as 'Self-Represented Litigant' → DIY tab")
        lines.append(f"   DIY Florida will auto-fill ALL forms and can e-file directly.")
        lines.append(f"   This is the EASIEST way — we highly recommend it.")
        lines.append("")

    # Forms
    lines.append("─" * 68)
    lines.append("📄 FORMS YOU NEED:")
    lines.append("─" * 68)
    for f in case.get("forms", []):
        required = "🔴 REQUIRED" if f.get("required") else "🟡 Optional"
        lines.append(f"\n  {required}")
        lines.append(f"  Form {f['form_id']}: {f['name']}")
        expl = FORM_EXPLANATIONS.get(f['form_id'], "")
        if expl:
            # Word-wrap explanation
            words = expl.split()
            wrapped = []
            line = "    → "
            for w in words:
                if len(line) + len(w) + 1 > 65:
                    wrapped.append(line)
                    line = "      " + w
                else:
                    line += " " + w
            wrapped.append(line)
            lines.extend(wrapped)

    if case.get("note"):
        lines.append("")
        lines.append(f"  ⚠️  NOTE: {case['note']}")

    # Source
    lines.append("")
    lines.append("─" * 68)
    lines.append("🔗 OFFICIAL SOURCE:")
    lines.append("─" * 68)
    if case.get("diy_florida"):
        lines.append(f"  Primary: DIY Florida → {ds['centralized_sources']['diy_florida']['url']}")
    lines.append(f"  Forms:   {ds['centralized_sources']['family_law_forms']['url']}")
    lines.append(f"  Help:    {ds['centralized_sources']['florida_courts_help']['url']}")

    # County-specific info
    if county_name:
        circuit, clerk = get_county_info(county_name)
        lines.append("")
        lines.append("─" * 68)
        lines.append(f"📍 YOUR COUNTY: {county_name}")
        lines.append("─" * 68)
        if circuit:
            lines.append(f"  Circuit: {circuit['name']} (Circuit #{circuit['id']})")
            lines.append(f"  Counties in circuit: {', '.join(circuit['counties'])}")
            lines.append(f"  Self-Help: {circuit['self_help_url']}")
        else:
            lines.append(f"  ⚠️  County '{county_name}' not found. Check spelling.")
        if clerk:
            lines.append(f"  Clerk website: {clerk['clerk_url']}")
            lines.append(f"  Clerk forms:   {clerk['forms_url']}")

    # Legal aid and disclaimer
    lines.append("")
    lines.append("─" * 68)
    lines.append("🆘 FREE HELP:")
    lines.append("─" * 68)
    lines.append(f"  Legal Aid Directory: {ds['centralized_sources']['legal_aid']['url']}")
    lines.append(f"  Free Legal Answers:  {ds['centralized_sources']['free_legal_answers']['url']}")
    lines.append(f"  Lawyer Referral:     {ds['centralized_sources']['florida_bar_referral']['url']}")
    lines.append(f"  ($25 for 30-minute consultation)")
    lines.append("")
    lines.append("─" * 68)
    lines.append("⚠️  DISCLAIMER:")
    lines.append("   This is NOT legal advice. Forms and fees may change.")
    lines.append("   Always verify with the official source.")
    lines.append("   You represent yourself — the court expects you to")
    lines.append("   follow all rules and procedures correctly.")
    lines.append("   When in doubt, consult an attorney.")
    lines.append("─" * 68)

    return "\n".join(lines)


def run_interview():
    """Interactive decision tree interview."""
    print()
    print("=" * 68)
    print("  LEGAL CLEAR — AI Form Finder")
    print("  Find the right Florida court forms for your situation")
    print("=" * 68)
    print()
    print("I'll ask a few questions to figure out what forms you need.")
    print()

    node = DECISION_TREE["start"]
    while True:
        print(node["question"])
        print()
        opts = node["options"]
        opt_keys = list(opts.keys())
        for i, key in enumerate(opt_keys, 1):
            label = opts[key].get("label", key)
            print(f"  {i}. {label}")
        print()

        choice = input(f"Enter 1-{len(opt_keys)}: ").strip()
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(opt_keys):
                print("Invalid choice. Try again.\n")
                continue
        except ValueError:
            print("Please enter a number.\n")
            continue

        selected = opts[opt_keys[idx]]

        if "result" in selected:
            result_id = selected["result"]
            note = selected.get("note")
            print()
            if note:
                print(f"💡 {note}")
                print()

            # Ask for county
            county = input("What county are you in? (press Enter to skip): ").strip()
            county = county if county else None
            print()
            print(format_recommendation(result_id, county))
            break
        elif "next" in selected:
            node = DECISION_TREE[selected["next"]]
            print()
        else:
            print("Internal error: no result or next in decision node")
            break


# ── CLI Entry Point ──────────────────────────────────────────
if __name__ == "__main__":
    if "--case" in sys.argv:
        idx = sys.argv.index("--case")
        case_id = sys.argv[idx + 1]
        county = None
        if "--county" in sys.argv:
            cidx = sys.argv.index("--county")
            county = sys.argv[cidx + 1]
        print(format_recommendation(case_id, county))
    elif "--list" in sys.argv:
        for cid, case in ds["case_types"].items():
            diy = "⭐ DIY" if case.get("diy_florida") else "   "
            print(f"  {diy}  {cid}: {case['name']}")
    else:
        run_interview()
