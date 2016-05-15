import sublime, sublime_plugin
import ntpath

class SublimeImprovedTabListCommand(sublime_plugin.TextCommand):
    def open_tab(self, view, transparent):
        self.last_view = view
        if transparent:
            sublime.active_window().open_file(view.file_name(), sublime.TRANSIENT)
        else:
            sublime.active_window().open_file(view.file_name())

    def tab_viewed(self, selected_idx):
        self.open_tab(self.names[selected_idx][1], True)
        return

    def tab_selected(self, selected_idx):
        if selected_idx == -1:
            self.open_tab(self.names[self.index][1], False)
            return
        self.open_tab(self.names[selected_idx][1], False)

    def run(self, edit):
        window = sublime.active_window()
        views = filter(lambda x: not x.is_scratch(), window.views())
        self.names = [(ntpath.basename(view.file_name()), view) for view in views if view.file_name()]
        self.names = sorted(self.names, key=lambda x: x[0])

        index = [i for i, j in enumerate(self.names) if j[1] == window.active_view()]
        if (len(index) == 0):
            self.index = 0
        else:
            self.index = index[0]

        window.show_quick_panel([x[0] for x in self.names],
            self.tab_selected, sublime.MONOSPACE_FONT, self.index,
            self.tab_viewed)
