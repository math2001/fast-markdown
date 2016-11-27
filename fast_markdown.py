import sublime
import sublime_plugin
import re
import sys

def StdClass(name='Unknown'):
    return type(name.title(), (), {})


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

def convert_indentation(settings, text):
    if settings.get('translate_tabs_to_spaces', False) is not True:
        return text
    return text.replace(' ' * settings.get('tab_size'), '\t')

def get_indentation(text):
    indentation = 0
    for char in text:
        if char == '\t':
            indentation += 1
        else:
            return indentation
    return indentation

def fix(text):
    text = text.strip()
    if text[0] in ['-', '*', '+']:
        return text[0], text[1:]
    elif text.split('.', 1)[0].isdigit():
        return 1, text.split('.', 1)[1]
    else:
        raise ValueError('No suffix for the line {0!r}'.format(text))

class FastMarkdownShitCommand(sublime_plugin.TextCommand):


    list_prefix = re.compile(r'[0-9\-\*\+]\.?$')
    numbered_list_prefix = re.compile(r'[0-9]+\. .*')

    unordered_sign = ['*', '+', '-']
    ordered_sign = ['#']

    def list(self):

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

    def reorder_list(self):

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
                    indentations = reset_lower_indentation(indentations, line.indentation)

                if indentations.get(line.indentation, None) is None:
                    indentations[line.indentation] = line.text.lstrip()[0]
                    print(indentations[line.indentation])
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

class FastMarkdownCommand(sublime_plugin.TextCommand):

    def reorder_list(self, regions):
        """regions is a list of region of line for ONE list"""
        lines = {}
        v = self.view
        entire_text = ''
        prev_line = None
        for region in regions:
            line = StdClass('line')
            line.region = region
            line.text = convert_indentation(self.settings, v.substr(line.region))
            if line.text == '':
                break
            line.indentation = get_indentation(line.text)
            line.prefix, line.suffix = fix(line.text)
            if prev_line and line.indentation > prev_line.indentation:
                lines[line.indentation] = None
            if lines.get(line.indentation, None) is None:
                lines[line.indentation] = line.prefix
            if isinstance(lines[line.indentation], int):
                entire_text += '{0}{1}.{2}\n'.format(line.indentation * '\t', lines[line.indentation], line.suffix)
                lines[line.indentation] += 1
            else:
                entire_text += '{0}{1}{2}\n'.format(line.indentation * '\t', lines[line.indentation], line.suffix)

            prev_line = line

        replace(v, sublime.Region(regions[0].begin(), regions[-1].end()), entire_text)

    def reorder_lists(self):
        v = self.view
        for region in v.sel():
            scope = v.extract_scope(region.begin())
            self.reorder_list(v.lines(scope))

    # def insert_new_list_item(self):
    #     v = self.view
    #     for region in v.sel():



    def run(self, edit, action=None):
        self.settings = self.view.settings()
        if action is None:
            return sublime.error_message('the action cannot be None')
        if not isinstance(action, str):
            return sublime.error_message('The action must be a string, not a {}'.format(action.__class__.__name__))
        try:
            action_to_run = getattr(self, action)
        except AttributeError:
            return sublime.error_message("The action '{}' is unknown.".format(action))

        action_to_run()
