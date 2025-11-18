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


def format_stat_question(entity: str, stat: str) -> str:
    stat_lower = stat.lower()
    if not stat:
        return f"Combien de titres {entity} a remportés ?"
    if "but" in stat_lower:
        return f"Combien de {stat} {entity} a inscrits ?"
    if "médailles" in stat_lower:
        return f"Combien de {stat} {entity} a remportées ?"
    if "tours de france" in stat_lower:
        return f"Combien de {stat} {entity} a gagnés ?"
    if any(keyword in stat_lower for keyword in ["titre", "coup", "ligue", "champ", "ballon", "grand chelem", "tournoi"]):
        return f"Combien de {stat} {entity} a remportés ?"
    return f"Quel est le total de {stat} obtenu par {entity} ?"


def split_entity_stat(text: str) -> Tuple[str, str]:
    if " en " in text:
        entity, stat = text.split(" en ", 1)
        return entity.strip(), stat.strip()
    return text.strip(), ""


def culture_fact(entry: Tuple[str, str, int]) -> Tuple[str, int, List[str]]:
    fact_type, subject, value = entry
    if fact_type == "foundation":
        instruction = f"En quelle année {subject} a-t-elle été fondée ?"
    elif fact_type == "landmark":
        instruction = f"En quelle année {subject} a ouvert ses portes ?"
    elif fact_type == "book":
        instruction = f"En quelle année le livre {subject} a-t-il été publié pour la première fois ?"
    else:
        raise ValueError(f"Unknown culture fact type: {fact_type}")
    hints = [decade_hint(value), year_last_digit_hint(value)]
    return instruction, value, hints


def sport_fact(entry: Tuple[str, str, int]) -> Tuple[str, int, List[str]]:
    fact_type, subject, value = entry
    if fact_type == "event_year":
        instruction = f"En quelle année {subject} ?"
        hints = [decade_hint(value), year_last_digit_hint(value)]
        return instruction, value, hints
    entity, stat = split_entity_stat(subject)
    instruction = format_stat_question(entity, stat)
    hints = [count_range_hint(value), count_parity_hint(value)]
    return instruction, value, hints


def music_fact(entry: Tuple[str, str, int]) -> Tuple[str, int, List[str]]:
    fact_type, subject, value = entry
    if fact_type == "album":
        instruction = f"En quelle année l'album « {subject} » est-il sorti ?"
        hints = [decade_hint(value), year_last_digit_hint(value)]
        return instruction, value, hints
    if fact_type == "award":
        entity, stat = split_entity_stat(subject)
        instruction = format_stat_question(entity, stat)
        hints = [count_range_hint(value), count_parity_hint(value)]
        return instruction, value, hints
    raise ValueError(f"Unknown music fact type: {fact_type}")


def news_fact(entry: Tuple[str, str, int]) -> Tuple[str, int, List[str]]:
    _, subject, value = entry
    instruction = f"En quelle année {subject} ?"
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


def math_question(level_id: int, difficulty: str, rng: random.Random) -> Tuple[str, int, List[str]]:
    if difficulty == "facile":
        template = rng.choice(["sum3", "mix", "diff", "thousands"])
        if template == "sum3":
            a = rng.randint(12, 180)
            b = rng.randint(25, 240)
            c = rng.randint(8, 120)
            result = a + b + c
            instruction = f"Additionnez {a}, {b} et {c}."
            hints = [f"Indice 1 : Additionnez d'abord {a} et {b}.",
                     f"Indice 2 : Ajoutez ensuite {c} au total provisoire."]
        elif template == "mix":
            a = rng.randint(7, 24)
            b = rng.randint(6, 15)
            c = rng.randint(15, 75)
            result = a * b + c
            instruction = f"Calculez {a} × {b} puis ajoutez {c}."
            hints = [f"Indice 1 : {a} × {b} vaut {a * b}.",
                     f"Indice 2 : Ajoutez {c} pour obtenir le total final."]
        elif template == "diff":
            a = rng.randint(350, 950)
            b = rng.randint(80, 320)
            result = a - b
            instruction = f"Soustrayez {b} à {a}."
            hints = [f"Indice 1 : Commencez par {a} - {b//2} = {a - (b//2)}.",
                     "Indice 2 : Terminez la soustraction pour obtenir le reste exact."]
        else:
            a = rng.randint(1200, 3200)
            b = rng.randint(450, 1700)
            result = a + b
            instruction = f"Additionnez {a} et {b}."
            hints = [f"Indice 1 : La somme dépasse {a + b - rng.randint(10, 30)}.",
                     f"Indice 2 : Vérifiez les centaines, le résultat est {len(str(result))} chiffres."]
    elif difficulty == "moyen":
        template = rng.choice(["prod_add", "double_mix", "sum4", "scaled_diff"])
        if template == "prod_add":
            a = rng.randint(28, 95)
            b = rng.randint(120, 380)
            c = rng.randint(150, 480)
            result = a * b + c
            instruction = f"Calculez {a} × {b} puis ajoutez {c}."
            hints = [f"Indice 1 : {a} × {b} vaut {a * b}.",
                     f"Indice 2 : Ajoutez {c} pour terminer."]
        elif template == "double_mix":
            a = rng.randint(22, 60)
            b = rng.randint(18, 55)
            c = rng.randint(40, 120)
            d = rng.randint(15, 60)
            result = a * b + c * d
            instruction = f"Additionnez {a} × {b} et {c} × {d}."
            hints = [f"Indice 1 : {a} × {b} = {a * b}.",
                     f"Indice 2 : {c} × {d} = {c * d}. Additionnez-les."]
        elif template == "sum4":
            values = [rng.randint(120, 980) for _ in range(4)]
            result = sum(values)
            instruction = f"Additionnez {', '.join(str(v) for v in values[:-1])} et {values[-1]}."
            hints = [f"Indice 1 : La somme des deux premiers termes vaut {values[0] + values[1]}.",
                     f"Indice 2 : Ajoutez ensuite {values[2]} puis {values[3]}."]
        else:
            a = rng.randint(4000, 7800)
            b = rng.randint(1200, 3900)
            c = rng.randint(150, 980)
            result = (a - b) + c
            instruction = f"Soustrayez {b} à {a}, puis ajoutez {c}."
            hints = [f"Indice 1 : {a} - {b} = {a - b}.",
                     f"Indice 2 : Ajoutez {c} pour conclure."]
    else:
        template = rng.choice(["big_mix", "double_prod", "staged", "combo"])
        if template == "big_mix":
            a = rng.randint(120, 260)
            b = rng.randint(210, 360)
            c = rng.randint(800, 2600)
            result = a * b + c
            instruction = f"Calculez {a} × {b} puis ajoutez {c}."
            hints = [f"Indice 1 : La multiplication donne {a * b}.",
                     f"Indice 2 : Ajoutez {c} pour dépasser {result - rng.randint(10, 50)}."]
        elif template == "double_prod":
            a = rng.randint(130, 220)
            b = rng.randint(140, 280)
            c = rng.randint(25, 70)
            d = rng.randint(60, 130)
            result = a * b - c * d
            instruction = f"Calculez {a} × {b} puis soustrayez {c} × {d}."
            hints = [f"Indice 1 : {a} × {b} = {a * b}.",
                     f"Indice 2 : {c} × {d} = {c * d}. Soustrayez-les."]
        elif template == "staged":
            a = rng.randint(3200, 7900)
            b = rng.randint(1800, 5400)
            c = rng.randint(600, 1800)
            result = a + b - c
            instruction = f"Additionnez {a} et {b}, puis soustrayez {c}."
            hints = [f"Indice 1 : {a} + {b} = {a + b}.",
                     f"Indice 2 : Retirez {c} du total précédent."]
        else:
            values = [rng.randint(900, 9500) for _ in range(3)]
            extras = [rng.randint(120, 850) for _ in range(2)]
            result = values[0] + values[1] + values[2] - extras[0] + extras[1]
            instruction = (
                f"Additionnez {values[0]}, {values[1]} et {values[2]}, retranchez {extras[0]}, "
                f"puis ajoutez {extras[1]}."
            )
            hints = [
                f"Indice 1 : La somme initiale vaut {values[0] + values[1] + values[2]}.",
                f"Indice 2 : Soustrayez {extras[0]} puis ajoutez {extras[1]}.",
            ]
    if not (0 <= result <= 99999):
        raise ValueError(f"Result {result} out of bounds for level {level_id}")
    return instruction, result, hints


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
            instruction, code_value, hints = converters[category](fact)

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
