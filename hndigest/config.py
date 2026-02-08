"""Configuration: channels, categories, and constants."""

import logging
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Channel:
    id: str
    telegram: str
    title: str
    language: str
    prompt: str  # Translation prompt (empty = no translation)
    footer: str
    first_issue_date: str  # ISO date of first issue (for edition numbering)
    days: int = 7
    limit: int = 50
    min_points: int = 50


CHANNELS: dict[str, Channel] = {
    "hn_uz": Channel(
        id="hn_uz",
        telegram="@HNDigestUz",
        title="Hacker News Dayjesti",
        language="uz",
        prompt="""Sarlavhani oʻzbek tiliga tarjima qil. Texnik atamalarni tarjima qilma.
Tirnoq oʻrniga «» ishlatilsin. Faqat tarjima qilingan sarlavhani qaytar.
Muhim: oʻzbek tilidagi maxsus harflarni toʻgʻri yoz — oʻ (o + ʻ), gʻ (g + ʻ), ʼ (tutuq belgisi). Oddiy apostrof (') ishlatma.""",
        footer="Obuna boʻling: @HNDigestUz",
        first_issue_date="2026-02-07",
    ),
    "hn_ru": Channel(
        id="hn_ru",
        telegram="@HNDigestRu",
        title="Hacker News Дайджест",
        language="ru",
        prompt="""Переведи заголовок на русский. Технические термины не переводи.
Используй «» для кавычек. Верни только переведённый заголовок.""",
        footer="Подписывайтесь: @HNDigestRu",
        first_issue_date="2026-02-07",
    ),
    "hn_en": Channel(
        id="hn_en",
        telegram="@HNDigestEn",
        title="Hacker News Digest",
        language="en",
        prompt="",  # No translation
        footer="Subscribe: @HNDigestEn",
        first_issue_date="2026-02-07",
    ),
}

# Constants
CACHE_DIR = Path("./cache/gemini")
CONTENT_CACHE_DIR = Path("./cache/content")
HN_API = "https://hn.algolia.com/api/v1/search_by_date"
HN_ITEM = "https://news.ycombinator.com/item?id={}"
GEMINI_API = (
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
)
TELEGRAM_API = "https://api.telegram.org/bot{}/sendMessage"
TELEGRAM_EDIT_API = "https://api.telegram.org/bot{}/editMessageText"

JOB_WORDS = ["hiring", "who is hiring", "who wants to be hired", "freelancer", "job", "career"]

# Category display names per language
CATEGORY_NAMES: dict[str, dict[str, str]] = {
    "top": {"uz": "Eng yaxshilar", "ru": "Лучшее", "en": "Top"},
    "ai": {"uz": "AI", "ru": "AI", "en": "AI"},
    "dev": {"uz": "Dev", "ru": "Код", "en": "Dev"},
    "ops": {"uz": "Ops", "ru": "Ops", "en": "Ops"},
    "data": {"uz": "Ma'lumotlar", "ru": "Данные", "en": "Data"},
    "science": {"uz": "Fan", "ru": "Наука", "en": "Science"},
    "security": {"uz": "Xavfsizlik", "ru": "Безопасность", "en": "Security"},
    "tech": {"uz": "Texnologiya", "ru": "Индустрия", "en": "Tech"},
    "career": {"uz": "Karyera", "ru": "Карьера", "en": "Career"},
    "culture": {"uz": "Madaniyat", "ru": "Культура", "en": "Culture"},
    "show_hn": {"uz": "Show HN", "ru": "Show HN", "en": "Show HN"},
    "ask_hn": {"uz": "Ask HN", "ru": "Ask HN", "en": "Ask HN"},
}

# Localized labels
LABELS: dict[str, dict[str, str]] = {
    "points": {"uz": "ball", "ru": "баллов", "en": "points"},
    "comments": {"uz": "izoh", "ru": "комм.", "en": "comments"},
}

# Month names per language
MONTHS: dict[str, list[str]] = {
    "uz": ["yan", "fev", "mar", "apr", "may", "iyun", "iyul", "avg", "sen", "okt", "noy", "dek"],
    "ru": ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"],
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
}

# Categories with keywords and domains
CATEGORIES: dict[str, dict[str, list[str]]] = {
    "ai": {
        "keywords": [
            "ai",
            "gpt",
            "llm",
            "chatgpt",
            "openai",
            "anthropic",
            "gemini",
            "claude",
            "machine learning",
            "neural",
            "transformer",
            "diffusion",
            "deepmind",
            "copilot",
            "midjourney",
            "stable diffusion",
            "mistral",
            "llama",
            "waymo",
            "self-driving",
            "autonomous",
            "model",
        ],
        "domains": ["openai.com", "anthropic.com", "deepmind.com", "huggingface.co"],
    },
    "dev": {
        "keywords": [
            "rust",
            "python",
            "javascript",
            "typescript",
            "golang",
            "compiler",
            "programming",
            "git",
            "open source",
            "api",
            "webassembly",
            "wasm",
            "software architecture",
            "vim",
            "emacs",
            "neovim",
            "terminal",
            "cli",
        ],
        "domains": ["github.com", "gitlab.com", "dev.to", "sourceware.org"],
    },
    "ops": {
        "keywords": [
            "linux",
            "kernel",
            "docker",
            "kubernetes",
            "devops",
            "nginx",
            "serverless",
            "sysadmin",
            "raspberry pi",
            "fpga",
            "hardware",
            "database",
            "sql",
            "postgres",
            "redis",
            "mongodb",
            "sqlite",
            "cassandra",
            "elasticsearch",
        ],
        "domains": ["postgresql.org"],
    },
    "data": {
        "keywords": [
            "data engineering",
            "analytics",
            "bigquery",
            "data science",
            "visualization",
            "spreadsheet",
            "big data",
            "pandas",
            "dbt",
            "data pipeline",
        ],
        "domains": [],
    },
    "science": {
        "keywords": [
            "research",
            "paper",
            "study",
            "physics",
            "biology",
            "chemistry",
            "math",
            "mathematics",
            "space",
            "spacex",
            "nasa",
            "telescope",
            "quantum",
            "genome",
            "climate",
            "climate change",
            "neuroscience",
            "arxiv",
            "peer review",
            "experiment",
            "solar",
            "nuclear",
            "energy",
        ],
        "domains": ["arxiv.org", "nature.com", "science.org", "nasa.gov", "spacex.com"],
    },
    "security": {
        "keywords": [
            "security",
            "vulnerability",
            "breach",
            "malware",
            "ransomware",
            "exploit",
            "zero-day",
            "privacy",
            "encryption",
            "backdoor",
            "hijack",
            "cve",
            "phishing",
            "infosec",
        ],
        "domains": ["krebsonsecurity.com", "schneier.com"],
    },
    "tech": {
        "keywords": [
            "startup",
            "founder",
            "yc",
            "ycombinator",
            "funding",
            "series a",
            "acquisition",
            "ipo",
            "valuation",
            "layoff",
            "regulation",
            "law",
            "ban",
            "government",
            "congress",
            "court",
            "lawsuit",
            "antitrust",
            "policy",
            "legal",
            "fcc",
            "ftc",
            "firm",
            "cloud",
            "eu-native",
            "digital autonomy",
            "big tech",
        ],
        "domains": ["techcrunch.com", "ycombinator.com", "theregister.com"],
    },
    "career": {
        "keywords": [
            "remote work",
            "career",
            "hiring culture",
            "management",
            "interview",
            "workplace",
            "burnout",
            "salary",
            "freelance",
            "work-life",
        ],
        "domains": [],
    },
    "culture": {
        "keywords": [
            "history",
            "urbanism",
            "philosophy",
            "gaming",
            "typography",
            "typeface",
            "font",
            "ui design",
            "ux design",
            "css",
            "svg",
            "figma",
            "accessibility",
            "copyright",
            "digital rights",
            "culture",
            "animation",
            "color palette",
        ],
        "domains": ["figma.com", "dribbble.com"],
    },
    "show_hn": {
        "keywords": ["show hn"],
        "domains": [],
    },
    "ask_hn": {
        "keywords": ["ask hn"],
        "domains": [],
    },
}


def category_name(key: str, language: str) -> str:
    """Get localized category display name."""
    return CATEGORY_NAMES.get(key, {}).get(language, key)


def categorize_story(story: dict) -> str:
    """Categorize a story based on title keywords and domain."""
    title_lower = story["title"].lower()
    domain = story.get("domain", "").lower()

    # Check Show HN / Ask HN first — they take priority
    for priority_key in ("show_hn", "ask_hn"):
        for kw in CATEGORIES[priority_key]["keywords"]:
            if kw in title_lower:
                return priority_key

    for cat_key, rules in CATEGORIES.items():
        if cat_key in ("show_hn", "ask_hn"):
            continue
        for kw in rules["keywords"]:
            if kw in title_lower:
                return cat_key
        for d in rules["domains"]:
            if d in domain:
                return cat_key

    return "culture"


logging.basicConfig(format="%(message)s", level=logging.INFO)
log = logging.getLogger("hndigest")
