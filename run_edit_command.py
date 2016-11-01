import sublime
import sublime_plugin


class RunEditCommandCommand(sublime_plugin.TextCommand):
    def run(self, edit, command, arguments=[], **kwargs):
        """
            Allows you to run:
            replace()
            erase()
            insert()
            without worrying about the edit object.

            By math2001
        """
        # return getattr(self.view, command)(edit, *arguments, **kwargs)

class EditReplaceCommand(sublime_plugin.TextCommand):

    def run(self, edit, region, text):
        return self.view.replace(edit, sublime.Region(region[0], region[1]), text)

class EditEraseCommand(sublime_plugin.TextCommand):

    def run(self, edit, region):
        return self.view.erase(edit, sublime.Region(region[0], region[1]))

class EditInsertCommand(sublime_plugin.TextCommand):

    def run(self, edit, point, text):
        return self.view.insert(edit, point, text)


class MessageDialogCommand(sublime_plugin.WindowCommand):

    def run(self, text):
        return sublime.message_dialog(text)