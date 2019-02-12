from pathlib import Path
import re

import pytest

from jfk_fling.fprogram import FortranGatherer


HERE = Path(__file__).parent
INPUT_PATTERN = re.compile(r'Input\[(\d+)\]')
OUTPUT_PATTERN = re.compile(r'Output\[(\d+)\]')


def read_case(fh):
    # Set the initial state.

    lines = iter(fh)
    number = 0
    sections = []
    for line in lines:
        if line.startswith('#' * 6):
            line = next(lines).strip()
            if INPUT_PATTERN.search(line):
                match = INPUT_PATTERN.match(line)
                number = match.group(1)
                next(lines)
                sections.append([number, [], []])
                state = sections[-1][1]
            else:
                match = OUTPUT_PATTERN.match(line)
                assert match is not None
                assert match.group(1) == number
                next(lines)
                state = sections[-1][2]
        else:
            state.append(line.rstrip())

    return [{'number': number,
             'input': '\n'.join(program_input).strip(),
             'expected': '\n'.join(program_expected).strip()}
            for number, program_input, program_expected in sections]


CASE_FILES = sorted((HERE / 'cases').glob('case_*.txt'))


@pytest.mark.parametrize("case", range(1, len(CASE_FILES) + 1))
def test_case(case):
    case_file = CASE_FILES[case-1]

    with case_file.open('r') as fh:
        case = read_case(fh)

    g = FortranGatherer()

    correct = True
    first_fail = [None, None, None]
    actual = []

    for section in case:
        g.extend(section['input'])

        program = g.to_program()
        if program != section['expected']:
            if correct:
                first_fail = program, section['expected'], section['number']
            correct = False

        content = f"""\
########
Input[{ section['number'] }]
########

{ section['input'] }

########
Output[{ section['number'] }]
########

{ program }

"""
        actual.append(content)

    if not correct:
        actual_file = (case_file.parent /
                       f'actual_{ case_file.name}')
        with actual_file.open('w') as fh:
            fh.write('\n'.join(actual))

    assert first_fail[0] == first_fail[1], (
        'Mismatch for cell[{}]'.format(first_fail[2]))
