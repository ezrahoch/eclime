import sublime, sublime_plugin
import ntpath

last_filename = ""

class BuildLastCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if (not self.view.file_name().endswith('.t.c')):
            if (self.view.file_name().endswith('.c')):
                global last_filename
                last_filename = self.view.file_name()

        window = sublime.active_window()
        window.open_file(last_filename)

        print(last_filename)
        args = {"variant": "build_me"}
        window.run_command('build', args)
