import sublime
import sublime_plugin
import re

def md(*msgs, **kwargs):
    sublime.message_dialog(kwargs.get('sep', ' ').join([str(msg) for msg in msgs]))

class StdClass(object):
    pass

class MarkdownKeyboardRunCommand(sublime_plugin.TextCommand):


    is_numbered_list = re.compile(r'[0-9]+\. .*')



    def list(self):

        def increment_line(line):
            nb, line = line.split('.', 1)
            return str(int(nb) + 1) + '.' + line

        regions = self.view.sel()
        for region in regions:
            line = StdClass()
            line.region = self.view.line(region)
            line.text = self.view.substr(line.region)
            char = line.text[0]
            ordered_list = False


            i = 0
            while char in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'] and i < 10:
                i += 1
                char = line.text[i]
                ordered_list = True
            if ordered_list is True:
                char = str(int(line.text[0:i]) + 1) + '.'

            if len(line.text.strip()) == len(char):
                # remove last list element because empty
                self.view.run_command('edit_replace', {
                    'region': (line.region.a, line.region.b),
                    'text': '\n'
                })
            else:

                # add list element
                prefix = char + ' '
                self.view.run_command('edit_insert', {
                    "point": line.region.end(),
                    "text": '\n' + prefix
                })
                self.reorder_list()
                # self.view.selection.clear()
                # self.view.selection.add(line.region.end())

    def reorder_list(self):
        regions = self.view.sel()
        for region in regions:
            if 'markup.list.numbered.markdown' not in \
                                          self.view.scope_name(region.begin()):
                return
            lines = self.view.extract_scope(region.begin())
            lines = self.view.split_by_newlines(lines)
            for i, line in enumerate(lines, 1):
                line = self.view.line(line)
                if line.empty():
                    continue
                nb, content = self.view.substr(line).split('.', 1)
                new_line = '{}.{}'.format(i, content)
                self.view.run_command('edit_replace', {
                    'region': [line.a, line.b],
                    'text': new_line
                })

            # self.view.selection.add_all(lines)





    def run(self, edit, command=None):
        # self.sel =
        if command is None:
            return sublime.error_message('the command cannot be None')
        if not isinstance(command, str):
            return sublime.error_message('The command must be a string, not a {}'.format(command.__class__.__name__))

        try:
            command_to_run = getattr(self, command)
        except AttributeError:
            return sublime.error_message("The command '{}' is unknown.".format(command))

        command_to_run()