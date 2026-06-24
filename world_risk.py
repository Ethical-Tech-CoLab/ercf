"""
ACAPS/INFORM-inspired country risk dataset.
Levels mapped to ERCF scale (0-4) from INFORM Severity Index (0-5 scale).
Data sources: ACAPS INFORM Severity Index (Dec 2025), ACAPS Humanitarian Access
Overview (Dec 2024), UNHCR displacement data (2025), OCHA FTS.

Live data overlay: when ACAPS_API_KEY is set, get_risk_by_iso3() and
get_all_risk_levels() augment static scores with live INFORM data
fetched from the ACAPS API (cached in memory for 24 hours).
"""

import time
from typing import Dict, Optional

# ISO 3166-1 numeric → ISO_A3 mapping (for world-atlas TopoJSON IDs)
NUM_TO_ISO3 = {
    4:"AFG", 8:"ALB", 12:"DZA", 24:"AGO", 32:"ARG", 36:"AUS", 40:"AUT",
    50:"BGD", 56:"BEL", 64:"BTN", 68:"BOL", 76:"BRA", 100:"BGR", 104:"MMR",
    108:"BDI", 112:"BLR", 116:"KHM", 120:"CMR", 124:"CAN", 140:"CAF",
    144:"LKA", 148:"TCD", 152:"CHL", 156:"CHN", 170:"COL", 180:"COD",
    188:"CRI", 191:"HRV", 192:"CUB", 196:"CYP", 203:"CZE", 204:"BEN",
    208:"DNK", 218:"ECU", 226:"GNQ", 231:"ETH", 232:"ERI", 233:"EST",
    239:"SGS", 246:"FIN", 250:"FRA", 268:"GEO", 270:"GMB", 276:"DEU",
    288:"GHA", 300:"GRC", 320:"GTM", 324:"GIN", 328:"GUY", 332:"HTI",
    340:"HND", 344:"HKG", 348:"HUN", 356:"IND", 360:"IDN", 364:"IRN",
    368:"IRQ", 372:"IRL", 376:"ISR", 380:"ITA", 388:"JAM", 392:"JPN",
    398:"KAZ", 400:"JOR", 404:"KEN", 408:"PRK", 410:"KOR", 414:"KWT",
    417:"KGZ", 418:"LAO", 422:"LBN", 430:"LBR", 434:"LBY", 440:"LTU",
    442:"LUX", 450:"MDG", 454:"MWI", 458:"MYS", 466:"MLI", 470:"MLT",
    478:"MRT", 484:"MEX", 496:"MNG", 498:"MDA", 504:"MAR", 508:"MOZ",
    516:"NAM", 524:"NPL", 528:"NLD", 533:"ABW", 540:"NCL", 554:"NZL",
    558:"NIC", 562:"NER", 566:"NGA", 578:"NOR", 586:"PAK", 591:"PAN",
    598:"PNG", 600:"PRY", 604:"PER", 608:"PHL", 616:"POL", 620:"PRT",
    624:"GNB", 630:"PRI", 634:"QAT", 642:"ROU", 643:"RUS", 646:"RWA",
    682:"SAU", 686:"SEN", 694:"SLE", 703:"SVK", 705:"SVN", 706:"SOM",
    710:"ZAF", 716:"ZWE", 724:"ESP", 728:"SSD", 729:"SDN", 740:"SUR",
    748:"SWZ", 752:"SWE", 756:"CHE", 760:"SYR", 762:"TJK", 764:"THA",
    768:"TGO", 780:"TTO", 788:"TUN", 792:"TUR", 795:"TKM", 800:"UGA",
    804:"UKR", 818:"EGY", 826:"GBR", 834:"TZA", 840:"USA", 858:"URY",
    860:"UZB", 862:"VEN", 887:"YEM", 894:"ZMB",
    # Special territories / disputed
    275:"PSE",  # Palestine
}

# Reverse: ISO_A3 → numeric
ISO3_TO_NUM = {v: k for k, v in NUM_TO_ISO3.items()}

WORLD_RISK = {
    # ── LEVEL 4 — CRITICAL ───────────────────────────────────────────────────
    "PSE": {
        "name": "Palestine (Gaza & West Bank)", "level": 4, "inform_score": 5.0,
        "access": 5, "access_label": "Extreme constraints",
        "crisis": "Active war — Gaza siege, total humanitarian blockade",
        "conflict_type": "International Armed Conflict",
        "pop_at_risk": 2300000, "displaced": 1900000,
        "exit_routes": ["Rafah Crossing (Egypt)", "Kerem Shalom (restricted)"],
        "actors": ["UNRWA", "ICRC", "MSF", "WFP", "WHO"],
        "source": "ACAPS INFORM Dec 2025 · OCHA Gaza 2025"
    },
    "SDN": {
        "name": "Sudan", "level": 4, "inform_score": 4.9,
        "access": 5, "access_label": "Extreme constraints",
        "crisis": "SAF–RSF armed conflict — world's largest displacement crisis 2024",
        "conflict_type": "Non-International Armed Conflict",
        "pop_at_risk": 24000000, "displaced": 8500000,
        "exit_routes": ["Chad (east)", "Egypt (north)", "South Sudan (south)", "Ethiopia (east)"],
        "actors": ["UNHCR", "WFP", "ICRC", "MSF", "IRC"],
        "source": "ACAPS INFORM Dec 2025 · UNHCR Sudan 2025"
    },
    "YEM": {
        "name": "Yemen", "level": 4, "inform_score": 4.8,
        "access": 5, "access_label": "Extreme constraints",
        "crisis": "Ongoing civil war — Houthi control, coalition strikes, Red Sea blockade",
        "conflict_type": "Non-International Armed Conflict (internationalized)",
        "pop_at_risk": 21000000, "displaced": 4500000,
        "exit_routes": ["Oman (east, limited)", "Djibouti (sea route, dangerous)"],
        "actors": ["OCHA", "ICRC", "WFP", "UNHCR", "MSF"],
        "source": "ACAPS INFORM Dec 2025 · OCHA Yemen 2025"
    },
    "AFG": {
        "name": "Afghanistan", "level": 4, "inform_score": 4.7,
        "access": 4, "access_label": "Very high constraints",
        "crisis": "Taliban rule + humanitarian crisis + drought + restrictions on women",
        "conflict_type": "Non-International Armed Conflict",
        "pop_at_risk": 29000000, "displaced": 4600000,
        "exit_routes": ["Iran (west, restricted)", "Pakistan (east, restricted)", "Tajikistan (north, limited)"],
        "actors": ["UNHCR", "WFP", "ICRC", "NRC", "IRC"],
        "source": "ACAPS INFORM Dec 2025 · OCHA Afghanistan 2025"
    },
    "MMR": {
        "name": "Myanmar", "level": 4, "inform_score": 4.7,
        "access": 4, "access_label": "Very high constraints",
        "crisis": "Military coup 2021 + civil war — SAC vs PDF/EAOs across all regions",
        "conflict_type": "Non-International Armed Conflict",
        "pop_at_risk": 18000000, "displaced": 3000000,
        "exit_routes": ["Thailand (east)", "Bangladesh (west, restricted)", "India (northwest)"],
        "actors": ["UNHCR", "ICRC", "MSF", "NRC"],
        "source": "ACAPS INFORM Jan 2025 · UNHCR Myanmar 2025"
    },
    "SYR": {
        "name": "Syria", "level": 4, "inform_score": 4.6,
        "access": 4, "access_label": "Very high constraints",
        "crisis": "Post-Assad transition + ongoing instability + mass displacement legacy",
        "conflict_type": "Non-International Armed Conflict (internationalized)",
        "pop_at_risk": 15000000, "displaced": 7200000,
        "exit_routes": ["Turkey (north)", "Lebanon (west)", "Jordan (south)", "Iraq (east)"],
        "actors": ["UNHCR", "WFP", "ICRC", "MSF", "UN OCHA"],
        "source": "ACAPS INFORM Dec 2025 · UNHCR Syria 2025"
    },
    "HTI": {
        "name": "Haiti", "level": 4, "inform_score": 4.5,
        "access": 3, "access_label": "High constraints",
        "crisis": "Gang control of 85% of Port-au-Prince + state collapse + political vacuum",
        "conflict_type": "Generalized Violence (non-State actors)",
        "pop_at_risk": 5200000, "displaced": 700000,
        "exit_routes": ["Dominican Republic (east)", "Sea routes to Caribbean (dangerous)"],
        "actors": ["OCHA", "WFP", "ICRC", "MSF", "IOM"],
        "source": "ACAPS INFORM Dec 2025 · IOM Haiti 2025"
    },
    "SOM": {
        "name": "Somalia", "level": 4, "inform_score": 4.5,
        "access": 5, "access_label": "Extreme constraints",
        "crisis": "Al-Shabaab insurgency + recurrent drought + famine risk",
        "conflict_type": "Non-International Armed Conflict",
        "pop_at_risk": 7000000, "displaced": 3800000,
        "exit_routes": ["Kenya (south)", "Ethiopia (northwest)", "Djibouti (north)"],
        "actors": ["UNHCR", "WFP", "ICRC", "MSF", "NRC"],
        "source": "ACAPS INFORM Dec 2025 · FSNAU Somalia 2025"
    },
    "UKR": {
        "name": "Ukraine", "level": 4, "inform_score": 4.5,
        "access": 5, "access_label": "Extreme constraints (frontline oblasts)",
        "crisis": "Russian invasion — active frontline warfare in east/south oblasts",
        "conflict_type": "International Armed Conflict",
        "pop_at_risk": 8000000, "displaced": 5600000,
        "exit_routes": ["Poland (west)", "Romania (southwest)", "Hungary (southwest)", "Slovakia (west)"],
        "actors": ["UNHCR", "ICRC", "WFP", "CIVIC", "NRC", "White Angels"],
        "source": "ACAPS INFORM Dec 2025 · CIVIC Ukraine 2025"
    },
    "COD": {
        "name": "DR Congo", "level": 4, "inform_score": 4.5,
        "access": 4, "access_label": "Very high constraints",
        "crisis": "M23 advance on Goma + 120+ armed groups — 7.2M displaced (world record)",
        "conflict_type": "Non-International Armed Conflict (internationalized)",
        "pop_at_risk": 23000000, "displaced": 7200000,
        "exit_routes": ["Uganda (northeast)", "Rwanda (east, contested)", "Republic of Congo (west)"],
        "actors": ["UNHCR", "MONUSCO", "ICRC", "MSF", "NRC"],
        "source": "ACAPS INFORM Dec 2025 · OCHA DRC 2025"
    },

    # ── LEVEL 3 — HIGH ───────────────────────────────────────────────────────
    "ETH": {
        "name": "Ethiopia", "level": 3, "inform_score": 4.2,
        "access": 4, "access_label": "Very high constraints",
        "crisis": "Tigray post-conflict + Amhara conflict + Oromo insurgency + floods",
        "conflict_type": "Non-International Armed Conflict",
        "pop_at_risk": 20000000, "displaced": 4000000,
        "exit_routes": ["Kenya (south)", "Djibouti (east)", "Sudan (west, limited)"],
        "actors": ["UNHCR", "WFP", "ICRC", "MSF", "IRC"],
        "source": "ACAPS INFORM Dec 2025"
    },
    "BFA": {
        "name": "Burkina Faso", "level": 3, "inform_score": 4.2,
        "access": 4, "access_label": "Very high constraints",
        "crisis": "JNIM/GSIM jihadist expansion — 40% of territory outside state control",
        "conflict_type": "Non-International Armed Conflict",
        "pop_at_risk": 5000000, "displaced": 2000000,
        "exit_routes": ["Ghana (south)", "Côte d'Ivoire (south)", "Benin (east)"],
        "actors": ["UNHCR", "WFP", "ICRC", "MSF"],
        "source": "ACAPS INFORM Dec 2025"
    },
    "SSD": {
        "name": "South Sudan", "level": 3, "inform_score": 4.1,
        "access": 4, "access_label": "Very high constraints",
        "crisis": "Post-civil war fragility + seasonal flooding + Sudan refugee influx",
        "conflict_type": "Non-International Armed Conflict (transitional)",
        "pop_at_risk": 9000000, "displaced": 2200000,
        "exit_routes": ["Uganda (south)", "Kenya (southeast)", "Ethiopia (east)"],
        "actors": ["UNHCR", "UNMISS", "WFP", "ICRC", "MSF"],
        "source": "ACAPS INFORM Dec 2025"
    },
    "NGA": {
        "name": "Nigeria", "level": 3, "inform_score": 4.0,
        "access": 4, "access_label": "Very high constraints",
        "crisis": "Boko Haram/ISWAP in NE + Farmer-Herder violence + banditry NW",
        "conflict_type": "Non-International Armed Conflict",
        "pop_at_risk": 9000000, "displaced": 3700000,
        "exit_routes": ["Niger (north)", "Cameroon (east)", "Chad (northeast)", "Benin (west)"],
        "actors": ["UNHCR", "WFP", "ICRC", "MSF", "NRC"],
        "source": "ACAPS INFORM Dec 2025"
    },
    "LBN": {
        "name": "Lebanon", "level": 3, "inform_score": 4.0,
        "access": 4, "access_label": "Very high constraints",
        "crisis": "Israeli strikes (post-Oct 2023) + state collapse + Syrian refugee burden",
        "conflict_type": "International Armed Conflict (spillover)",
        "pop_at_risk": 4000000, "displaced": 1200000,
        "exit_routes": ["Syria (east, restricted)", "Sea route to Cyprus (limited)"],
        "actors": ["UNHCR", "ICRC", "WFP", "MSF", "LAF"],
        "source": "ACAPS INFORM Dec 2025"
    },
    "MLI": {
        "name": "Mali", "level": 3, "inform_score": 4.0,
        "access": 4, "access_label": "Very high constraints",
        "crisis": "JNIM jihadist control + military junta expulsion of MINUSMA/France",
        "conflict_type": "Non-International Armed Conflict",
        "pop_at_risk": 4000000, "displaced": 375000,
        "exit_routes": ["Mauritania (west)", "Senegal (west)", "Guinea (south)", "Burkina Faso (east, also crisis)"],
        "actors": ["UNHCR", "WFP", "ICRC", "MSF"],
        "source": "ACAPS INFORM Dec 2025"
    },
    "TCD": {
        "name": "Chad", "level": 3, "inform_score": 3.8,
        "access": 3, "access_label": "High constraints",
        "crisis": "Sudan refugee crisis (700K+) + Sahel jihadist spillover + Lake Chad",
        "conflict_type": "Non-International Armed Conflict (spillover)",
        "pop_at_risk": 7000000, "displaced": 600000,
        "exit_routes": ["Niger (west)", "Nigeria (south)", "Cameroon (south)"],
        "actors": ["UNHCR", "WFP", "ICRC", "MSF"],
        "source": "ACAPS INFORM Dec 2025"
    },
    "CAF": {
        "name": "Central African Republic", "level": 3, "inform_score": 3.8,
        "access": 3, "access_label": "High constraints",
        "crisis": "Wagner-backed government vs multiple armed groups (CPC, FPRC)",
        "conflict_type": "Non-International Armed Conflict",
        "pop_at_risk": 2500000, "displaced": 880000,
        "exit_routes": ["Cameroon (west)", "Republic of Congo (south)", "Chad (north)"],
        "actors": ["UNHCR", "MINUSCA", "WFP", "ICRC", "MSF"],
        "source": "ACAPS INFORM Dec 2025"
    },
    "NER": {
        "name": "Niger", "level": 3, "inform_score": 3.8,
        "access": 3, "access_label": "High constraints",
        "crisis": "Post-coup instability + Sahel jihadist spillover from Mali/Burkina",
        "conflict_type": "Non-International Armed Conflict + Political Crisis",
        "pop_at_risk": 4000000, "displaced": 330000,
        "exit_routes": ["Nigeria (south)", "Benin (south)", "Togo (south)"],
        "actors": ["UNHCR", "WFP", "ICRC", "MSF"],
        "source": "ACAPS INFORM Dec 2025"
    },
    "LBY": {
        "name": "Libya", "level": 3, "inform_score": 3.7,
        "access": 3, "access_label": "High constraints",
        "crisis": "Divided government + militia control + migration hub + flood aftermath",
        "conflict_type": "Non-International Armed Conflict",
        "pop_at_risk": 3000000, "displaced": 135000,
        "exit_routes": ["Tunisia (west)", "Egypt (east)", "Niger (south, dangerous)"],
        "actors": ["UNHCR", "IOM", "ICRC", "MSF"],
        "source": "ACAPS INFORM Dec 2025"
    },
    "VEN": {
        "name": "Venezuela", "level": 3, "inform_score": 3.7,
        "access": 3, "access_label": "High constraints",
        "crisis": "Political/economic collapse + 7.7M migrants/refugees + gang violence",
        "conflict_type": "Complex Emergency (political + economic)",
        "pop_at_risk": 20000000, "displaced": 7700000,
        "exit_routes": ["Colombia (west)", "Brazil (south)", "Trinidad (sea route)", "Guyana (east)"],
        "actors": ["UNHCR", "WFP", "ICRC", "NRC", "R4V"],
        "source": "ACAPS INFORM Dec 2025"
    },
    "IRQ": {
        "name": "Iraq", "level": 3, "inform_score": 3.6,
        "access": 3, "access_label": "High constraints",
        "crisis": "Post-ISIS instability + PMF/Iranian proxy activity + IDP returns",
        "conflict_type": "Non-International Armed Conflict (residual)",
        "pop_at_risk": 7000000, "displaced": 1200000,
        "exit_routes": ["Turkey (north)", "Jordan (west)", "Iran (east)"],
        "actors": ["UNHCR", "IOM", "WFP", "ICRC"],
        "source": "ACAPS INFORM Dec 2025"
    },
    "MOZ": {
        "name": "Mozambique", "level": 3, "inform_score": 3.6,
        "access": 3, "access_label": "High constraints",
        "crisis": "Cabo Delgado insurgency (IS affiliate) + electoral violence 2024",
        "conflict_type": "Non-International Armed Conflict",
        "pop_at_risk": 4000000, "displaced": 850000,
        "exit_routes": ["Tanzania (north)", "Malawi (west)", "Zimbabwe (south)"],
        "actors": ["UNHCR", "WFP", "ICRC", "MSF", "RWZI"],
        "source": "ACAPS INFORM Dec 2025"
    },
    "CMR": {
        "name": "Cameroon", "level": 3, "inform_score": 3.6,
        "access": 3, "access_label": "High constraints",
        "crisis": "Anglophone separatist conflict (NW/SW) + Boko Haram (Far North)",
        "conflict_type": "Non-International Armed Conflict",
        "pop_at_risk": 3500000, "displaced": 1000000,
        "exit_routes": ["Nigeria (west)", "Central African Republic (east)", "Chad (north, also in crisis)"],
        "actors": ["UNHCR", "WFP", "ICRC", "MSF"],
        "source": "ACAPS INFORM Dec 2025"
    },
    "PAK": {
        "name": "Pakistan", "level": 3, "inform_score": 3.5,
        "access": 3, "access_label": "High constraints",
        "crisis": "TTP attacks (KPK/FATA) + mega-flood displacement + Afghan refugee burden",
        "conflict_type": "Non-International Armed Conflict + Climate Emergency",
        "pop_at_risk": 10000000, "displaced": 1000000,
        "exit_routes": ["Afghanistan (northwest, also crisis)", "Iran (west)", "India (east, restricted)"],
        "actors": ["UNHCR", "WFP", "ICRC", "IOM"],
        "source": "ACAPS INFORM Dec 2025"
    },
    "BGD": {
        "name": "Bangladesh", "level": 3, "inform_score": 3.5,
        "access": 3, "access_label": "High constraints",
        "crisis": "Rohingya refugee crisis (Cox's Bazar) + political instability 2024",
        "conflict_type": "Humanitarian Emergency + Political Crisis",
        "pop_at_risk": 3000000, "displaced": 1200000,
        "exit_routes": ["India (north/west, restricted for Rohingya)"],
        "actors": ["UNHCR", "WFP", "IOM", "MSF", "BRAC"],
        "source": "ACAPS INFORM Dec 2025"
    },

    # ── LEVEL 2 — MODERATE ──────────────────────────────────────────────────
    "COL": {"name":"Colombia","level":2,"inform_score":3.2,"access":3,"access_label":"High constraints","crisis":"FARC dissidents + ELN + narco-violence + 6.8M IDPs legacy","conflict_type":"Non-International Armed Conflict","pop_at_risk":8000000,"displaced":6800000,"exit_routes":["Ecuador (south)","Venezuela (east)","Panama (north)"],"actors":["UNHCR","ICRC","WFP","NRC"],"source":"ACAPS INFORM Dec 2025"},
    "ZWE": {"name":"Zimbabwe","level":2,"inform_score":3.0,"access":2,"access_label":"Moderate constraints","crisis":"Economic collapse + El Niño food insecurity + political repression","conflict_type":"Complex Emergency","pop_at_risk":6000000,"displaced":200000,"exit_routes":["South Africa (south)","Botswana (west)","Zambia (north)"],"actors":["UNHCR","WFP","UNICEF"],"source":"ACAPS INFORM Dec 2025"},
    "KEN": {"name":"Kenya","level":2,"inform_score":2.8,"access":2,"access_label":"Moderate constraints","crisis":"Al-Shabaab cross-border raids + drought + post-election unrest 2024","conflict_type":"Spillover + Climate Emergency","pop_at_risk":3000000,"displaced":420000,"exit_routes":["Tanzania (south)","Uganda (west)","Ethiopia (north)"],"actors":["UNHCR","WFP","ICRC"],"source":"ACAPS INFORM Dec 2025"},
    "EGY": {"name":"Egypt","level":2,"inform_score":2.8,"access":2,"access_label":"Moderate constraints","crisis":"Sinai insurgency + Gaza spillover + economic stress + migration pressure","conflict_type":"Low-intensity conflict + Humanitarian pressure","pop_at_risk":2000000,"displaced":250000,"exit_routes":["Libya (west)","Sudan (south)","Jordan (northeast)"],"actors":["UNHCR","IOM","WFP"],"source":"ACAPS INFORM Dec 2025"},
    "PHL": {"name":"Philippines","level":2,"inform_score":2.8,"access":2,"access_label":"Moderate constraints","crisis":"Mindanao conflict (BIFF/NPA) + typhoon displacement cycles","conflict_type":"Non-International Armed Conflict + Natural Disasters","pop_at_risk":3000000,"displaced":600000,"exit_routes":["Malaysia (Mindanao south)"],"actors":["UNHCR","WFP","ICRC","NRC"],"source":"ACAPS INFORM Dec 2025"},
    "ISR": {"name":"Israel","level":2,"inform_score":3.0,"access":2,"access_label":"Moderate constraints","crisis":"Active conflict with Gaza + Hezbollah + northern displacement","conflict_type":"International Armed Conflict","pop_at_risk":500000,"displaced":80000,"exit_routes":["Jordan (east)","Egypt (south)"],"actors":["MDA","ICRC"],"source":"ACAPS INFORM Dec 2025"},
    "HND": {"name":"Honduras","level":2,"inform_score":2.8,"access":2,"access_label":"Moderate constraints","crisis":"Gang violence (MS-13/Barrio 18) + poverty + forced displacement + migration","conflict_type":"Generalized Violence","pop_at_risk":3000000,"displaced":250000,"exit_routes":["Guatemala (north)","El Salvador (east)","Mexico (north)"],"actors":["UNHCR","IOM","NRC"],"source":"ACAPS INFORM Dec 2025"},
    "GTM": {"name":"Guatemala","level":2,"inform_score":2.6,"access":2,"access_label":"Moderate constraints","crisis":"Gang violence + rural poverty + food insecurity in dry corridor","conflict_type":"Generalized Violence","pop_at_risk":3000000,"displaced":280000,"exit_routes":["Mexico (north)","Belize (east)"],"actors":["UNHCR","WFP","NRC"],"source":"ACAPS INFORM Dec 2025"},
    "UGA": {"name":"Uganda","level":2,"inform_score":2.7,"access":2,"access_label":"Moderate constraints","crisis":"DRC/South Sudan refugee hosting + ADF attacks in east","conflict_type":"Refugee Emergency + Spillover","pop_at_risk":2000000,"displaced":500000,"exit_routes":["Kenya (east)","Tanzania (south)"],"actors":["UNHCR","WFP","ICRC"],"source":"ACAPS INFORM Dec 2025"},
    "PNG": {"name":"Papua New Guinea","level":2,"inform_score":2.7,"access":2,"access_label":"Moderate constraints","crisis":"Highlands tribal conflict + Bougainville + natural disasters","conflict_type":"Non-International Armed Conflict","pop_at_risk":2000000,"displaced":180000,"exit_routes":["Australia (sea, limited)"],"actors":["UNHCR","WFP"],"source":"ACAPS INFORM Dec 2025"},
    "IRN": {"name":"Iran","level":2,"inform_score":2.7,"access":2,"access_label":"Moderate constraints","crisis":"Political repression + sanctions + Afghan/Iraqi refugee burden + Balochistan unrest","conflict_type":"Complex Emergency","pop_at_risk":2000000,"displaced":150000,"exit_routes":["Turkey (west)","Armenia (north)"],"actors":["UNHCR","ICRC"],"source":"ACAPS INFORM Dec 2025"},
    "GIN": {"name":"Guinea","level":2,"inform_score":2.5,"access":2,"access_label":"Moderate constraints","crisis":"Military junta + political repression + Fouta Djallon tensions","conflict_type":"Political Crisis","pop_at_risk":500000,"displaced":0,"exit_routes":["Senegal (north)","Sierra Leone (south)","Guinea-Bissau (west)"],"actors":["UNHCR","WFP"],"source":"ACAPS INFORM Dec 2025"},

    # ── LEVEL 1 — LOW ───────────────────────────────────────────────────────
    "TUR": {"name":"Turkey","level":1,"inform_score":2.2,"access":1,"access_label":"Low constraints","crisis":"4M+ Syrian/Afghan refugees — no active conflict on territory","conflict_type":"Refugee Emergency","pop_at_risk":500000,"displaced":100000,"exit_routes":["Greece (west)","Bulgaria (north)"],"actors":["UNHCR","WFP","IOM"],"source":"ACAPS INFORM Dec 2025"},
    "JOR": {"name":"Jordan","level":1,"inform_score":2.0,"access":1,"access_label":"Low constraints","crisis":"Syrian/Iraqi refugee burden (750K) + economic stress + Gaza proximity","conflict_type":"Refugee Emergency","pop_at_risk":300000,"displaced":50000,"exit_routes":["Iraq (east)","Saudi Arabia (south)"],"actors":["UNHCR","WFP","ICRC"],"source":"ACAPS INFORM Dec 2025"},
    "MEX": {"name":"Mexico","level":1,"inform_score":2.3,"access":1,"access_label":"Low constraints","crisis":"Cartel violence + forced displacement in Guerrero/Sinaloa/Chiapas","conflict_type":"Generalized Violence","pop_at_risk":2000000,"displaced":380000,"exit_routes":["USA (north)","Guatemala (south)"],"actors":["UNHCR","ICRC","IOM"],"source":"ACAPS INFORM Dec 2025"},
    "ECU": {"name":"Ecuador","level":1,"inform_score":2.1,"access":1,"access_label":"Low constraints","crisis":"Narco violence escalation (Los Choneros) + Venezuelan migration","conflict_type":"Generalized Violence","pop_at_risk":1000000,"displaced":100000,"exit_routes":["Colombia (north)","Peru (south)"],"actors":["UNHCR","IOM"],"source":"ACAPS INFORM Dec 2025"},
    "PER": {"name":"Peru","level":1,"inform_score":2.0,"access":1,"access_label":"Low constraints","crisis":"Political instability + Shining Path remnants + Venezuelan migration","conflict_type":"Low-intensity conflict","pop_at_risk":1000000,"displaced":100000,"exit_routes":["Ecuador (north)","Bolivia (east)","Chile (south)"],"actors":["UNHCR","IOM"],"source":"ACAPS INFORM Dec 2025"},
    "RUS": {"name":"Russia","level":1,"inform_score":2.0,"access":2,"access_label":"Moderate constraints","crisis":"Aggressor state (Ukraine war) + internal displacement in border areas","conflict_type":"International Armed Conflict (originator)","pop_at_risk":500000,"displaced":100000,"exit_routes":["Finland (north)","Estonia (west)","Georgia (south)"],"actors":["UNHCR"],"source":"ACAPS INFORM Dec 2025"},
    "IND": {"name":"India","level":1,"inform_score":1.8,"access":1,"access_label":"Low constraints","crisis":"Manipur conflict + Naxalite insurgency + climate disasters + Myanmar border","conflict_type":"Non-International Armed Conflict (subnational)","pop_at_risk":3000000,"displaced":640000,"exit_routes":["Bangladesh (east)","Nepal (north)","Myanmar (east, also crisis)"],"actors":["UNHCR","WFP","ICRC"],"source":"ACAPS INFORM Dec 2025"},
    "IDN": {"name":"Indonesia","level":1,"inform_score":2.0,"access":1,"access_label":"Low constraints","crisis":"West Papua separatist conflict + natural disaster displacement","conflict_type":"Non-International Armed Conflict (subnational)","pop_at_risk":1000000,"displaced":200000,"exit_routes":["Papua New Guinea (east)"],"actors":["UNHCR","WFP"],"source":"ACAPS INFORM Dec 2025"},
    "ZAF": {"name":"South Africa","level":1,"inform_score":1.5,"access":1,"access_label":"Low constraints","crisis":"Gang violence + migration crisis + KwaZulu-Natal unrest","conflict_type":"Generalized Violence","pop_at_risk":1000000,"displaced":100000,"exit_routes":["Botswana (north)","Mozambique (north)"],"actors":["UNHCR","IOM"],"source":"ACAPS INFORM Dec 2025"},
    "MRT": {"name":"Mauritania","level":1,"inform_score":2.0,"access":1,"access_label":"Low constraints","crisis":"Sahel spillover threat + food insecurity + Malian refugee influx","conflict_type":"Refugee Emergency + Spillover risk","pop_at_risk":800000,"displaced":80000,"exit_routes":["Senegal (south)","Mali (east, crisis)"],"actors":["UNHCR","WFP"],"source":"ACAPS INFORM Dec 2025"},
    "SAU": {"name":"Saudi Arabia","level":1,"inform_score":1.5,"access":1,"access_label":"Low constraints","crisis":"Yemen war participation + Houthi drone/missile attacks on border areas","conflict_type":"International Armed Conflict (participant)","pop_at_risk":500000,"displaced":50000,"exit_routes":["Oman (east)","Jordan (north)"],"actors":["ICRC","Saudi Red Crescent"],"source":"ACAPS INFORM Dec 2025"},
    "RWA": {"name":"Rwanda","level":1,"inform_score":1.8,"access":1,"access_label":"Low constraints","crisis":"DRC border tensions + M23 support allegations + Burundian refugee hosting","conflict_type":"Regional tension","pop_at_risk":500000,"displaced":80000,"exit_routes":["Uganda (north)","Tanzania (east)","Burundi (south)"],"actors":["UNHCR","WFP"],"source":"ACAPS INFORM Dec 2025"},

    # ── LEVEL 0 — BASELINE ──────────────────────────────────────────────────
    "USA": {"name":"United States","level":0,"inform_score":0.5,"access":0,"access_label":"No constraints","crisis":"No active humanitarian crisis","conflict_type":"None","pop_at_risk":0,"displaced":0,"exit_routes":[],"actors":[],"source":"No crisis"},
    "GBR": {"name":"United Kingdom","level":0,"inform_score":0.3,"access":0,"access_label":"No constraints","crisis":"No active humanitarian crisis","conflict_type":"None","pop_at_risk":0,"displaced":0,"exit_routes":[],"actors":[],"source":"No crisis"},
    "DEU": {"name":"Germany","level":0,"inform_score":0.3,"access":0,"access_label":"No constraints","crisis":"No active humanitarian crisis — major refugee host","conflict_type":"None","pop_at_risk":0,"displaced":0,"exit_routes":[],"actors":[],"source":"No crisis"},
    "FRA": {"name":"France","level":0,"inform_score":0.4,"access":0,"access_label":"No constraints","crisis":"No active humanitarian crisis","conflict_type":"None","pop_at_risk":0,"displaced":0,"exit_routes":[],"actors":[],"source":"No crisis"},
    "BRA": {"name":"Brazil","level":0,"inform_score":1.2,"access":0,"access_label":"No constraints","crisis":"No armed conflict — climate/indigenous issues","conflict_type":"None","pop_at_risk":0,"displaced":0,"exit_routes":[],"actors":[],"source":"No crisis"},
    "ARG": {"name":"Argentina","level":0,"inform_score":0.8,"access":0,"access_label":"No constraints","crisis":"Economic crisis — no active conflict","conflict_type":"None","pop_at_risk":0,"displaced":0,"exit_routes":[],"actors":[],"source":"No crisis"},
    "CHL": {"name":"Chile","level":0,"inform_score":0.7,"access":0,"access_label":"No constraints","crisis":"No active humanitarian crisis","conflict_type":"None","pop_at_risk":0,"displaced":0,"exit_routes":[],"actors":[],"source":"No crisis"},
    "AUS": {"name":"Australia","level":0,"inform_score":0.3,"access":0,"access_label":"No constraints","crisis":"No active humanitarian crisis","conflict_type":"None","pop_at_risk":0,"displaced":0,"exit_routes":[],"actors":[],"source":"No crisis"},
    "CAN": {"name":"Canada","level":0,"inform_score":0.3,"access":0,"access_label":"No constraints","crisis":"No active humanitarian crisis","conflict_type":"None","pop_at_risk":0,"displaced":0,"exit_routes":[],"actors":[],"source":"No crisis"},
    "JPN": {"name":"Japan","level":0,"inform_score":0.4,"access":0,"access_label":"No constraints","crisis":"No active humanitarian crisis","conflict_type":"None","pop_at_risk":0,"displaced":0,"exit_routes":[],"actors":[],"source":"No crisis"},
    "CHN": {"name":"China","level":0,"inform_score":0.8,"access":1,"access_label":"Low constraints","crisis":"Xinjiang + Tibet — access restrictions","conflict_type":"None","pop_at_risk":0,"displaced":0,"exit_routes":[],"actors":[],"source":"No crisis"},
    "NLD": {"name":"Netherlands","level":0,"inform_score":0.3,"access":0,"access_label":"No constraints","crisis":"No active humanitarian crisis","conflict_type":"None","pop_at_risk":0,"displaced":0,"exit_routes":[],"actors":[],"source":"No crisis"},
    "ITA": {"name":"Italy","level":0,"inform_score":0.4,"access":0,"access_label":"No constraints","crisis":"No active humanitarian crisis — migration arrival point","conflict_type":"None","pop_at_risk":0,"displaced":0,"exit_routes":[],"actors":[],"source":"No crisis"},
    "ESP": {"name":"Spain","level":0,"inform_score":0.3,"access":0,"access_label":"No constraints","crisis":"No active humanitarian crisis","conflict_type":"None","pop_at_risk":0,"displaced":0,"exit_routes":[],"actors":[],"source":"No crisis"},
    "POL": {"name":"Poland","level":0,"inform_score":0.5,"access":0,"access_label":"No constraints","crisis":"No active humanitarian crisis — Ukrainian refugee host","conflict_type":"None","pop_at_risk":0,"displaced":0,"exit_routes":[],"actors":[],"source":"No crisis"},
    "KAZ": {"name":"Kazakhstan","level":0,"inform_score":0.5,"access":0,"access_label":"No constraints","crisis":"No active humanitarian crisis","conflict_type":"None","pop_at_risk":0,"displaced":0,"exit_routes":[],"actors":[],"source":"No crisis"},
}

# ─── Live ACAPS data cache ───────────────────────────────────────────────────

_LIVE_CACHE: Dict = {"data": None, "ts": 0.0}
_CACHE_TTL: float = 86400.0   # 24 hours


def _score_to_level(score: float) -> int:
    """Map INFORM Severity score (0-5 scale) to ERCF level 0-4."""
    if score >= 4.5: return 4
    if score >= 3.5: return 3
    if score >= 2.5: return 2
    if score >= 1.5: return 1
    return 0


def _refresh_live_data() -> Optional[Dict]:
    """Fetch live INFORM data from ACAPS API; returns ISO3-keyed dict or None.

    Results are cached in memory for _CACHE_TTL seconds.  When the API key is
    not configured or the request fails, the previous cached result is returned
    (stale-on-error behaviour) so the app degrades gracefully.
    """
    global _LIVE_CACHE
    now = time.time()

    # Return in-memory cache if still fresh
    if _LIVE_CACHE["data"] is not None and (now - _LIVE_CACHE["ts"]) < _CACHE_TTL:
        return _LIVE_CACHE["data"]

    try:
        from acaps_data import fetch_inform_severity
        raw = fetch_inform_severity()
        if not raw:               # empty list = API error / timeout
            return _LIVE_CACHE["data"]   # stale fallback

        merged: Dict = {}
        for item in raw:
            iso3 = (item.get("iso3") or "").upper().strip()
            if not iso3 or len(iso3) != 3:
                continue
            try:
                score = float(item.get("inform_severity_score") or 0)
            except (TypeError, ValueError):
                score = 0.0

            merged[iso3] = {
                "inform_score_live": round(score, 2),
                # Field names vary slightly across ACAPS API versions
                "crisis_name":  item.get("crisis_name") or item.get("name", ""),
                "affected_pop": item.get("affected_population") or item.get("people_affected"),
                "last_update":  item.get("last_update") or item.get("date", ""),
                "crisis_type":  item.get("crisis_type", ""),
            }

        _LIVE_CACHE = {"data": merged, "ts": now}
        return merged

    except Exception:
        return _LIVE_CACHE.get("data")   # stale fallback on any error


# ─── Public getters ──────────────────────────────────────────────────────────

def get_risk_by_iso3(iso3: str) -> Dict:
    """Return risk entry (static + live overlay) or a default Level-0 stub."""
    iso3 = iso3.upper()
    base = dict(WORLD_RISK.get(iso3, {
        "name": iso3, "level": 0, "inform_score": 0.0,
        "access": 0, "access_label": "No data",
        "crisis": "No ACAPS data available",
        "conflict_type": "Unknown",
        "pop_at_risk": 0, "displaced": 0,
        "exit_routes": [], "actors": [],
        "source": "No data"
    }))

    live = _refresh_live_data()
    if live and iso3 in live:
        ld = live[iso3]
        base["inform_score_live"] = ld["inform_score_live"]
        base["acaps_live"]        = ld
        # Overlay level only when live score differs from static
        live_lvl = _score_to_level(ld["inform_score_live"])
        if live_lvl != base.get("level", 0):
            base["level_static"] = base["level"]
            base["level"]        = live_lvl

    return base


def get_all_risk_levels() -> Dict:
    """Return flat ISO3 → {level, name, inform_score, …} dict for the choropleth.

    Live ACAPS scores overlay static values when available.
    """
    live = _refresh_live_data()
    result: Dict = {}

    for iso, d in WORLD_RISK.items():
        entry = {
            "level":        d["level"],
            "name":         d["name"],
            "inform_score": d["inform_score"],
            "access":       d.get("access", 0),
            "crisis":       d["crisis"],
            "pop_at_risk":  d.get("pop_at_risk", 0),
            "displaced":    d.get("displaced", 0),
        }
        if live and iso in live:
            ld = live[iso]
            entry["inform_score_live"] = ld["inform_score_live"]
            live_lvl = _score_to_level(ld["inform_score_live"])
            if live_lvl != entry["level"]:
                entry["level_updated"] = True
                entry["level"]         = live_lvl
        result[iso] = entry

    return result
