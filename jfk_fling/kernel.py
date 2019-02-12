from ipykernel.kernelbase import Kernel
import tempfile
import os

from .realtime_subprocess import RealTimeSubprocess
from .fprogram import FortranGatherer


class FortranKernel(Kernel):
    implementation = 'jupyter_fortran_kernel'
    implementation_version = '0.1'
    language = 'Fortran'
    language_version = 'F2008'
    language_info = {'name': 'fortran',
                     'mimetype': 'text/plain',
                     'file_extension': '.f90'}
    banner = ("Fortran kernel.\n"
              "Uses gfortran, compiles in F2008, and creates source code "
              "files and executables in temporary folder.\n")

    # TODO:
    #  * Since we have all the definition nodes, implement autocomplete.
    #  * Look into ways of storing all variables, and then restoring them for
    #    execution (since we know the names of all variables from our node
    #    information).

    def __init__(self, *args, **kwargs):
        super(FortranKernel, self).__init__(*args, **kwargs)
        self.gatherer = FortranGatherer()
        self.files = []
        self.fragment_accumulator = []

    def cleanup_files(self):
        """Remove all the temporary files created by the kernel"""
        for file in self.files:
            os.remove(file)

    def new_temp_file(self, **kwargs):
        """Create a new temp file to be deleted when the kernel shuts down"""
        # We don't want the file to be deleted when closed, but only when
        # the kernel stops
        kwargs['delete'] = False
        kwargs['mode'] = 'w'
        file = tempfile.NamedTemporaryFile(**kwargs)
        self.files.append(file.name)
#        file = open(os.path.join(os.path.dirname(__file__), 'tmp.f90'), 'w')
#        self.files.append(file.name)
        return file

    def _write_to_stdout(self, contents):
        self.send_response(
            self.iopub_socket, 'stream', {'name': 'stdout', 'text': contents})

    def _write_to_stderr(self, contents):
        self.send_response(
            self.iopub_socket, 'stream', {'name': 'stderr', 'text': contents})

    def create_jupyter_subprocess(self, cmd):
        return RealTimeSubprocess(
            cmd,
            lambda contents: self._write_to_stdout(contents.decode()),
            lambda contents: self._write_to_stderr(contents.decode()))

    def compile_with_gfortran(self, source_filename, binary_filename):
        compiler = os.environ.get('FC', 'gfortran')
        fflags = os.environ.get('FFLAGS', '').split(' ')
        args = ([compiler, source_filename, '-std=f2008'] +
                fflags +
                ['-o', binary_filename])
        return self.create_jupyter_subprocess(args)

    def do_complete(self, code, cursor_pos):
        with self.new_temp_file(suffix='.f90') as source_file:
            source_file.write(code)
            source_file.flush()

        import fortls.langserver
        ls = fortls.langserver.LangServer(None)

        directory = os.path.abspath(os.path.dirname(source_file.name))
        request = {"params": {"rootPath": directory}}
        ls.serve_initialize(request)

        fname = os.path.abspath(source_file.name)
        # curr_pos is the character number of the multi-line string.
        split = code.split('\n')
        chars_seen = 0
        for line_number, line in enumerate(split):
            if cursor_pos <= chars_seen + len(line) + 1:
                break
            chars_seen += len(line) + 1  # (don't forget the newline)
        char = (cursor_pos - chars_seen)
        request = {
            "params": {
                "textDocument": {"uri": fname},
                "position": {"line": line_number, "character": char}}}

        response = ls.serve_autocomplete(request)

        matches = [item['label'] for item in response['items']]
        if matches:
            m = matches[0]
            for i in range(1, len(m)):
                if m[:i].lower() != line[char-i-1:char].lower():
                    break

            cursor_pos = cursor_pos - i + 1
        return {'matches': matches,
                'cursor_end': cursor_pos,
                'cursor_start': cursor_pos,
                'metadata': {},
                'status': 'ok'}

    def do_execute(self, code, silent, store_history=True,
                   user_expressions=None, allow_stdin=False):

        fragment = False
        if code.strip() == '%code':
            self._write_to_stdout(self.gatherer.to_program())
            resp = {
                'status': 'ok',
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {}}
            return resp
        elif code.strip() == '%clear':
            self.gatherer.clear()
            resp = {
                'status': 'ok',
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {}}
            return resp

        elif (code.strip().startswith('%fragment')
              or code.strip().startswith('%%fragment')):
            fragment = True
            _, code = code.split('%fragment', 1)
            self.fragment_accumulator.append(code)
            resp = {
                'status': 'ok',
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {}}
            return resp

        if self.fragment_accumulator:
            code = '\n'.join(self.fragment_accumulator + [code])
            self.fragment_accumulator = []

        try:
            self.gatherer.extend(code)
        except Exception as exception:
            msg = '[FAILED TO PARSE:] {}'.format(str(exception))
            self._write_to_stderr(msg)

            resp = {
                'status': 'ok',
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {}}
            return resp
        program_code = self.gatherer.to_program()
        with self.new_temp_file(suffix='.f90') as source_file:
            source_file.write(program_code)
            source_file.flush()
            if fragment:
                resp = {
                    'status': 'ok',
                    'execution_count': self.execution_count,
                    'payload': [],
                    'user_expressions': {}}
                return resp
            with self.new_temp_file(suffix='.out') as binary_file:
                p = self.compile_with_gfortran(
                    source_file.name, binary_file.name)
                while p.poll() is None:
                    p.write_contents()
                p.write_contents()
                if p.returncode != 0:  # Compilation failed
                    # Remove the most recently added sub-program.
                    del self.gatherer.programs[-1]
                    msg = ("[Fortran kernel] gfortran exited with code {}, "
                           "the executable will not be executed"
                           .format(p.returncode))
                    self._write_to_stderr(msg)
                    resp = {
                        'status': 'ok',
                        'execution_count': self.execution_count,
                        'payload': [],
                        'user_expressions': {}}
                    return resp

        p = self.create_jupyter_subprocess(binary_file.name)
        while p.poll() is None:
            p.write_contents()
        p.write_contents()

        if p.returncode != 0:
            # e.g. segfault...
            del self.gatherer.programs[-1]
            msg = ("[Fortran kernel] Executable exited with code {}"
                   "".format(p.returncode))
            self._write_to_stderr(msg)
        resp = {
            'status': 'ok',
            'execution_count': self.execution_count,
            'payload': [],
            'user_expressions': {},
        }
        return resp

    def do_shutdown(self, restart):
        # Cleanup the created source code files and executables when
        # shutting down the kernel.
        self.cleanup_files()
