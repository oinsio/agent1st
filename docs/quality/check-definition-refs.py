#!/usr/bin/env python3
"""Самопроверка ссылок definition.md (рекомендация 7.7 из consistency-v2.2.md).

Проверяет, что документ разрешает собственные ссылки, как К5 требует этого
от инструкций агенту:
  - каждый код Я/К/Н/С, упомянутый в тексте, есть строкой таблицы
    (кроме объявленных вакантными);
  - каждая ссылка «правило N» попадает в существующий пункт правил §3;
  - каждая ссылка «§N» и «§N п.M» попадает в существующий раздел и пункт;
  - каждый профиль в кавычках после слова «профиль» есть в таблице §8;
  - каждый файл в обратных кавычках лежит рядом с проверяемым файлом;
  - строка таблицы критериев, называющая ЧАСТИЧНО или НЕТ, ссылается
    на правило или шкалу (правило «одно правило, одно место»);
  - строки, которые абзац типа объявляет ссылающимися на него, содержат
    эту ссылку.

Запуск: python3 check-definition-refs.py definition.md [ещё файлы]
Код выхода 1, если найдена хотя бы одна проблема.
"""
import re
import sys
from pathlib import Path

CODE = re.compile(r"(?<![А-Яа-яA-Za-z])([ЯКНС]\d+)(?![А-Яа-я\d])")
ROW_CODE = re.compile(r"^\| ([ЯКНС]\d+) \|")
HEADING = re.compile(r"^## (\d+)\) ")
NUMBERED = re.compile(r"^(\d+)\. ")
RULE_REF = re.compile(r"правил[оауе]\s+(\d+)(?:\s+и\s+(\d+))?")
SECTION_REF = re.compile(r"§(\d+)(?:\s+п\.(\d+))?")
PROFILE_REF = re.compile(r"профил[яьеюи]\s+«([^»]+)»")
FILE_REF = re.compile(r"`([\w.-]+\.(?:md|py))`")
VACANT = re.compile(r"код (\S+?) вакантен")
VERDICT = re.compile(r"(?<![А-Я])(ЧАСТИЧНО|НЕТ)(?![А-Я])")
POINTS_HERE = re.compile(r"строки ([^.]+?) ссылаются сюда")


def sections(lines):
    """Карта номер раздела → список строк раздела."""
    out, current = {}, None
    for line in lines:
        m = HEADING.match(line)
        if m:
            current = int(m.group(1))
            out[current] = []
        elif current is not None:
            out[current].append(line)
    return out


def numbered_items(section_lines):
    return {int(m.group(1)) for line in section_lines for m in [NUMBERED.match(line)] if m}


def check(path: Path):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    problems = []
    secs = sections(lines)

    defined = {m.group(1) for line in lines for m in [ROW_CODE.match(line)] if m}
    vacant = set(VACANT.findall(text))
    for n, line in enumerate(lines, 1):
        for code in CODE.findall(line):
            if code not in defined and code not in vacant:
                problems.append(f"{n}: код {code} нигде не определён строкой таблицы")

    rules = numbered_items(secs.get(3, []))
    for n, line in enumerate(lines, 1):
        for a, b in RULE_REF.findall(line):
            for r in (a, b):
                if r and int(r) not in rules:
                    problems.append(f"{n}: правило {r} не существует (в §3 пункты {sorted(rules)})")

    for n, line in enumerate(lines, 1):
        for s, p in SECTION_REF.findall(line):
            s = int(s)
            if s not in secs:
                problems.append(f"{n}: раздел §{s} не существует")
            elif p and int(p) not in numbered_items(secs[s]):
                problems.append(f"{n}: §{s} п.{p} не существует")

    profiles = set()
    for line in secs.get(8, []):
        m = re.match(r"^\| ([^|]+?) \|", line)
        if m and m.group(1) not in ("Тип", "---"):
            profiles.add(m.group(1).strip().lower())
    for n, line in enumerate(lines, 1):
        for name in PROFILE_REF.findall(line):
            if name.strip().lower() not in profiles:
                problems.append(f"{n}: профиль «{name}» отсутствует в §8 ({', '.join(sorted(profiles))})")

    for n, line in enumerate(lines, 1):
        for fname in FILE_REF.findall(line):
            if not (path.parent / fname).exists():
                problems.append(f"{n}: файл `{fname}` не найден рядом с {path.name}")

    for n, line in enumerate(lines, 1):
        if ROW_CODE.match(line) and VERDICT.search(line):
            if "правил" not in line and "шкал" not in line:
                problems.append(f"{n}: строка {ROW_CODE.match(line).group(1)} называет вердикт без ссылки на правило или шкалу")

    rows = {m.group(1): line for line in lines for m in [ROW_CODE.match(line)] if m}
    for m in POINTS_HERE.finditer(text):
        for code in CODE.findall(m.group(1)):
            row = rows.get(code, "")
            if "вызывает LLM" not in row:
                problems.append(f"строка {code} объявлена ссылающейся на абзац типа, но ссылки в ней нет")

    return problems


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    status = 0
    for arg in argv[1:]:
        path = Path(arg)
        problems = check(path)
        print(f"{path.name}: {'без проблем' if not problems else str(len(problems)) + ' проблем'}")
        for p in problems:
            print("  " + p)
        if problems:
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv))
