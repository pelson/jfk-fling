import jinja2



class FVisitor:
    def visit(self, node):
        meth_name = 'visit_{}'.format(type(node).__name__)

        # Get the specific method for this type, else
        # use the generic one.
        method = getattr(self, meth_name, self.generic_visit)

        return method(node)

    def generic_visit(self, node):
        # Call all the children of this node.
        if hasattr(node, 'content'):
            return [self.visit(child) for child in node.content]
        else:
            return self.visit_generic_terminal_node(node)

    def visit_generic_terminal_node(self, node):
        pass


class DeleteNodeType(FVisitor):
    def __init__(self, delete_types):
        self.delete_types = delete_types

    def children(self, node):
        # Depending on their level in the tree produced by fparser2003,
        # some nodes have children listed in .content and some have them
        # listed under .items. If a node has neither then it has no
        # children.
        if hasattr(node, "content"):
            return node.content
        elif hasattr(node, "items"):
            return node.items
        else:
            return []

    def generic_visit(self, node):
        name = node.__class__.__name__
        children = self.children(node)
        for child in children[:]:
            if name in self.delete_types:
                print('DROPPING:', child)
                print(dir(child))
                print(child.__dict__)
                # children.remove(child)
                child.string = ''
                # child.items = ('foo',)
                import fparser.two.Fortran2003
                idx = children.index(child)
#                children[idx] = fparser.two.Fortran2003.Comment('')
        super().generic_visit(node)


class ProgramVisitor(FVisitor):
    def __init__(self):
        super().__init__()
        self.name = None
        self.definitions = []
        self.specification = SpecificationVisitor()
        self.executions = None

    def generic_visit(self, node):
        raise RuntimeError(str(node.__class__.__name__))

    def visit_Program_Stmt(self, node):
        # Call the super class version of generic_visit (the one
        # that doesn't raise!)
        print('FOO!', node.use_names)
        super().generic_visit(node)

    def visit_Main_Program(self, node):
        self.name = node.string
        super().generic_visit(node)

    def visit_Specification_Part(self, node):
        self.specification.visit(node)

    def visit_Execution_Part(self, node):
        self.executions = node

    def visit_End_Program_Stmt(self, node):
        pass


class SpecificationVisitor(FVisitor):
    def __init__(self):
        self.use_nodes = []
        self.implicit_nodes = []
        self.type_decl_nodes = []

    def visit_Type_Declaration_Stmt(self, node):
        self.type_decl_nodes.append(node)

    def visit_Implicit_Stmt(self, node):
        self.implicit_nodes.append(node)

    def visit_Use_Stmt(self, node):
        self.use_nodes.append(node)

    def __str__(self):
        return '\n'.join(str(node) for node in (self.use_nodes + self.implicit_nodes + [''] + self.type_decl_nodes))

    @classmethod
    def combine(cls, visitors):
        spec = cls()
        for specification in visitors:
            spec.use_nodes.extend(specification.use_nodes)
            spec.implicit_nodes.extend(specification.implicit_nodes)
            # TODO: We could do more here, like make sure we aren't
            # redefining entities.
            spec.type_decl_nodes.extend(specification.type_decl_nodes)

        # TODO: We need to have only one implicit node.
        if len(spec.implicit_nodes) > 1:
            spec.implicit_nodes = spec.implicit_nodes[-1:]
        return spec

def combine_programs(programs):
    prog = ProgramTransaction()
    for program in programs:
        prog.statement_nodes.extend(program.statement_nodes)
    return prog


class ProgramTransaction(FVisitor):
    # Represents a cell's statements and definitions.
    def __init__(self):
        self.statement_nodes = []
        self.definition_nodes = []
        self.spec_nodes = []
        self.modules = []
        self.prog_preamble = []
        self.program = ProgramVisitor()

    def generic_visit(self, node):
        pass_through_nodes = [
            'Program', 'Main_Program', 'Program_Stmt',
            'Internal_Subprogram_Part', 'Execution_Part',
            'End_Program_Start', 'End_Program_Stmt',
            'Contains_Stmt',
        ]
        this_node = node.__class__.__name__
        if this_node not in pass_through_nodes:
            raise RuntimeError('Unhandled node type {}'.format(this_node))
        return super().generic_visit(node)

    def visit_Main_Program(self, node):
        self.program.visit(node)

    def visit_Subroutine_Subprogram(self, node):
        self.definition_nodes.append(node)

    def visit_Function_Subprogram(self, node):
        self.definition_nodes.append(node)

    def visit_Specification_Part(self, node):
        # Don't use fparser.two.utils.walk_ast here as we need to
        # modify the node.
        DeleteNodeType(['Implicit_Part']).visit(node)
        self.spec_nodes.append(node)

    def visit_Execution_Part(self, node):
        # Note: We could drill down here (Print_Stmt, Assignment_Stmt) if
        # we need more context (like which variables are being definied).
        self.statement_nodes.append(node)

    def visit_Type_Declaration_Stmt(self, node):
        self.statement_nodes.append(node)

    def visit_Module(self, node):
        self.modules.append(node)


class ClassPrinter(FVisitor):
    def generic_visit(self, node):
        print('-------------\n\n\n{}:\n\n{}'
              ''.format(node.__class__.__name__, str(node)))
        return super().generic_visit(node)


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

        cell_prog = ProgramTransaction()
        cell_prog.visit(program)
        self.programs.append(cell_prog)

    def clear(self, ):
        del self.programs[:]

    def to_program(self):
        TEMPLATE = """
{{modules}}

PROGRAM main
  {{ specifications|string|indent(2) }}

{% if statements %}
  ! Redirect stdout to /dev/null for old statements
  OPEN(unit=6, file="/dev/null", status="old")

  {{statements|indent(2)}}

  ! Re-enable stdout for new statements
  OPEN(unit=6, file="/dev/stdout", status="old")
{%- endif %}
{% if new_statements %}
  {{ new_statements|indent(2) }}
{% endif %}

{% if definitions -%}
CONTAINS
  {{ definitions|indent(2) }}
{%- endif %}


END PROGRAM main
""".strip()

        template = jinja2.Environment(
            loader=jinja2.BaseLoader).from_string(TEMPLATE)

        import textwrap
        from itertools import chain

        # Note we have to do more to join spec parts (use, implicit, defn)
        specifications = SpecificationVisitor.combine(
            [prog.program.specification for prog in self.programs])
        statements = '\n'.join(
            str(node) for node in chain.from_iterable(
                [prog.statement_nodes for prog in self.programs[:-1]]))

        new_statements = '\n'.join(
            str(node) for node in chain.from_iterable(
                [prog.statement_nodes for prog in self.programs[-1:]]))
        definitions = '\n'.join(
            str(node) for node in chain.from_iterable(
                [prog.definition_nodes for prog in self.programs]))
        modules = '\n'.join(
            str(node) for node in chain.from_iterable(
                [prog.modules for prog in self.programs]))

        prog = template.render(
            specifications=specifications,
            statements=statements,
            new_statements=new_statements,
            definitions=definitions,
            modules=modules,
            )
        while '\n\n\n' in prog:
            prog = prog.replace('\n\n\n', '\n\n')
        prog = prog.strip()

        return prog
