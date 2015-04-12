import sublime, sublime_plugin
import ntpath

last_filename = ""

class BuildLastCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        print(last_filename)
        window = sublime.active_window()
        window.open_file(last_filename)

        print(last_filename)
        args = {"variant": "build_me"}
        window.run_command('build', args)

class BuildCurrentCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        global last_filename
        last_filename = self.view.file_name()
        print(last_filename)

        window = sublime.active_window()

        args = {"variant": "build_me"}
        window.run_command('build', args)
