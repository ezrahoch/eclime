import sublime, sublime_plugin
import ntpath
import time

last_filename = ""

class BuildLastCommand(sublime_plugin.TextCommand):
    def build_now(self):
        window = sublime.active_window()
        args = {"variant": "build_me"}
        window.run_command('build', args)

    def run(self, edit):
        print(last_filename)
        window = sublime.active_window()
        new_view = window.open_file(last_filename)

        sublime.set_timeout(self.build_now, 100)

        # if (new_view != self.view):
        #     new_view.run_command("jump_back")


class BuildCurrentCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        global last_filename
        last_filename = self.view.file_name()
        print(last_filename)

        window = sublime.active_window()

        args = {"variant": "build_me"}
        window.run_command('build', args)
