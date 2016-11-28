# -*- encoding: utf-8 -*-
import sublime
from sublime_plugin import TextCommand

class Rowcol2region:
    """Helper for saving region after modification of the buffer.
    It is based on the row/col, not one the number of the char"""

    def __init__(self, view):
        self.view = view

    def save(self, sels=None):
        v = self.view
        self.sels = []
        for region in sels or self.view.sel():
            self.sels.append([v.rowcol(region.begin()), v.rowcol(region.end())])
        return self

    def get_valid_text_point(self, rowcol):
        row, col = rowcol
        v = self.view
        line_length = len(v.substr(v.line(v.text_point(row, 0))))
        if col > line_length:
            col = line_length
        return v.text_point(row, col)

    def restore(self):
        v = self.view
        v.sel().clear()
        for start, end in self.sels:
            v.sel().add(sublime.Region(self.get_valid_text_point(start),
                                 self.get_valid_text_point(end)))
        return self

class TestRowcol2region(TextCommand):

    def run(self, edit):
        if self.view.name() == 'Test rowcol2region':
            view = self.view
        else:
            view = self.view.window().new_file()
            view.set_name('Test rowcol2region')
            view.insert(edit, 0, 'hisdfsdfasdfasdf\nhello\nuio')
        saver = Rowcol2region(view).save()
        view.selection.clear()
        view.selection.add(sublime.Region(0, 15))
        view.replace(edit, sublime.Region(2, 16), 'hello')
        view.selection.clear()
        saver.restore()

    def is_enabled(self):
        return False
