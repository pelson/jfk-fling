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
                next(lines)
                sections.append([number, [], []])
                state = sections[-1][1]
            else:
                match = OUTPUT_PATTERN.match(line)
                assert match is not None
                assert match.group(1) == number
                next(lines)
                next(lines)
                state = sections[-1][2]
        else:
            state.append(line.rstrip())

    return [{'number': number,
             'input': '\n'.join(program_input).strip(),
             'expected': '\n'.join(program_expected).strip()}
            for number, program_input, program_expected in sections]

@pytest.mark.parametrize("case_filename", sorted((HERE / 'cases').glob('case_*.txt')))
def test_case(case_filename):
    with open(case_filename, 'r') as fh:
        case = read_case(fh)
    
    g = FortranGatherer()

    correct = True
    first_fail = [None, None, None]
    actual = []

    hash_line = '#' * 8
    newline = ''

    for section in case:
        g.extend(section['input'])

        program = g.to_program()
        if program != section['expected']:
            if correct:
                first_fail = program, section['expected'], section['number']
            correct = False

        actual.extend([
            hash_line, 'Input[{}]'.format(section['number']), hash_line, newline])
        actual.extend([section['input'], newline])
        actual.extend([
            hash_line, 'Output[{}]'.format(section['number']), hash_line, newline])
        actual.extend([program, newline, newline])


    if not correct:
        with open(case_filename.parent / f'actual_{ case_filename.name}', 'w') as fh:
            fh.write('\n'.join(actual))

    assert first_fail[0] == first_fail[1], 'Mismatch for cell[{}]'.format(first_fail[2])


