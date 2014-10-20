"""
Terminator plugin to open grep output using a chosen editor.
Currently supports gvim and gedit.

Author: michele.silva@gmail.com
License: GPLv2
"""
import inspect, os, re, shlex, subprocess
from terminatorlib import plugin
from terminatorlib import config

AVAILABLE = ['GrepPlugin']
DEFAULT_COMMAND = 'gvim --remote-silent +{line} {filepath}'
DEFAULT_PATTERN = r'(?P<file>[^\s:/.]+[/.][^\s:]+)(?::(?P<line>[0-9]+))?'


class GrepPlugin(plugin.URLHandler):
    """ Process URLs returned by the grep command. """
    capabilities = ['url_handler']
    handler_name = 'grepurl'
    nameopen = 'Open File'
    namecopy = 'Copy Open Command'
    match = None

    def __init__(self):
        self.plugin_name = self.__class__.__name__
        self.current_path = None
        self.config = config.Config()
        settings = self.config.plugin_get_config(self.plugin_name)
        if not settings or 'command' not in settings or 'pattern' not in settings:
            settings = {
              'command': DEFAULT_COMMAND,
              'pattern': DEFAULT_PATTERN,
            }
            self.config.plugin_set_config(self.plugin_name, settings)
            self.config.save()

        self.match = self.config.plugin_get(self.plugin_name, 'pattern')
        # terminator regex doesn't support `(?:...)` or `(?P<name>...)` so we hack it (ugly).
        self.match = re.sub(r'\(\?:', '(', self.match)
        self.match = re.sub(r'\(\?P<[^>]+>', '(', self.match)
        # Actually it doesn't support \X either.
        self.match = self.match.replace(r'\r', '\r')
        self.match = self.match.replace(r'\n', '\n')
        self.match = self.match.replace(r'\t', '\t')
        self.match = self.match.replace(r'\v', '\v')
        self.match = self.match.replace(r'\f', '\f')
        self.match = self.match.replace(r'\s', ' \t\f\v\n\r')
        self.match = self.match.replace(r'\d', '[0-9]')
        self.match = self.match.replace(r'\w', '[a-zA-Z_-]')

    def get_cwd(self):
        """ Return current working directory. """
        # HACK: Because the current working directory is not available to plugins,
        # we need to use the inspect module to climb up the stack to the Terminal
        # object and call get_cwd() from there.
        for frameinfo in inspect.stack():
            frameobj = frameinfo[0].f_locals.get('self')
            if frameobj and frameobj.__class__.__name__ == 'Terminal':
                return frameobj.get_cwd()
        return None

    def open_url(self):
        """ Return True if we should open the file. """
        # HACK: Because the plugin doesn't tell us we should open or copy
        # the command, we need to climb the stack to see how we got here.
        return inspect.stack()[3][3] == 'open_url'

    def callback(self, strmatch):
        pattern = self.config.plugin_get(self.plugin_name, 'pattern')
        for match in re.finditer(pattern, strmatch):

            # Get the full path.
            filepath = match.group('file')
            if not filepath:
                continue
            filepath = os.path.join(self.get_cwd(), filepath)

            # Get the line number.
            lineno = match.group('line')
            if not lineno:
                lineno = '0'

            # Continue only if the file exists
            if not os.path.exists(filepath):
                continue

            # Generate the openurl string
            command = self.config.plugin_get(self.plugin_name, 'command')
            command = command.replace('{filepath}', filepath)
            command = command.replace('{line}', lineno)

            # Check we are opening the file
            if self.open_url():
                subprocess.call(shlex.split(command))
                return '--version'
            return command

        return None

