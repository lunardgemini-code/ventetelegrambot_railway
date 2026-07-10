# utils/helpers.py — Fonctions utilitaires générales

import html
import uuid
from datetime import datetime
from config import ADMIN_IDS


def escape_html(text: str) -> str:
    """Escape HTML special characters to prevent injection in Telegram messages.

    Telegram's HTML parser supports tags like <b>, <a>, <code> etc.
    User-supplied text must be escaped before embedding in parse_mode='HTML' messages.
    """
    return html.escape(str(text), quote=False)


def is_admin(user_id: int) -> bool:
    """Vérifie si un utilisateur est administrateur."""
    return user_id in ADMIN_IDS


def format_price(amount) -> str:
    """Formate un montant en prix lisible : $X.XX (robuste si None / str)."""
    try:
        if amount is None or amount == "":
            return "$0.00"
        return f"${float(amount):.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def safe_format(template: str, **kwargs) -> str:
    """Like str.format but never crashes on stray braces in values."""
    try:
        return template.format(**kwargs)
    except (KeyError, ValueError, IndexError):
        # Fallback: sequential replace of known placeholders only
        out = template
        for key, value in kwargs.items():
            out = out.replace("{" + key + "}", str(value))
        return out


def generate_order_id() -> str:
    """Génère un identifiant de commande unique au format ORD-XXXXXXXX."""
    return f"ORD-{uuid.uuid4().hex[:8].upper()}"


def format_date(timestamp: str | None) -> str:
    """Formate un timestamp ISO en date lisible en français.

    Exemple de sortie : ``14 Fév 2026, 09:30``
    """
    if not timestamp:
        return "N/A"
    try:
        dt = datetime.fromisoformat(timestamp)
        months = [
            "Jan", "Fév", "Mar", "Avr", "Mai", "Jun",
            "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc",
        ]
        return f"{dt.day} {months[dt.month - 1]} {dt.year}, {dt.strftime('%H:%M')}"
    except (ValueError, TypeError):
        return str(timestamp)


def truncate_text(text: str, max_len: int = 30) -> str:
    """Tronque un texte s'il dépasse la longueur maximale."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
