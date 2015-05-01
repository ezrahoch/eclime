import sublime, sublime_plugin
import ntpath
import time

last_filename = ""
last_variaint = ""

class BuildLastCommand(sublime_plugin.TextCommand):
    def build_now(self):
        window = sublime.active_window()
        args = {"variant": last_variaint}
        window.run_command('build', args)

    def run(self, edit):
        print("file: " + last_filename)
        print("variant: " + last_variaint)
        window = sublime.active_window()
        new_view = window.open_file(last_filename)

        sublime.set_timeout(self.build_now, 100)

        # if (new_view != self.view):
        #     new_view.run_command("jump_back")


class BuildCurrentCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        global last_filename
        global last_variaint
        last_filename = self.view.file_name()
        print("file: " + last_filename)

        window = sublime.active_window()

        last_variaint = "build_me";
        print("variant: " + last_variaint)
        args = {"variant": last_variaint}
        window.run_command('build', args)

class BuildCurrentUtCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        global last_filename
        global last_variaint
        last_filename = self.view.file_name()
        print("file: " + last_filename)

        window = sublime.active_window()

        last_variaint = "build_me_ut";
        args = {"variant": last_variaint}
        print("variant: " + last_variaint)
        window.run_command('build', args)
