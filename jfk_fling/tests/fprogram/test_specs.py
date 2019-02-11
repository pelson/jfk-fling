from jfk_fling.fprogram import FortranGatherer


def test_spec():
    g = FortranGatherer()
    g.extend("""
    PROGRAM main
        use foo
        implicit none
        
        INTEGER :: x

    END PROGRAM main
    """)

    g.extend("""
    PROGRAM main
        use bar
        implicit None
        
        INTEGER :: y

    END PROGRAM main
    """)

    expected = """
PROGRAM main
  USE foo
  USE bar
  IMPLICIT NONE

  INTEGER :: x
  INTEGER :: y

END PROGRAM main
""".strip()
    assert g.to_program() == expected



def test_internal_proc():
    g = FortranGatherer()
    g.extend("""
    PROGRAM main
    CONTAINS
        subroutine foo
            print*, 'Foo'
        end subroutine foo
    END PROGRAM main
    """)
    g.extend("""
    PROGRAM main
    CONTAINS
        subroutine bar
            print*, 'Foo'
        end subroutine bar
    END PROGRAM main
    """)
    expected = """
PROGRAM main

CONTAINS

  CONTAINS
  SUBROUTINE foo
    PRINT *, 'Foo'
  END SUBROUTINE foo

  CONTAINS
  SUBROUTINE bar
    PRINT *, 'Foo'
  END SUBROUTINE bar

END PROGRAM main
    """.strip()
    print(g.to_program())
    assert g.to_program() == expected


