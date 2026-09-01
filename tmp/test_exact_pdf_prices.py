import sys

sys.path.insert(0, "c:/Users/Pasante/Desktop/AnalizadorPlanillas/pricebot/api")
import main

raw_data = {
    "pdf_pages": [
        "BE64-12-150 49440,42 TBE-07-150 17814,76",
        "TEP-09-450 2617,85 TEP-09-600 3175,54",
        "CPP45--07-050 2934,12",
    ]
}

prices = main._extract_unambiguous_pdf_prices(raw_data)
for code in sorted(prices):
    print(f"{code}: {prices[code]}")

assert prices["BE64-12-150"] == "49440.42"
assert prices["TBE-07-150"] == "17814.76"
assert prices["TEP-09-450"] == "2617.85"
assert prices["TEP-09-600"] == "3175.54"
assert prices["CPP45-07-050"] == "2934.12"
print("PASS")
