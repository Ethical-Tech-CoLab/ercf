"""
Demographic vulnerability estimates for ERCF conflict-affected contexts.
Sources: UNICEF State of the World's Children 2023; UN DESA World Population Prospects 2022;
         WHO World Report on Disability 2011 (15% global estimate retained, conflict zones higher).

vulnerable_estimate = pct_under5 + pct_over60 + (pct_disabled × 0.5)
The 0.5 weight on disability avoids double-counting with elderly (already in over60)
and reflects that roughly half of disabilities impose mobility/medical constraints
relevant to evacuation planning.

All figures are national-level estimates and should be adjusted based on local assessment,
displacement context, and available field data.
"""

DEMOGRAPHIC_DATA = {
    "syria": {
        "pct_under5":         9.0,
        "pct_over60":         5.0,
        "pct_disabled":      15.0,
        "vulnerable_estimate": 21.5,
        "source": "UNICEF/UN DESA 2023 (Syria national demographics; conflict-displaced population has elevated child proportion)",
        "note": "Conflict displacement has concentrated younger populations; actual field estimates may vary 25–40%.",
    },
    "ukraine": {
        "pct_under5":         5.0,
        "pct_over60":        24.0,
        "pct_disabled":      15.0,
        "vulnerable_estimate": 36.5,
        "source": "UNICEF/UN DESA 2023 (Ukraine national demographics)",
        "note": "Elderly proportion is high; mobile adults disproportionately evacuated early — stay-behind population likely older.",
    },
    "sudan": {
        "pct_under5":        14.0,
        "pct_over60":         4.0,
        "pct_disabled":      15.0,
        "vulnerable_estimate": 25.5,
        "source": "UNICEF/UN DESA 2023 (Sudan national demographics)",
        "note": "",
    },
    "palestine": {
        "pct_under5":        10.0,
        "pct_over60":         4.5,
        "pct_disabled":      15.0,
        "vulnerable_estimate": 22.0,
        "source": "UNICEF/UN DESA 2023 (Gaza Strip demographics; PCBS 2023)",
        "note": "Gaza has a young population; blockade conditions elevate disability burden.",
    },
    "gaza": {
        "pct_under5":        10.0,
        "pct_over60":         4.5,
        "pct_disabled":      15.0,
        "vulnerable_estimate": 22.0,
        "source": "UNICEF/UN DESA 2023 (Gaza Strip; PCBS 2023)",
        "note": "Gaza has a young population; blockade conditions elevate disability burden.",
    },
    "iraq": {
        "pct_under5":         9.0,
        "pct_over60":         5.0,
        "pct_disabled":      15.0,
        "vulnerable_estimate": 21.5,
        "source": "UNICEF/UN DESA 2023 (Iraq national demographics)",
        "note": "",
    },
    "afghanistan": {
        "pct_under5":        14.5,
        "pct_over60":         3.5,
        "pct_disabled":      15.0,
        "vulnerable_estimate": 25.5,
        "source": "UNICEF/UN DESA 2023 (Afghanistan; high child proportion)",
        "note": "Very young population; conflict-induced disability likely higher than global 15% estimate.",
    },
    "drc": {
        "pct_under5":        16.0,
        "pct_over60":         3.5,
        "pct_disabled":      15.0,
        "vulnerable_estimate": 27.0,
        "source": "UNICEF/UN DESA 2023 (DRC national demographics)",
        "note": "",
    },
    "yemen": {
        "pct_under5":        12.5,
        "pct_over60":         3.5,
        "pct_disabled":      15.0,
        "vulnerable_estimate": 23.5,
        "source": "UNICEF/UN DESA 2023 (Yemen national demographics)",
        "note": "Famine and healthcare collapse elevate effective vulnerability beyond demographic baseline.",
    },
    "somalia": {
        "pct_under5":        16.5,
        "pct_over60":         3.0,
        "pct_disabled":      15.0,
        "vulnerable_estimate": 27.0,
        "source": "UNICEF/UN DESA 2023 (Somalia national demographics)",
        "note": "",
    },
    "ethiopia": {
        "pct_under5":        13.5,
        "pct_over60":         4.0,
        "pct_disabled":      15.0,
        "vulnerable_estimate": 25.0,
        "source": "UNICEF/UN DESA 2023 (Ethiopia national demographics)",
        "note": "",
    },
    "libya": {
        "pct_under5":         8.0,
        "pct_over60":         6.0,
        "pct_disabled":      15.0,
        "vulnerable_estimate": 21.5,
        "source": "UNICEF/UN DESA 2023 (Libya national demographics)",
        "note": "",
    },
    "myanmar": {
        "pct_under5":         8.0,
        "pct_over60":         8.0,
        "pct_disabled":      15.0,
        "vulnerable_estimate": 23.5,
        "source": "UNICEF/UN DESA 2023 (Myanmar national demographics)",
        "note": "",
    },
    "mali": {
        "pct_under5":        17.0,
        "pct_over60":         3.5,
        "pct_disabled":      15.0,
        "vulnerable_estimate": 28.0,
        "source": "UNICEF/UN DESA 2023 (Mali national demographics)",
        "note": "",
    },
    "car": {
        "pct_under5":        16.5,
        "pct_over60":         4.0,
        "pct_disabled":      15.0,
        "vulnerable_estimate": 28.0,
        "source": "UNICEF/UN DESA 2023 (Central African Republic)",
        "note": "",
    },
    "central african republic": {
        "pct_under5":        16.5,
        "pct_over60":         4.0,
        "pct_disabled":      15.0,
        "vulnerable_estimate": 28.0,
        "source": "UNICEF/UN DESA 2023 (Central African Republic)",
        "note": "",
    },
    "south sudan": {
        "pct_under5":        17.0,
        "pct_over60":         3.0,
        "pct_disabled":      15.0,
        "vulnerable_estimate": 27.5,
        "source": "UNICEF/UN DESA 2023 (South Sudan national demographics)",
        "note": "Youngest population in dataset; protracted displacement elevates effective vulnerability.",
    },
    "nigeria": {
        "pct_under5":        15.0,
        "pct_over60":         3.5,
        "pct_disabled":      15.0,
        "vulnerable_estimate": 26.0,
        "source": "UNICEF/UN DESA 2023 (Nigeria national demographics; Borno State may differ)",
        "note": "",
    },
    "colombia": {
        "pct_under5":         7.0,
        "pct_over60":        12.0,
        "pct_disabled":      15.0,
        "vulnerable_estimate": 26.5,
        "source": "UNICEF/UN DESA 2023 (Colombia national demographics)",
        "note": "",
    },
    "haiti": {
        "pct_under5":        12.0,
        "pct_over60":         5.5,
        "pct_disabled":      15.0,
        "vulnerable_estimate": 25.0,
        "source": "UNICEF/UN DESA 2023 (Haiti national demographics)",
        "note": "",
    },
    "myanmar (burma)": {
        "pct_under5":         8.0,
        "pct_over60":         8.0,
        "pct_disabled":      15.0,
        "vulnerable_estimate": 23.5,
        "source": "UNICEF/UN DESA 2023 (Myanmar national demographics)",
        "note": "",
    },
}

# Alias map for common name variations
COUNTRY_ALIASES = {
    "syrian arab republic": "syria",
    "syr": "syria",
    "ukr": "ukraine",
    "sdn": "sudan",
    "pse": "palestine",
    "irq": "iraq",
    "afg": "afghanistan",
    "cod": "drc",
    "democratic republic of the congo": "drc",
    "dr congo": "drc",
    "yem": "yemen",
    "som": "somalia",
    "eth": "ethiopia",
    "lby": "libya",
    "mmr": "myanmar",
    "mlf": "mali",
    "caf": "car",
    "ssd": "south sudan",
    "nga": "nigeria",
    "col": "colombia",
    "hti": "haiti",
    "occupied palestinian territory": "palestine",
    "opt": "palestine",
}


def get_demographics(country_name: str):
    """
    Return demographic vulnerability data for a given country name or alias.
    Returns None if country not in dataset.
    """
    key = country_name.lower().strip()
    key = COUNTRY_ALIASES.get(key, key)
    return DEMOGRAPHIC_DATA.get(key)
