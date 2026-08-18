"""Compara las 974 filas del nuevo extractor vs los 141 códigos que se agregaron manualmente."""
import json, pathlib

# JSON actual (producido por el extractor mejorado: 974 filas)
current = json.loads(pathlib.Path('Respuestas/LCT Lista de Precios 02-2026 (4).json').read_text(encoding='utf-8'))
current_codes = {r.get('Cód. Artículo','').strip() for r in current['rows']}
print(f"Filas del extractor mejorado: {len(current['rows'])}")

# Todos los códigos que habíamos añadido manualmente (sesiones 7 + 8)
session7 = [  # páginas 16, 22-24, 34 (85 filas)
    "3000","3001","3002","3003","3004","3005","3006","3007","3008","3009",
    "3010","3011","3012","3013","3014","3015","3016","3017","3018","3019",
    "3033","3034","3035","3036","3037","3038","3039","3041","3042","3043","3044",
    "3045","3046","3047","3048","3049","3050","3051","3052","3053","3054","3055",
    "3056","3057","3058","3059","3060","3061",
    "4033","4072","4315","4038","4312","4039","4040",
    "4032","4073","4074","4035","4036","4075","4332","4333","4310","4034","4037","4057",
    "4306","4334","4335","4303","4031","4055","4319","4318","4051","4052","4053","4056","4054",
    "4076","4101","4100","4103","4030",
]
session8 = [  # 56 códigos de la segunda auditoría
    "2170","2171","2172","2181","2182",
    "2200","2201","2202","2203","2204","2205","2206","2207","2208","2209","2210","2211","2212",
    "3130","3131","3132","3133","3135","3136","3137","3138","3140","3142","3143","3144",
    "3153","3156","3157","3158",
    "3300","3302","3303","3305","3307","3308","3309","3311","3320","3321","3322","3324","3325",
    "4761","4764","4771","5924","5935","5937","5943","5945","6030"
]

all_manual = set(session7 + session8)
now_captured = all_manual & current_codes
still_missing = all_manual - current_codes

print(f"\nDe {len(all_manual)} que se agregaron manualmente:")
print(f"  Ahora capturados por el extractor: {len(now_captured)}")
print(f"  Aún requieren patch manual:         {len(still_missing)}")

print(f"\nAún faltantes ({len(still_missing)}):")
for c in sorted(still_missing, key=lambda x: int(x)):
    print(f"  {c}")
