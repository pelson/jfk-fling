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
