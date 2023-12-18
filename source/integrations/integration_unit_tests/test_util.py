import io


class MockParamiko:
    stdin_string = 'message\n'
    stdout_string = 'message\n'
    stderr_string = ''

    def connect(self, hostname, username, pkey):
        return

    def close(self):
        return

    def exec_command(self, command):
        stdin = io.StringIO(self.stdin_string)
        stdout = io.StringIO(self.stdout_string)
        stderr = io.StringIO(self.stderr_string)

        return stdin, stdout, stderr
