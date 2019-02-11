from jfk_fling.fprogram import FortranGatherer


program = """
program hello
   implicit none
   print*, "Hello, World!"
end program
"""

expected = """
PROGRAM main
  IMPLICIT NONE

  PRINT *, "Hello, World!"

END PROGRAM main
""".strip()

def test_program():
    p = FortranGatherer()
    p.extend(program)
    print(p.to_program())
    assert p.to_program() == expected
