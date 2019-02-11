from jfk_fling.fprogram import FortranGatherer


program = """
MODULE my_mod
contains
    integer function square(number)
        integer, intent(in) :: number
        square = number * number
    end function
END MODULE my_mod

PROGRAM main
    use funcs
    implicit none
    
    integer :: x
    
    x = 7
    write(*, '(a,i4)') "x   =", x
    write(*, '(a,i4)') "x^2 =", square(x)
END PROGRAM main
"""


output = """
MODULE my_mod
  CONTAINS
  INTEGER FUNCTION square(number)
    INTEGER, INTENT(IN) :: number
    square = number * number
  END FUNCTION
END MODULE my_mod

MODULE main_mod
  USE funcs

  INTEGER :: x

END MODULE main_mod


PROGRAM main
  USE main_mod
  IMPLICIT NONE

  x = 7
  WRITE(*, FMT = '(a,i4)') "x   =", x
  WRITE(*, FMT = '(a,i4)') "x^2 =", square(x)
END PROGRAM main
""".strip()


def test_program():
    p = FortranGatherer()
    p.extend(program)
    print(p.to_program())
    assert p.to_program() == output
