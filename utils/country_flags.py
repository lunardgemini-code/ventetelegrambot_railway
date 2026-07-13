"""Country flag helpers for national football teams."""

from __future__ import annotations

import re
import unicodedata


def _normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", without_accents.casefold()).strip()


_COUNTRY_ALIAS_GROUPS = {
    "AE": ("united arab emirates", "uae"),
    "AL": ("albania",),
    "AO": ("angola",),
    "AR": ("argentina",),
    "AT": ("austria",),
    "AU": ("australia",),
    "AZ": ("azerbaijan",),
    "BA": ("bosnia and herzegovina", "bosnia herzegovina"),
    "BE": ("belgium",),
    "BF": ("burkina faso",),
    "BG": ("bulgaria",),
    "BH": ("bahrain",),
    "BJ": ("benin",),
    "BO": ("bolivia",),
    "BR": ("brazil",),
    "BW": ("botswana",),
    "BY": ("belarus",),
    "CA": ("canada",),
    "CD": ("dr congo", "congo dr", "democratic republic of the congo"),
    "CF": ("central african republic",),
    "CG": ("congo", "republic of the congo"),
    "CH": ("switzerland",),
    "CI": ("ivory coast", "cote d ivoire"),
    "CL": ("chile",),
    "CM": ("cameroon",),
    "CN": ("china", "china pr"),
    "CO": ("colombia",),
    "CR": ("costa rica",),
    "CU": ("cuba",),
    "CV": ("cape verde", "cabo verde"),
    "CW": ("curacao",),
    "CY": ("cyprus",),
    "CZ": ("czechia", "czech republic"),
    "DE": ("germany",),
    "DK": ("denmark",),
    "DO": ("dominican republic",),
    "DZ": ("algeria",),
    "EC": ("ecuador",),
    "EE": ("estonia",),
    "EG": ("egypt",),
    "ES": ("spain", "espana"),
    "ET": ("ethiopia",),
    "FI": ("finland",),
    "FJ": ("fiji",),
    "FR": ("france",),
    "GA": ("gabon",),
    "GB": ("england", "scotland", "wales", "northern ireland", "united kingdom"),
    "GE": ("georgia",),
    "GH": ("ghana",),
    "GM": ("gambia", "the gambia"),
    "GN": ("guinea",),
    "GQ": ("equatorial guinea",),
    "GR": ("greece",),
    "GT": ("guatemala",),
    "GW": ("guinea bissau",),
    "HN": ("honduras",),
    "HR": ("croatia",),
    "HT": ("haiti",),
    "HU": ("hungary",),
    "ID": ("indonesia",),
    "IE": ("ireland", "republic of ireland"),
    "IL": ("israel",),
    "IN": ("india",),
    "IQ": ("iraq",),
    "IR": ("iran", "iran islamic republic"),
    "IS": ("iceland",),
    "IT": ("italy",),
    "JM": ("jamaica",),
    "JO": ("jordan",),
    "JP": ("japan",),
    "KE": ("kenya",),
    "KG": ("kyrgyzstan",),
    "KP": ("north korea", "korea dpr"),
    "KR": ("south korea", "korea republic"),
    "KZ": ("kazakhstan",),
    "LB": ("lebanon",),
    "LR": ("liberia",),
    "LS": ("lesotho",),
    "LT": ("lithuania",),
    "LU": ("luxembourg",),
    "LV": ("latvia",),
    "LY": ("libya",),
    "MA": ("morocco",),
    "MD": ("moldova",),
    "ME": ("montenegro",),
    "MG": ("madagascar",),
    "MK": ("north macedonia", "macedonia"),
    "ML": ("mali",),
    "MR": ("mauritania",),
    "MT": ("malta",),
    "MU": ("mauritius",),
    "MW": ("malawi",),
    "MX": ("mexico",),
    "MY": ("malaysia",),
    "MZ": ("mozambique",),
    "NA": ("namibia",),
    "NC": ("new caledonia",),
    "NE": ("niger",),
    "NG": ("nigeria",),
    "NI": ("nicaragua",),
    "NL": ("netherlands", "holland"),
    "NO": ("norway",),
    "NZ": ("new zealand",),
    "OM": ("oman",),
    "PA": ("panama",),
    "PE": ("peru",),
    "PF": ("tahiti",),
    "PH": ("philippines",),
    "PK": ("pakistan",),
    "PL": ("poland",),
    "PR": ("puerto rico",),
    "PS": ("palestine",),
    "PT": ("portugal",),
    "PY": ("paraguay",),
    "QA": ("qatar",),
    "RO": ("romania",),
    "RS": ("serbia",),
    "RU": ("russia",),
    "RW": ("rwanda",),
    "SA": ("saudi arabia",),
    "SB": ("solomon islands",),
    "SC": ("seychelles",),
    "SD": ("sudan",),
    "SE": ("sweden",),
    "SI": ("slovenia",),
    "SK": ("slovakia",),
    "SL": ("sierra leone",),
    "SN": ("senegal",),
    "SO": ("somalia",),
    "SV": ("el salvador",),
    "SY": ("syria",),
    "SZ": ("eswatini", "swaziland"),
    "TD": ("chad",),
    "TG": ("togo",),
    "TH": ("thailand",),
    "TJ": ("tajikistan",),
    "TN": ("tunisia",),
    "TR": ("turkey", "turkiye"),
    "TT": ("trinidad and tobago",),
    "TZ": ("tanzania",),
    "UA": ("ukraine",),
    "UG": ("uganda",),
    "US": ("united states", "united states of america", "usa"),
    "UY": ("uruguay",),
    "UZ": ("uzbekistan",),
    "VE": ("venezuela",),
    "VN": ("vietnam", "viet nam"),
    "XK": ("kosovo",),
    "YE": ("yemen",),
    "ZA": ("south africa",),
    "ZM": ("zambia",),
    "ZW": ("zimbabwe",),
}

_COUNTRY_ALIASES = {
    _normalize_name(alias): alpha2
    for alpha2, aliases in _COUNTRY_ALIAS_GROUPS.items()
    for alias in aliases
}


def _flag_from_alpha2(alpha2: str) -> str:
    code = str(alpha2 or "").upper()
    if len(code) != 2 or not code.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(char) - ord("A")) for char in code)


def country_flag(team_name: str, team_code: str = "") -> str:
    """Return a flag only when the team name is recognizably a country."""
    normalized_name = _normalize_name(team_name)
    alpha2 = _COUNTRY_ALIASES.get(normalized_name)
    if not alpha2 and normalized_name == _normalize_name(team_code):
        alpha2 = _COUNTRY_ALIASES.get(normalized_name)
    return _flag_from_alpha2(alpha2 or "")


def format_team_name(team_name: str, team_code: str = "", fallback: str = "Team") -> str:
    """Prefix national teams with a Unicode flag and leave clubs unchanged."""
    name = str(team_name or fallback)
    flag = country_flag(name, team_code)
    return f"{flag} {name}" if flag else name


def format_match_teams(match: dict) -> str:
    """Format both sides of a stored/provider match for Telegram."""
    home = format_team_name(match.get("home_name"), match.get("home_code"), "Home")
    away = format_team_name(match.get("away_name"), match.get("away_code"), "Away")
    return f"{home} - {away}"
