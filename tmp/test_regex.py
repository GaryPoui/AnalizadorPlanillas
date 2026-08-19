import re

CODE_TOKEN_RE = r"(?:[A-Z][A-Z0-9]{0,7}(?:[-./][A-Z0-9]{1,10}){1,4}|[A-Z]{1,5}\d{2,6}|[A-Z]{2,8}|\d{4,5})"
PRICE_TOKEN_RE = r"(?:\$\s*)?\d{1,3}(?:\.\d{3})*[,\.]\d{2}|(?:\$\s*)?\d{2,7}[,\.]\d{2}|(?:\$\s*)?\d{4,7}"
CODE_PRICE_RE = re.compile(rf"({CODE_TOKEN_RE})\s+({PRICE_TOKEN_RE})")

tests = [
    ("BE64-12-150 49440,42",    [("BE64-12-150", "49440,42")]),
    ("BE64-12-150 49.440,42",   [("BE64-12-150", "49.440,42")]),
    ("TBE-07-150 17814,76",     [("TBE-07-150",  "17814,76")]),
    ("CPE90-64-16-150 24979,47",[("CPE90-64-16-150", "24979,47")]),
    ("CAE-64-16-150 40219,77",  [("CAE-64-16-150", "40219,77")]),
    ("GSE-64/92 1454,55",       [("GSE-64/92",   "1454,55")]),
    ("PC44.28-09-3000 5950,27", [("PC44.28-09-3000", "5950,27")]),
    ("GCE 2444,71",             [("GCE",          "2444,71")]),
    ("2200 708,30",             [("2200",          "708,30")]),
    # parallel line — should find BOTH
    ("BE64-12-300 53486,87 BE92-12-300 61085,84", [("BE64-12-300","53486,87"),("BE92-12-300","61085,84")]),
]

all_ok = True
for line, expected in tests:
    got = CODE_PRICE_RE.findall(line)
    ok = got == expected
    status = "OK" if ok else "FAIL"
    print(f"  [{status}] {line!r}")
    if not ok:
        print(f"         expected {expected}")
        print(f"         got      {got}")
        all_ok = False

print()
print("ALL PASS" if all_ok else "SOME FAILED")
