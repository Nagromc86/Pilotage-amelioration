import re
import dateparser

ACTION_PATTERNS = [
    r"(?i)\baction\s*:\s*(?P<action>.+)",
    r"(?i)\bà faire\s*:\s*(?P<action>.+)",
    r"(?i)\btodo\s*:\s*(?P<action>.+)",
    r"(?i)\bdecision\s*:\s*(?P<action>.+)",
    r"(?i)\bdecide\s*:\s*(?P<action>.+)",
    r"(?i)\b=>\s*(?P<action>.+)",
]

ACTOR_PATTERNS = [
    r"@(?P<actor>[A-ZÉÈÀÂÎÔÛÇ][A-Za-zÉÈÀÂÎÔÛÇéèàâêîôûç\-']+)",
    r"(?P<actor>[A-ZÉÈÀÂÎÔÛÇ][a-zéèàâêîôûç\-']{1,})\s+(doit|va)\b",
]

def parse_due(text, languages=("fr","en")):
    dt = dateparser.parse(text, languages=list(languages), settings={"PREFER_DATES_FROM":"future"})
    return dt.strftime("%Y-%m-%d") if dt else ""

def extract_actions(text, known_actors=None):
    known_actors = known_actors or []
    suggestions = []

    for line in text.splitlines():
        line = line.strip()
        if not line: continue

        act = None
        for pat in ACTION_PATTERNS:
            m = re.search(pat, line)
            if m:
                act = m.group("action").strip().rstrip(".")
                break

        if not act and re.search(r"(?i)\b(doit|à faire|faire|livrer|envoyer|finaliser|préparer)\b", line):
            act = line

        if not act:
            continue

        actor = ""
        for pat in ACTOR_PATTERNS:
            m = re.search(pat, line)
            if m:
                actor = m.group("actor").strip()
                break

        if not actor:
            for a in known_actors:
                if act.lower().startswith(a.lower()+" ") or f" {a} " in act:
                    actor = a
                    break

        due = ""
        for hint in ["aujourd'hui","demain","après-demain","la semaine prochaine","d'ici vendredi","fin de semaine","fin de mois","fin de semaine prochaine"]:
            if hint in line.lower():
                due = parse_due(hint)
                break
        if not due:
            m = re.search(r"(?i)(pour|avant|d'ici|le)\s+([0-3]?\d[/-][01]?\d(?:[/-]\d{2,4})?|[0-3]?\d\s+[A-Za-zéûî]+)", line)
            if m:
                due = parse_due(m.group(0))

        suggestions.append({"action": act, "actor": actor, "due_date": due})

    seen = set(); uniq = []
    for s in suggestions:
        key = (s["action"].lower(), s["actor"].lower(), s["due_date"])
        if key not in seen:
            uniq.append(s); seen.add(key)
    return uniq
