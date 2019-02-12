from itertools import chain

import jinja2


class FVisitor:
    def visit(self, node):
        meth_name = 'visit_{}'.format(type(node).__name__)

        # Get the specific method for this type, else
        # use the generic one.
        method = getattr(self, meth_name, self.generic_visit)

        return method(node)

    def visit_children(self, node):
        # Call all the children of this node.
        if hasattr(node, 'content'):
            return [self.visit(child) for child in node.content]

    def generic_visit(self, node):
        # The fallback visitor method if there is no specific node
        # implementation.
        return self.visit_children(node)


class ComponentVisitor(FVisitor):
    pass_through_nodes = []

    @classmethod
    def process(cls, node):
        instance = cls()
        instance.visit(node)
        return instance

    def generic_visit(self, node):
        name = node.__class__.__name__
        if name not in self.pass_through_nodes:
            raise RuntimeError(
                'Unhandled {} type {}'.format(
                    self.__class__.__name__,
                    node.__class__.__name__))
        else:
            self.visit_children(node)


class Program(ComponentVisitor):
    """
    Represents a whole ".f90" file. (R201)

    """
    pass_through_nodes = ['Program']

    def __init__(self):
        self.definitions = []
        self.modules = []
        self.main_program = MainProgram()

    def visit_Main_Program(self, node):
        self.main_program.visit(node)

    def visit_Subroutine_Subprogram(self, node):
        self.definitions.append(node)

    def visit_Function_Subprogram(self, node):
        self.definitions.append(node)

    def visit_Module(self, node):
        self.modules.append(node)

    @classmethod
    def combine(cls, programs):
        prg = Program()
        for program in programs:
            prg.modules.extend(program.modules)
            prg.definitions.extend(program.definitions)
        prg.main_program = MainProgram.combine(
            [program.main_program for program in programs])
        return prg


class MainProgram(ComponentVisitor):
    """
    Represents a ``PROGRAM..END PROGRAM`` block. (R1101)

    """
    pass_through_nodes = ['End_Program_Stmt', 'Contains_Stmt', 'Main_Program',
                          'Internal_Subprogram_Part']

    def __init__(self):
        super().__init__()
        self.name = 'main'
        self.specification = Specification()
        self.executions = []
        self.internal_subprogram = []

    def visit_Program_Stmt(self, node):
        self.name = str(node.items[1])
        self.visit_children(node)

    def visit_Specification_Part(self, node):
        self.specification.visit(node)

    def visit_Execution_Part(self, node):
        self.executions.append(node)

    def visit_Function_Subprogram(self, node):
        self.internal_subprogram.append(node)

    def visit_Subroutine_Subprogram(self, node):
        self.internal_subprogram.append(node)

    @classmethod
    def combine(cls, programs):
        program = cls()
        program.specification = Specification.combine(
            [prog.specification for prog in programs])
        for prog in programs:
            program.executions.extend(prog.executions)
            program.internal_subprogram.extend(prog.internal_subprogram)
            # We use the last name seen for the program.
            program.name = prog.name
        return program


class Specification(ComponentVisitor):
    """
    Represents a specification-construct (R204)

    """
    pass_through_nodes = ['Specification_Part', 'Implicit_Part']

    def __init__(self):
        # Note: all attributes must be handled in the `.combine`
        # class method also.
        self.use_nodes = []
        self.implicit_nodes = []
        self.type_decl_nodes = []
        self.derived_type_nodes = []

    def visit_Type_Declaration_Stmt(self, node):
        self.type_decl_nodes.append(node)

    def visit_Implicit_Stmt(self, node):
        self.implicit_nodes.append(node)

    def visit_Use_Stmt(self, node):
        self.use_nodes.append(node)

    def visit_Derived_Type_Def(self, node):
        self.derived_type_nodes.append(node)

    def __str__(self):
        NEWLINE = ['']
        nodes = (self.use_nodes +
                 self.implicit_nodes +
                 NEWLINE +
                 self.derived_type_nodes +
                 NEWLINE +
                 self.type_decl_nodes)
        return '\n'.join(str(node) for node in nodes)

    @classmethod
    def combine(cls, visitors):
        spec = cls()
        for specification in visitors:
            spec.use_nodes.extend(specification.use_nodes)
            spec.implicit_nodes.extend(specification.implicit_nodes)
            # TODO: We could do more here, like make sure we aren't
            # redefining entities.
            spec.type_decl_nodes.extend(specification.type_decl_nodes)
            spec.derived_type_nodes.extend(specification.derived_type_nodes)

        # Drop all implicit nodes except the last.
        if len(spec.implicit_nodes) > 1:
            spec.implicit_nodes = spec.implicit_nodes[-1:]
        return spec


def rstrip_lines(string):
    lines = [line.rstrip() for line in string.split('\n')]
    return '\n'.join(lines)


PROGRAM_TEMPLATE = """
{{ modules }}
{{ program.definitions|join('\n')|string }}

PROGRAM {{ main_prog.name }}
  {{ main_prog.specification|string|indent(2) }}

{% if prev_main_prog.executions %}
  ! Redirect stdout to /dev/null for old statements
  OPEN(unit=6, file="/dev/null", status="old")

  {{ prev_main_prog.executions|join('\n')|indent(2) }}

  ! Re-enable stdout for new statements
  OPEN(unit=6, file="/dev/stdout", status="old")
{%- endif %}

{% if this_main_prog.executions %}
  {{ this_main_prog.executions|join('\n')|indent(2) }}
{% endif %}

{% if main_prog.internal_subprogram %}
  CONTAINS
    {{ main_prog.internal_subprogram|join('\n\n')|indent(4) }}
{%- endif %}
END PROGRAM {{ main_prog.name }}
"""


class FortranGatherer:
    """
    A fortran parse tree visitor that separates all
    statements from "definition blocks".

    """
    def __init__(self):
        self.programs = []

    def extend(self, snippet):
        from fparser.two.parser import ParserFactory
        from fparser.common.readfortran import FortranStringReader

        source = """
        PROGRAM main
        contains  ! NOTE: I'm exploiting a bug here.
                  ! :( https://github.com/stfc/fparser/issues/136
            {}
        END PROGRAM main
        """.format(snippet).strip()

        parser = ParserFactory().create(std="f2008")
        try:
            reader = FortranStringReader(source)
            program = parser(reader)
        except Exception:  # FortranSyntaxError
            reader = FortranStringReader(snippet)
            program = parser(reader)

        cell_prog = Program.process(program)
        self.programs.append(cell_prog)

    def clear(self, ):
        del self.programs[:]

    def template_context(self):
        main_programs = [prog.main_program for prog in self.programs]

        main_prog = MainProgram.combine(main_programs)
        prev_main_prog = MainProgram.combine(main_programs[:-1])
        this_main_prog = MainProgram.combine(main_programs[-1:])

        prev_program = Program.combine(self.programs[:-1])
        # Combine like this as self.programs could be empty.
        current_program = Program.combine(self.programs[-1:])
        program = Program.combine([prev_program, current_program])

        modules = '\n'.join(
            str(node) for node in chain.from_iterable(
                [prog.modules for prog in self.programs]))

        return dict(
            program=program,
            current_program=current_program,
            prev_main_prog=prev_main_prog,
            this_main_prog=this_main_prog,
            modules=modules,
            main_prog=main_prog,
        )

    def to_program(self):
        template = jinja2.Environment(
            loader=jinja2.BaseLoader).from_string(PROGRAM_TEMPLATE)

        prog = template.render(**self.template_context())

        # Rather than trying to implement a perfect whitespace Jinja2
        # template we post-process the result, stripping out spurious
        # whitespace as much as possible.
        prog = rstrip_lines(prog)
        while '\n\n\n' in prog:
            prog = prog.replace('\n\n\n', '\n\n')
        prog = prog.strip()

        return prog
