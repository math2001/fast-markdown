import sublime
import sublime_plugin
import re
import sys

class StdClass(object):
    pass

def md(*msgs, **kwargs):
    sublime.message_dialog(kwargs.get('sep', ' ').join([str(msg) for msg in msgs]))

def em(*msgs, **kwargs):
    sublime.error_message(kwargs.get('sep', ' ').join([str(msg) for msg in msgs]))


def replace(view, region, text):
    if isinstance(region, sublime.Region):
        region = [region.a, region.b]
    view.run_command('edit_replace', {
        'region': region,
        'text': text
    })

def insert(view, point, text):
    view.run_command('edit_insert', {
        'point': point,
        'text': text
    })



class FastMarkdownCommand(sublime_plugin.TextCommand):


    list_prefix = re.compile(r'[0-9\-\*\+]\.?$')
    numbered_list_prefix = re.compile(r'[0-9]+\. .*')

    unordered_sign = ['*', '+', '-']
    ordered_sign = ['#']

    def list_(self) -> None:

        """ This function is called when enter is pressed in a list. """

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

            sub_list_prefix = self.is_list_prefix.search(line.text)

            line.text = self.convert_indentation(line.text)
            # remove last list element because empty
            if len(line.text.rstrip()) == len(char):
                self.view.run_command('edit_replace', {
                    'region': (line.region.a, line.region.b),
                    'text': '\n'
                })
            elif sub_list_prefix:
                sub_list_prefix = sub_list_prefix.group(0)
                self.view.run_command('edit_replace', {
                    "region": [line.region.end() - 1, line.region.end()],
                    "text": '\n\t' + sub_list_prefix + ' '
                })
                # sub_list_prefix = ''
            else:
                if not ordered_list and char not in ['*', '-', '+']:
                    return sublime.error_message("the char must be '*', '-' or '+'. Got {} instead".format(repr(char)))
                # add list element
                prefix = char + ' '
                self.view.run_command('edit_insert', {
                    "point": line.region.end(),
                    "text": '\n' + prefix
                })
                self.reorder_list()
                # self.view.selection.clear()
                # self.view.selection.add(line.region.end())

    def list(self) -> None:

        """ This function is called when enter is pressed in a list. """
        regions = self.view.sel()
        for region in regions:
            line = StdClass()
            line.region = self.view.line(region)
            line.text = self.convert_indentation(self.view.substr(line.region))
            line.indentation = self.get_indentation(line.text)
            if self.list_prefix.match(line.text.strip()):
                # remove element because the line is empty
                if line.indentation == 0:
                    replace(self.view, line.region, '\n')
                else:
                    list_prefix = self.get_sign_for(line.indentation, line.region.end())
                    if list_prefix.isdigit():
                        list_prefix = str(int(list_prefix) + 1) + '.'
                    replace(self.view, line.region, '{}{} '.format('\t' * (line.indentation - 1), list_prefix))

            elif line.text[-1] in self.unordered_sign + self.ordered_sign and line.text[-2] == ' ':
                # insert a sub-list
                if line.text[-1] in self.ordered_sign:
                    sign = '1.'
                else:
                    sign = line.text[-1]

                replace(self.view, [line.region.end() - 1, line.region.end()], '\n{}{} '.format('\t' * (line.indentation + 1), sign))

            else:
                # insert new element
                list_prefix = line.text.strip()[0]
                if not self.list_prefix.match(list_prefix):
                    return sublime.error_message('The sign {} is not valid.'.format(repr(list_prefix)))
                if list_prefix.isdigit():
                    list_prefix = '{}.'.format(int(list_prefix) + 1)

                insert(self.view, line.region.end(), '\n{}{} '.format('\t' * line.indentation, list_prefix))
        self.reorder_list()

    def get_sign_for(self, indentation, point) -> None:
        row, col = self.view.rowcol(point)
        while row >= 0:
            row -= 1
            line = StdClass()
            line.region = self.view.line(self.view.text_point(row, 0))
            line.text = self.convert_indentation(self.view.substr(line.region))
            line.indentation = self.get_indentation(line.text)
            if line.indentation < indentation:
                cont = False
                return line.text.lstrip()[0]


    def reorder_list(self) -> None:

        """
            Rename the prefixes.

            1. x1
            8. x2
            5. x3

            to

            1. x1
            2. x2
            3. x3

            works with nested list and unordered lists.

        """

        def reset_lower_indentation(indentations, indentation):
            new_indentations = {}
            for current_indentation in indentations.keys():
                if current_indentation < indentation:
                    new_indentations[current_indentation] = indentations[current_indentation]
            return new_indentations

        def replace_line(indentations, line):
            indentations[line.indentation] += 1
            print(indentations[line.indentation], line.text)
            line.text = '{}{}.{}'.format(
                '\t' * line.indentation,
                indentations[line.indentation],
                line.text.split('.', 1)[1]
            )
            replace(self.view, line.region, line.text)

        regions = self.view.sel()
        for region in regions:
            lines = self.view.extract_scope(region.begin())
            lines = self.view.split_by_newlines(lines)
            indentations = {}
            prev_indentation = 0
            for i, line_region in enumerate(lines):
                line = StdClass()
                line.region = self.view.line(line_region.begin())
                line.text = self.convert_indentation(self.view.substr(line.region))
                line.indentation = self.get_indentation(line.text)
                if line.region.empty():
                    continue
                if line.indentation > prev_indentation:
                    # print('reset', line.text)
                    indentations = reset_lower_indentation(indentations, line.indentation)
                    # return print(indentations)

                if indentations.get(line.indentation, None) is None:
                    indentations[line.indentation] = line.text.lstrip()[0]
                    if indentations[line.indentation].isdigit():
                        indentations[line.indentation] = 0
                        replace_line(indentations, line)
                else:
                    if isinstance(indentations[line.indentation], int):
                        replace_line(indentations, line)
                prev_indentation = line.indentation

    def convert_indentation(self, text: str=None) -> None:
        if text is None:
            text = self.view.substr(sublime.Region(0, self.view.size()))
        settings = self.view.settings()
        if settings.get('translate_tabs_to_spaces', False) is not True:
            return text
        text = text.replace(' ' * settings.get('tab_size'), '\t')
        return text

    def get_indentation(self, line):
        indentation = 0
        for char in line:
            if char == '\t':
                indentation += 1
            else:
                return indentation
        return indentation

    def run(self, edit, action:str=None):
        if action is None:
            return sublime.error_message('the action cannot be None')
        if not isinstance(action, str):
            return sublime.error_message('The action must be a string, not a {}'.format(action.__class__.__name__))

        try:
            action_to_run = getattr(self, action)
        except AttributeError:
            return sublime.error_message("The action '{}' is unknown.".format(action))

        action_to_run()
