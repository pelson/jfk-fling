from ipykernel.kernelbase import Kernel
import tempfile
import os

from .realtime_subprocess import RealTimeSubprocess
from .fprogram import FortranGatherer


class FortranKernel(Kernel):
    implementation = 'jfk-fling'
    implementation_version = '0.1'
    language = 'Fortran'
    language_version = 'F2008'
    language_info = {'name': 'fortran',
                     'mimetype': 'text/plain',
                     'file_extension': '.f90'}
    banner = ("Fortran kernel.\n"
              "Uses $FC, compiles in F2008, and creates source code "
              "files and executables in temporary folder.\n")

    def __init__(self, *args, **kwargs):
        super(FortranKernel, self).__init__(*args, **kwargs)
        self.gatherer = FortranGatherer()
        self.files_for_cleanup = []
        self.fragment_accumulator = []

    def cleanup_files(self):
        """Remove all the temporary files created by the kernel"""
        for fname in self.files_for_cleanup:
            os.remove(fname)

    def new_temp_file(self, **kwargs):
        """Create a new temp file to be deleted when the kernel shuts down"""
        fh = tempfile.NamedTemporaryFile(delete=False, mode='w', **kwargs)
        self.files_for_cleanup.append(fh.name)
        return fh

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

    def split_magics(self, code):
        code_lines = []
        magics = []
        lines = code.split('\n')

        state = 'magics'
        for line in lines:
            if state == 'magics':
                if line.startswith('%'):
                    magics.append(line.lstrip('%'))
                    continue
                elif not line:
                    continue
            state = 'code'
            code_lines.append(line)
        return magics, '\n'.join(code_lines) 

    def do_execute(self, code, silent, store_history=True,
                   user_expressions=None, allow_stdin=False):
        response_template = {
            'status': 'ok', 'execution_count': self.execution_count,
            'payload': [], 'user_expressions': {}}

        fragment = False
        magics, code = self.split_magics(code)

        if 'code' in magics:
            if code.strip():
                self._write_to_stderr(
                    'The %code magic must not have code body.') 
            self._write_to_stdout(self.gatherer.to_program())
            return response_template
        elif 'clear' in magics:
            self.gatherer.clear()

        elif 'fragment' in magics:
            fragment = True
            self.fragment_accumulator.append(code)
            return response_template

        if self.fragment_accumulator:
            code = '\n'.join(self.fragment_accumulator + [code])
            self.fragment_accumulator = []

        try:
            self.gatherer.extend(code)
        except Exception as exception:
            msg = '[FAILED TO PARSE:] {}'.format(str(exception))
            self._write_to_stderr(msg)
            return response_template

        program_code = self.gatherer.to_program()
        with self.new_temp_file(suffix='.f90') as source_file:
            source_file.write(program_code)
            source_file.flush()
            if fragment:
                return response_template
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
                    return response_template

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
        return response_template

    def do_shutdown(self, restart):
        # Cleanup the created source code files and executables when
        # shutting down the kernel.
        self.cleanup_files()
