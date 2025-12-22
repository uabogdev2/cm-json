from __future__ import annotations

import json
import random
import unicodedata
from pathlib import Path
from typing import Callable, Dict, List, Tuple

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

TOTAL_LEVELS = 1500

DIFFICULTY_RANGES = {
    "facile": range(1, 501),
    "moyen": range(501, 1001),
    "difficile": range(1001, TOTAL_LEVELS + 1),
}

# Category distribution per difficulty (sum must equal 500)
DIFFICULTY_CATEGORY_COUNTS = {
    "facile": {"math": 200, "sport": 100, "culture": 100, "musique": 50, "actualité": 50},
    "moyen": {"math": 200, "sport": 100, "culture": 100, "musique": 50, "actualité": 50},
    "difficile": {"math": 200, "sport": 100, "culture": 100, "musique": 50, "actualité": 50},
}

CATEGORY_FACT_LIMITS = {
    "sport": 300,
    "culture": 300,
    "musique": 150,
    "actualité": 150,
}

YEAR_TEMPLATES = [
    "Tape l'annee associee a {subject}.",
    "Quel millesime correspond a {subject} ?",
    "Entre l'annee exacte reliee a {subject}.",
    "Valide le code en donnant l'annee de {subject}.",
    "Quel est le nombre (en annee) pour {subject} ?"
]

STAT_TEMPLATES = [
    "Combien de {stat} {entity} a remporte ?",
    "Indique le total de {stat} obtenu par {entity}.",
    "Quel est le nombre exact de {stat} pour {entity} ?",
    "Tape le cumul de {stat} realise par {entity}.",
    "Combien compte-t-on de {stat} pour {entity} ?"
]

DIGIT_WORDS = {
    0: "zero",
    1: "un",
    2: "deux",
    3: "trois",
    4: "quatre",
    5: "cinq",
    6: "six",
    7: "sept",
    8: "huit",
    9: "neuf",
}


def load_fact_file(path: Path) -> List[Tuple[str, str, int]]:
    entries: List[Tuple[str, str, int]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split("|")
            if len(parts) != 3:
                raise ValueError(f"Malformed line in {path}: {line}")
            fact_type, subject, value = parts
            entries.append((fact_type, subject, int(value)))
    return entries


def take_required(entries: List[Tuple[str, str, int]], required: int) -> List[Tuple[str, str, int]]:
    if len(entries) < required:
        raise ValueError(f"Not enough entries ({len(entries)}) to satisfy requirement ({required}).")
    return entries[:required]


def decade_hint(year: int) -> str:
    if year >= 1900:
        start = (year // 10) * 10
        return f"Indice 1 : L'année se situe dans les années {start}."
    if year >= 1000:
        century = (year // 100) + 1
        return f"Indice 1 : L'événement appartient au {century}e siècle."
    if year >= 100:
        century = (year // 100) + 1
        return f"Indice 1 : L'événement remonte au {century}e siècle."
    if year >= 0:
        return "Indice 1 : L'année se situe avant l'an 1000."
    return "Indice 1 : L'année est négative."


def year_last_digit_hint(year: int) -> str:
    return f"Indice 2 : L'année se termine par {year % 10}."


def count_range_hint(value: int) -> str:
    if value == 0:
        return "Indice 1 : Le total est nul."
    if value < 10:
        return "Indice 1 : Le total est inférieur à 10."
    if value < 20:
        return "Indice 1 : Le total est compris entre 10 et 20."
    if value < 50:
        return "Indice 1 : Le total se situe entre 20 et 50."
    if value < 100:
        return "Indice 1 : Le total est inférieur à 100."
    if value < 500:
        return "Indice 1 : Le total est compris entre 100 et 500."
    if value < 1000:
        return "Indice 1 : Le total est inférieur à 1000."
    return "Indice 1 : Le total dépasse 1000."


def count_parity_hint(value: int) -> str:
    if value == 0:
        return "Indice 2 : Ce nombre est neutralisé à zéro."
    if value % 2 == 0:
        return "Indice 2 : Il s'agit d'un nombre pair."
    return "Indice 2 : Il s'agit d'un nombre impair."


def to_ascii(text: str) -> str:
    replacements = {
        "×": "x",
        "–": "-",
        "—": "-",
        "’": "'",
        "«": '"',
        "»": '"',
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii")


def build_year_instruction(subject: str, rng: random.Random) -> str:
    return rng.choice(YEAR_TEMPLATES).format(subject=subject)


def format_stat_question(entity: str, stat: str, rng: random.Random) -> str:
    stat_lower = stat.lower()
    if not stat:
        stat = "titres remportes"
    template = rng.choice(STAT_TEMPLATES)
    if "but" in stat_lower:
        stat = stat
    if "médailles" in stat_lower or "medailles" in stat_lower:
        stat = stat
    if "but" in stat_lower:
        template = rng.choice([
            "Combien de {stat} {entity} a inscrits ?",
            "Quel est le nombre total de {stat} marques par {entity} ?"
        ])
    elif "médailles" in stat_lower or "medailles" in stat_lower:
        template = rng.choice([
            "Combien de {stat} {entity} a remportees ?",
            "Quel est le total de {stat} pour {entity} ?"
        ])
    elif "tours de france" in stat_lower:
        template = rng.choice([
            "Combien de {stat} {entity} a gagnes ?",
            "Quel est le nombre de {stat} attribues a {entity} ?"
        ])
    elif any(keyword in stat_lower for keyword in ["titre", "coup", "ligue", "champ", "ballon", "grand chelem", "tournoi", "super bowl"]):
        template = rng.choice([
            "Combien de {stat} {entity} a remportes ?",
            "Indique le total de {stat} detenus par {entity}."
        ])
    return template.format(entity=entity, stat=stat)


def split_entity_stat(text: str) -> Tuple[str, str]:
    if " en " in text:
        entity, stat = text.split(" en ", 1)
        return entity.strip(), stat.strip()
    return text.strip(), ""


def culture_fact(entry: Tuple[str, str, int], rng: random.Random) -> Tuple[str, int, List[str]]:
    fact_type, subject, value = entry
    if fact_type == "foundation":
        label = f"la fondation de {subject}"
    elif fact_type == "landmark":
        label = f"l'ouverture de {subject}"
    elif fact_type == "book":
        label = f"la premiere publication du livre {subject}"
    else:
        raise ValueError(f"Unknown culture fact type: {fact_type}")
    instruction = build_year_instruction(label, rng)
    hints = [decade_hint(value), year_last_digit_hint(value)]
    return instruction, value, hints


def sport_fact(entry: Tuple[str, str, int], rng: random.Random) -> Tuple[str, int, List[str]]:
    fact_type, subject, value = entry
    if fact_type == "event_year":
        instruction = build_year_instruction(subject, rng)
        hints = [decade_hint(value), year_last_digit_hint(value)]
        return instruction, value, hints
    entity, stat = split_entity_stat(subject)
    instruction = format_stat_question(entity, stat, rng)
    hints = [count_range_hint(value), count_parity_hint(value)]
    return instruction, value, hints


def music_fact(entry: Tuple[str, str, int], rng: random.Random) -> Tuple[str, int, List[str]]:
    fact_type, subject, value = entry
    if fact_type == "album":
        instruction = build_year_instruction(f"la sortie de l'album {subject}", rng)
        hints = [decade_hint(value), year_last_digit_hint(value)]
        return instruction, value, hints
    if fact_type == "award":
        entity, stat = split_entity_stat(subject)
        instruction = format_stat_question(entity, stat, rng)
        hints = [count_range_hint(value), count_parity_hint(value)]
        return instruction, value, hints
    raise ValueError(f"Unknown music fact type: {fact_type}")


def news_fact(entry: Tuple[str, str, int], rng: random.Random) -> Tuple[str, int, List[str]]:
    _, subject, value = entry
    instruction = build_year_instruction(subject, rng)
    hints = [decade_hint(value), year_last_digit_hint(value)]
    return instruction, value, hints


def build_category_sequences() -> Dict[str, List[str]]:
    sequences: Dict[str, List[str]] = {}
    for difficulty, counts in DIFFICULTY_CATEGORY_COUNTS.items():
        seq: List[str] = []
        for category, amount in counts.items():
            seq.extend([category] * amount)
        rng = random.Random(hash(difficulty) & 0xFFFF)
        rng.shuffle(seq)
        sequences[difficulty] = seq
    return sequences


def difficulty_for_level(level_id: int) -> str:
    for difficulty, id_range in DIFFICULTY_RANGES.items():
        if level_id in id_range:
            return difficulty
    raise ValueError(f"Invalid level id {level_id}")


def compute_points(level_id: int, difficulty: str) -> int:
    mod = level_id % 5
    if difficulty == "facile":
        return 15 + mod * 5
    if difficulty == "moyen":
        return 60 + mod * 10
    return 130 + mod * 15


def compute_time_limit(level_id: int, difficulty: str) -> int:
    mod = level_id % 4
    if difficulty == "facile":
        return 20 + mod * 5
    if difficulty == "moyen":
        return 40 + mod * 10
    return 65 + mod * 15


def compute_hint_cost(level_id: int, difficulty: str) -> int:
    mod = level_id % 4
    if difficulty == "facile":
        return 60 + mod * 10
    if difficulty == "moyen":
        return 140 + mod * 15
    return 220 + mod * 20


def math_template_expression(difficulty: str, rng: random.Random) -> Tuple[str, str, List[str]]:
    if difficulty == "facile":
        a = rng.randint(6, 20)
        b = rng.randint(3, 12)
        c = rng.randint(15, 70)
    elif difficulty == "moyen":
        a = rng.randint(15, 50)
        b = rng.randint(18, 70)
        c = rng.randint(90, 260)
    else:
        a = rng.randint(40, 110)
        b = rng.randint(60, 180)
        c = rng.randint(220, 750)
    if rng.random() < 0.4:
        d = rng.randint(10, max(20, c // 2))
        result = a * b + c - d
        instruction = f"Calcule : ({a} x {b}) + {c} - {d}."
        hints = [
            f"Indice 1 : {a} x {b} = {a * b}.",
            f"Indice 2 : Ajoute {c}, puis retire {d}."
        ]
    else:
        result = a * b + c
        instruction = f"Calcule : ({a} x {b}) + {c}."
        hints = [
            f"Indice 1 : Commence par la multiplication ({a * b}).",
            "Indice 2 : Ajoute ensuite le dernier terme."
        ]
    return instruction, str(result), hints


def math_template_sequence(difficulty: str, rng: random.Random) -> Tuple[str, str, List[str]]:
    mode = rng.choice(["up", "down", "double"])
    length = 4
    if mode == "up":
        step = rng.randint(2, 9) if difficulty == "facile" else rng.randint(4, 18)
        start = rng.randint(5, 40)
        values = [start + i * step for i in range(length)]
        answer = values[-1] + step
        hint_detail = f"+{step}"
    elif mode == "down":
        step = rng.randint(2, 8) if difficulty == "facile" else rng.randint(6, 20)
        min_start = step * (length + 2)
        max_start = min_start + (40 if difficulty == "facile" else 120)
        start = rng.randint(min_start, max_start)
        values = [start - i * step for i in range(length)]
        answer = values[-1] - step
        hint_detail = f"-{step}"
    else:
        factor = 2 if difficulty != "difficile" else rng.choice([2, 3])
        start = rng.randint(2, 6) * (10 if difficulty == "facile" else 20)
        values = [start * (factor ** i) for i in range(length)]
        answer = values[-1] * factor
        hint_detail = f"x{factor}"
    instruction = f"Complete la suite : {', '.join(str(v) for v in values)}, ?"
    if mode == "double":
        hints = [
            f"Indice 1 : Chaque terme se multiplie par {hint_detail[1:]}.",
            "Indice 2 : Applique ce facteur au dernier nombre cite."
        ]
    else:
        hints = [
            f"Indice 1 : La suite avance toujours de {hint_detail}.",
            "Indice 2 : Utilise le meme ecart pour obtenir le prochain terme."
        ]
    return instruction, str(answer), hints


def math_template_conversion(difficulty: str, rng: random.Random) -> Tuple[str, str, List[str]]:
    options = [
        ("heure", "minutes", 60, lambda v: v * 60, "Combien de minutes dans {value} heures ?"),
        ("minute", "secondes", 60, lambda v: v * 60, "Combien de secondes dans {value} minutes ?"),
        ("jour", "heures", 24, lambda v: v * 24, "Combien d'heures dans {value} jours ?"),
        ("kilometre", "metres", 1000, lambda v: v * 1000, "Convertis {value} kilometres en metres."),
        ("metre", "centimetres", 100, lambda v: v * 100, "Combien de centimetres dans {value} metres ?"),
        ("semaine", "jours", 7, lambda v: v * 7, "Combien de jours dans {value} semaines ?"),
    ]
    unit_from, unit_to, factor, func, phrase = rng.choice(options)
    if difficulty == "facile":
        value = rng.randint(2, 8)
    elif difficulty == "moyen":
        value = rng.randint(5, 18)
    else:
        value = rng.randint(10, 30)
    result = func(value)
    instruction = phrase.format(value=value)
    hints = [
        f"Indice 1 : 1 {unit_from} = {factor} {unit_to}.",
        f"Indice 2 : Multiplie {value} par {factor}."
    ]
    return instruction, str(result), hints


def math_template_literal_digits(difficulty: str, rng: random.Random) -> Tuple[str, str, List[str]]:
    length = 4 if difficulty == "facile" else rng.choice([4, 5])
    digits = []
    for i in range(length):
        if i == 0 and rng.random() < 0.3:
            digits.append(0)
        else:
            digits.append(rng.randint(0, 9))
    phrase = "-".join(DIGIT_WORDS[d] for d in digits)
    code = "".join(str(d) for d in digits)
    instruction = f"Transcris \"{phrase}\" en chiffres (sans espace)."
    hints = [
        "Indice 1 : Les mots sont deja ordonnes.",
        "Indice 2 : Remplace chaque mot par son chiffre."
    ]
    return instruction, code, hints


def math_template_balance(difficulty: str, rng: random.Random) -> Tuple[str, str, List[str]]:
    if difficulty == "facile":
        start = rng.randint(300, 900)
        spend1 = rng.randint(30, 180)
        spend2 = rng.randint(25, 140)
        earn = rng.randint(20, 110)
    elif difficulty == "moyen":
        start = rng.randint(900, 2800)
        spend1 = rng.randint(120, 480)
        spend2 = rng.randint(110, 420)
        earn = rng.randint(80, 360)
    else:
        start = rng.randint(2200, 5800)
        spend1 = rng.randint(260, 1100)
        spend2 = rng.randint(240, 880)
        earn = rng.randint(150, 640)
    result = start - spend1 - spend2 + earn
    instruction = (
        f"Je dispose de {start} euros. Je paye {spend1} euros puis {spend2} euros, "
        f"et je recois ensuite {earn} euros. Quel est mon solde ?"
    )
    hints = [
        f"Indice 1 : Apres les depenses, il reste {start - spend1 - spend2} euros.",
        f"Indice 2 : Ajoute {earn} pour obtenir la somme finale."
    ]
    return instruction, str(result), hints


def math_template_decomposition(difficulty: str, rng: random.Random) -> Tuple[str, str, List[str]]:
    thousands = rng.randint(1, 9)
    hundreds = rng.randint(0, 9)
    tens = rng.randint(0, 9)
    ones = rng.randint(0, 9)
    parts = [f"({thousands} x 1000)"]
    result = thousands * 1000
    if hundreds or rng.random() < 0.4:
        parts.append(f"({hundreds} x 100)")
        result += hundreds * 100
    if tens or rng.random() < 0.6:
        parts.append(f"({tens} x 10)")
        result += tens * 10
    if ones or rng.random() < 0.6:
        parts.append(str(ones))
        result += ones
    instruction = "Calcule : " + " + ".join(parts)
    hints = [
        "Indice 1 : Multiplie chaque bloc avant d'additionner.",
        "Indice 2 : Assemble milliers, centaines, dizaines et unites."
    ]
    return instruction, str(result), hints


def math_question(level_id: int, difficulty: str, rng: random.Random) -> Tuple[str, str, List[str]]:
    templates = [
        math_template_expression,
        math_template_sequence,
        math_template_conversion,
        math_template_literal_digits,
        math_template_balance,
        math_template_decomposition,
    ]
    instruction, code_value, hints = rng.choice(templates)(difficulty, rng)
    if not code_value.isdigit():
        raise ValueError(f"Code {code_value} invalide")
    if not (1 <= len(code_value) <= 5):
        raise ValueError(f"Code {code_value} a une longueur hors limites")
    return instruction, code_value, hints


def main() -> None:
    rng = random.Random(202405)

    culture_facts = take_required(load_fact_file(DATA_DIR / "culture_facts.txt"), CATEGORY_FACT_LIMITS["culture"])
    sport_facts = take_required(load_fact_file(DATA_DIR / "sport_facts.txt"), CATEGORY_FACT_LIMITS["sport"])
    music_facts = take_required(load_fact_file(DATA_DIR / "music_facts.txt"), CATEGORY_FACT_LIMITS["musique"])
    news_facts = take_required(load_fact_file(DATA_DIR / "news_facts.txt"), CATEGORY_FACT_LIMITS["actualité"])

    fact_data = {
        "culture": culture_facts,
        "sport": sport_facts,
        "musique": music_facts,
        "actualité": news_facts,
    }
    fact_indices = {key: 0 for key in fact_data}

    sequences = build_category_sequences()
    sequence_positions = {difficulty: 0 for difficulty in sequences}

    converters = {
        "culture": culture_fact,
        "sport": sport_fact,
        "musique": music_fact,
        "actualité": news_fact,
    }

    levels: List[Dict[str, object]] = []

    for level_id in range(1, TOTAL_LEVELS + 1):
        difficulty = difficulty_for_level(level_id)
        seq = sequences[difficulty]
        pos = sequence_positions[difficulty]
        if pos >= len(seq):
            raise ValueError(f"No more categories available for difficulty {difficulty}")
        category = seq[pos]
        sequence_positions[difficulty] += 1

        if category == "math":
            instruction, code_value, hints = math_question(level_id, difficulty, rng)
        else:
            idx = fact_indices[category]
            data_list = fact_data[category]
            if idx >= len(data_list):
                raise ValueError(f"Not enough facts for category {category}")
            fact = data_list[idx]
            fact_indices[category] += 1
            instruction, code_value, hints = converters[category](fact, rng)

        code_str = str(code_value)
        if not code_str.isdigit() or len(code_str) > 5:
            raise ValueError(f"Invalid code {code_str} at level {level_id}")

        instruction = to_ascii(instruction)
        hints = [to_ascii(hint) for hint in hints]

        level_entry = {
            "id": level_id,
            "name": f"Niveau {level_id}",
            "instruction": instruction,
            "code": code_str,
            "codeLength": len(code_str),
            "pointsReward": compute_points(level_id, difficulty),
            "isLocked": level_id != 1,
            "timeLimit": compute_time_limit(level_id, difficulty),
            "additionalHints": hints[:2],
            "hintCost": compute_hint_cost(level_id, difficulty),
        }
        levels.append(level_entry)

    output_path = ROOT / "level.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(levels, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()
