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
        self.definition_nodes = []
        self.modules = []
        self.program = MainProgram()

    def visit_Main_Program(self, node):
        self.program.visit(node)

    def visit_Subroutine_Subprogram(self, node):
        self.definition_nodes.append(node)

    def visit_Function_Subprogram(self, node):
        self.definition_nodes.append(node)

    def visit_Module(self, node):
        self.modules.append(node)


class MainProgram(ComponentVisitor):
    """
    Represents a PROGRAM..END PROGRAM block. (R1101)

    """
    pass_through_nodes = ['End_Program_Stmt', 'Contains_Stmt']

    def __init__(self):
        super().__init__()
        self.name = None
        self.definitions = []
        self.specification = SpecificationVisitor()
        self.executions = []
        self.internal_subprogram = []

    def visit_Program_Stmt(self, node):
        # Call the super class version of generic_visit (the one
        # that doesn't raise!)
        print('FOO!', node.use_names)
        self.visit_children(node)

    def visit_Main_Program(self, node):
        self.name = node.string
        self.visit_children(node)

    def visit_Specification_Part(self, node):
        self.specification.visit(node)

    def visit_Execution_Part(self, node):
        self.executions.append(node)

    def visit_Internal_Subprogram_Part(self, node):
        self.visit_children(node)

    def visit_Function_Subprogram(self, node):
        self.internal_subprogram.append(node)

    def visit_Subroutine_Subprogram(self, node):
        self.internal_subprogram.append(node)

    @classmethod
    def combine(cls, programs):
        program = cls()
        program.specification = SpecificationVisitor.combine(
            [prog.specification for prog in programs])
        for prog in programs:
            program.definitions.extend(prog.definitions)
            program.executions.extend(prog.executions)
            program.internal_subprogram.extend(prog.internal_subprogram)
        return program


class SpecificationVisitor(ComponentVisitor):
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

PROGRAM main
  {{ program.specification|string|indent(2) }}

{% if previous_program.executions %}
  ! Redirect stdout to /dev/null for old statements
  OPEN(unit=6, file="/dev/null", status="old")

  {{ previous_program.executions|join('\n')|indent(2) }}

  ! Re-enable stdout for new statements
  OPEN(unit=6, file="/dev/stdout", status="old")
{%- endif %}

{% if this_program.executions %}
  {{ this_program.executions|join('\n')|indent(2) }}
{% endif %}

{% if program.internal_subprogram %}
  CONTAINS
    {{ program.internal_subprogram|join('\n\n')|indent(4) }}
{%- endif %}
END PROGRAM main
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
        PROGRAM tmp_prog
        contains  ! NOTE: I'm exploiting a bug here.
                  ! :( https://github.com/stfc/fparser/issues/136
            {}
        END PROGRAM tmp_prog
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

    def to_program(self):
        template = jinja2.Environment(
            loader=jinja2.BaseLoader).from_string(PROGRAM_TEMPLATE)

        program = MainProgram.combine(
            [prog.program for prog in self.programs])
        previous_program = MainProgram.combine(
            [prog.program for prog in self.programs[:-1]])

        # Note: self.programs could be empty.
        this_program = self.programs[-1:]
        if this_program:
            this_program = this_program[0].program
        else:
            this_program = MainProgram()

        modules = '\n'.join(
            str(node) for node in chain.from_iterable(
                [prog.modules for prog in self.programs]))

        prog = template.render(
            program=program,
            previous_program=previous_program,
            this_program=this_program,
            modules=modules,
            )
        # Rather than trying to implement a perfect whitespace Jinja2
        # template we post-process the result, stripping out spurious
        # whitespace as much as possible.
        prog = rstrip_lines(prog)
        while '\n\n\n' in prog:
            prog = prog.replace('\n\n\n', '\n\n')
        prog = prog.strip()

        return prog
