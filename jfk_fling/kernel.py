from ipykernel.kernelbase import Kernel
import subprocess
import tempfile
import os
import os.path as path


from .realtime_subprocess import RealTimeSubprocess


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


class FortranGatherer(FVisitor):
    """
    A fortran parse tree visitor that separates all
    statements from "definition blocks".

    """
    def __init__(self):
        self.statement_nodes = []
        self.definition_nodes = []

    def extend(self, snippet):
        from fparser.two.parser import ParserFactory
        from fparser.common.readfortran import FortranStringReader

        source = """
        PROGRAM tmp_prog
            {}
        END PROGRAM tmp_prog
        """.format(snippet).strip()

        reader = FortranStringReader(source)
        parser = ParserFactory().create(std="f2008")
        program = parser(reader)
        self.visit(program)

    def to_program(self):
        TEMPLATE = """
PROGRAM main

{statements}
  
CONTAINS

{definitions}

END PROGRAM main
""".strip()
        import textwrap
        statements = '\n'.join(str(node) for node in self.statement_nodes)
        definitions = '\n'.join(str(node) for node in self.definition_nodes)

        prog = TEMPLATE.format(
            statements=textwrap.indent(statements, '  '),
            definitions=textwrap.indent(definitions, '  '))

        return prog

    def generic_visit(self, node):
        print(node.__class__.__name__)
        return super().generic_visit(node)

    def visit_Subroutine_Subprogram(self, node):
        self.definition_nodes.append(node)

    def visit_Execution_Part(self, node):
        self.statement_nodes.append(node)


class FortranKernel(Kernel):
    implementation = 'jupyter_fortran_kernel'
    implementation_version = '0.1'
    language = 'Fortran'
    language_version = 'F2008'
    language_info = {'name': 'fortran',
                     'mimetype': 'text/plain',
                     'file_extension': 'f90'}
    banner = "Fortran kernel.\n" \
             "Uses gfortran, compiles in F2008, and creates source code files and executables in temporary folder.\n"

    def __init__(self, *args, **kwargs):
        super(FortranKernel, self).__init__(*args, **kwargs)
        self.gatherer = FortranGatherer()
        self.files = []

    def cleanup_files(self):
        """Remove all the temporary files created by the kernel"""
        for file in self.files:
            os.remove(file)

    def new_temp_file(self, **kwargs):
        """Create a new temp file to be deleted when the kernel shuts down"""
        # We don't want the file to be deleted when closed, but only when the kernel stops
        kwargs['delete'] = False
        kwargs['mode'] = 'w'
        file = tempfile.NamedTemporaryFile(**kwargs)
        self.files.append(file.name)
        return file

    def _write_to_stdout(self, contents):
        self.send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': contents})

    def _write_to_stderr(self, contents):
        self.send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': contents})

    def create_jupyter_subprocess(self, cmd):
        return RealTimeSubprocess(cmd,
                                  lambda contents: self._write_to_stdout(contents.decode()),
                                  lambda contents: self._write_to_stderr(contents.decode()))

    def compile_with_gfortran(self, source_filename, binary_filename):
        args = ['gfortran', source_filename, '-std=f2008', '-o', binary_filename]
        return self.create_jupyter_subprocess(args)

    def do_execute(self, code, silent, store_history=True,
                   user_expressions=None, allow_stdin=False):

        self.gatherer.extend(code)
        code = self.gatherer.to_program()
        with self.new_temp_file(suffix='.f90') as source_file:
            source_file.write(code)
            source_file.flush()
            with self.new_temp_file(suffix='.out') as binary_file:
                p = self.compile_with_gfortran(source_file.name, binary_file.name)
                while p.poll() is None:
                    p.write_contents()
                p.write_contents()
                if p.returncode != 0:  # Compilation failed
                    self._write_to_stderr(
                            "[Fortran kernel] gfortran exited with code {}, the executable will not be executed".format(
                                    p.returncode))
                    return {'status': 'ok', 'execution_count': self.execution_count, 'payload': [],
                            'user_expressions': {}}

        p = self.create_jupyter_subprocess(binary_file.name)
        while p.poll() is None:
            p.write_contents()
        p.write_contents()

        if p.returncode != 0:
            self._write_to_stderr("[Fortran kernel] Executable exited with code {}".format(p.returncode))
        return {'status': 'ok', 'execution_count': self.execution_count, 'payload': [], 'user_expressions': {}}

    def do_shutdown(self, restart):
        """Cleanup the created source code files and executables when shutting down the kernel"""
        self.cleanup_files()
