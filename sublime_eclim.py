# Ideas:
# - preprocess & compile & return errors on preprocessed file
# - auto insert include file
# - goto include file
# -

import sublime, sublime_plugin
import subprocess
import re
import json
import linecache
import os

eclim_executables = ["/local/local/.eclipse/org.eclipse.platform_4.4.1_1473617060_linux_gtk_x86_64/eclim",
                     "/Users/ezra/eclipse/eclim"]

def show_error_msg(msg):
    sublime.error_message(msg)

def run_eclim(args_list, ignore_errors=False):
    args_str = " ".join([str(s) for s in args_list])

    eclim_executable = ""
    for filename in eclim_executables:
        if (os.path.isfile(filename)):
            eclim_executable = filename

    if (eclim_executable == ""):
        show_error_msg("Failed to find eclim")
        return None

    cmd = "%s %s" % (eclim_executable, args_str)
    print ("Running: %s" % (cmd))

    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = p.communicate()
    out = out.decode('utf-8')
    err = err.decode('utf-8')

    if err or "Connection refused" in out:
        if not ignore_errors:
            show_error_msg(err)
        return None

    if (not out.startswith('{') and not out.startswith('[')):
        if not ignore_errors:
            show_error_msg(out)
        return None

    result = json.loads(out)
    print ("Result: %s" % (result))

    return result

def get_project_path():
    folders = sublime.active_window().folders()
    project_root = folders[0]
    if (not project_root.endswith('/')):
        project_root += '/'
    return project_root

def to_local_filename(filename):
    project_root = get_project_path()

    if (filename.startswith(project_root)):
        filename = filename[len(project_root):]

    return filename

def get_file_name(view):
    return to_local_filename(view.file_name())

class CompletionProposal(object):
    def __init__(self, name, insert=None, type="None"):
        split = name.replace(",", ", ").split()
        if len(split) < 2:
            self.name = name
        else:
            self.name = "%s\t%s" % (split[0], " ".join(split[1:]))
        self.display = self.name
        if insert:
            self.insert = insert
        else:
            self.insert = name
        self.type = "None"

    def __repr__(self):
        return "CompletionProposal: %s %s" % (self.name, self.insert)

class SublimeEclimFollowCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if not self.view.is_read_only() and self.view.is_dirty():
            self.view.run_command("save")

        filename = get_file_name(self.view)
        print (filename)

        pos = self.view.sel()[0]
        word = self.view.word(pos)
        offset = offset_of_location(self.view, word.a)

        location = run_eclim(['-command', 'c_search',
                              '-n', 'elfs',
                              '-f', '"' + filename + '"',
                              '-e', 'utf-8',
                              '-l', word.size(),
                              '-o', offset
                             ])

        if (len(location) == 0):
            return

        window = sublime.active_window()
        window.open_file("%s:%s:%s" % (location[0]['filename'], location[0]['line'], location[0]['column']), sublime.ENCODED_POSITION)

class SublimeEclimGoToLocationBase(sublime_plugin.TextCommand):
    def go_to_location(self, loc, transient):
        f, l, c = self.get_flc(loc)
        path = "%s:%s:%s" % (f, l, c)
        if (transient):
            sublime.active_window().open_file(path, sublime.ENCODED_POSITION | sublime.TRANSIENT)
        else:
            sublime.active_window().open_file(path, sublime.ENCODED_POSITION)

    def location_selected(self, selected_idx):
        if (selected_idx == -1):
            if (self.previous_file != get_file_name(sublime.active_window().active_view())):
                self.view.run_command("jump_back")
                # self.view.show_at_center(self.sel)
            return
        self.go_to_location(self.locations[selected_idx], False)

    def location_viewed(self, selected_idx):
        self.go_to_location(self.locations[selected_idx], True)

    def init_locations(self, locations):
        self.sel = self.view.rowcol(self.view.sel()[0].a)
        self.previous_file = get_file_name(self.view)
        self.locations = locations

    def try_save(self, view):
        if not view.is_read_only() and view.is_dirty():
            view.run_command("save")


class SublimeEclimTreeCommand(SublimeEclimGoToLocationBase):
    def get_flc(self, loc):
        return loc[1], loc[2], loc[3]

    def parse_tree(self, loc, depth):
        result = []
        if ('position' in loc):
            full_filename = loc['position']['filename']
            relative_filename = to_local_filename(full_filename)
            line_number = loc['position']['line']
            function_name = loc['name'].split('(')[0]
            # display = ("%s %s (%s:%s)" % (depth * " ", function_name, relative_filename, line_number))
            display = ("%s %s" % (depth * " ", function_name))
            display2 = ("%s %s:%s" % (depth * " ", relative_filename, line_number))
            result = [(display, full_filename, line_number, loc['position']['column'], display2)]

        if ('callers' in loc):
            for caller in loc["callers"]:
                result = result + self.parse_tree(caller, depth+1)

        return result

    def run(self, edit):
        self.try_save(self.view)

        filename = get_file_name(self.view)
        print (filename)

        pos = self.view.sel()[0]
        word = self.view.word(pos)
        offset = offset_of_location(self.view, word.a)

        locations = run_eclim(['-command', 'c_callhierarchy',
                               '-p', 'elfs',
                               '-f', filename,
                               '-e', 'utf-8',
                               '-l', word.size(),
                               '-o', offset
                              ])

        if (len(locations) == 0):
            return

        locations = self.parse_tree(locations, 0)
        print (str(locations))
        #  multiple usages -> show menu
        self.init_locations(locations)
        self.view.window().show_quick_panel(
            # [l[0] for l in self.locations],
            [[l[0], l[4]] for l in self.locations],
            self.location_selected, sublime.MONOSPACE_FONT, 0,
            self.location_viewed)

class SublimeEclimReferencesCommand(SublimeEclimGoToLocationBase):
    def get_flc(self, loc):
        return loc['filename'], loc['line'], loc['column']

    def run(self, edit):
        self.try_save(self.view)

        filename = get_file_name(self.view)
        print (filename)

        pos = self.view.sel()[0]
        word = self.view.word(pos)
        offset = offset_of_location(self.view, word.a)

        locations = run_eclim(['-command', 'c_search',
                               '-n', 'elfs',
                               '-f', '"' + filename + '"',
                               '-e', 'utf-8',
                               '-l', word.size(),
                               '-o', offset,
                               '-x', 'references'
                              ])

        if (len(locations) == 0):
            return

        linecache.checkcache()
        if len(locations) == 1:
            #  one definition was found and it is in a java file -> go there
            self.go_to_location(locations[0], False)
            return
        else:
            #  multiple usages -> show menu
            self.init_locations(locations)
            self.view.window().show_quick_panel(
                [["%s:%s" % (to_local_filename(l['filename']), l['line']), linecache.getline(l['filename'], l['line']).strip()] for l in self.locations],
                self.location_selected, sublime.MONOSPACE_FONT, 0,
                self.location_viewed)


def offset_of_location(view, location):
    '''we should get utf-8 size in bytes for eclim offset'''
    text = view.substr(sublime.Region(0, location))
    cr_size = 0
    if view.line_endings() == 'Windows':
        cr_size = text.count('\n')
    return len(text.encode('utf-8')) + cr_size

def to_proposals(completions, with_params):
#        proposals = [CompletionProposal(p['menu'], p['completion']) for p in completions]
        proposals = []

        # newer versions of Eclim package the list of completions in a dict
        if isinstance(completions, dict):
            completions = completions['completions']
        for c in completions:
            if not "<br/>" in c['info']:  # no overloads
                if len(c['info']) < len(c['completion']):
                    proposals.append(CompletionProposal(c['completion'], c['completion']))
                else:
                    proposals.append(CompletionProposal(c['info'], c['completion']))
            else:
                variants = c['info'].split("<br/>")
                param_lists = [re.search(r'\((.*)\)', v) for v in variants]
                param_lists = [x.group(1) for x in param_lists if x]
                props = []
                for idx, pl in enumerate(param_lists):
                    if pl:
                        params = [par for par in pl.split(", ")] # par..split(" ")[-1]
                        insert = ", ".join(["${%i:%s}" % (i, s)
                                            for i, s in
                                            zip(range(1, len(params) + 1), params)
                                            ])
                        if with_params:
                            insert = c['completion'] + insert + ")"
                        else:
                            insert = c['completion']
                        props.append(CompletionProposal(variants[idx], insert))
                    else:
                        props.append(CompletionProposal(variants[idx], c['completion']))
                proposals.extend(props)
        return proposals

class LinterRegion(object):
    def __init__(self, line, column, message):
        self.line = int(line)-1
        self.column = int(column)
        self.message = message

    def region(self, view):
        return view.word(view.text_point(self.line, self.column))

    def __repr__(self):
        return "LinterRegion: %s %s %s" % (self.line, self.column, self.message)

linting = {}
# last_proposals = []
# in_background = False
class SublimeEclimAutoComplete(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        # Avoid code completion on short lines
        line_text = view.substr(view.line(locations[0])).strip()
        if (len(line_text) < 3):
            return

        # Avoid code completion after ';' or after '{' (such code completions will take a long time)
        prev_char = view.substr(locations[0]-1)
        if (prev_char == ";" or prev_char == "{"):
            return

        filename = get_file_name(view)
        print (filename)

        if (not filename.endswith('.c') and not filename.endswith('.h')):
            return

        if ('comment' in view.scope_name(locations[0])):
            return

        view.run_command("save")

        offset = offset_of_location(view, locations[0])


        cmd_output = run_eclim(['-command', 'c_complete',
                                '-p', 'elfs',
                                '-f', '"' + filename + '"',
                                '-e', 'utf-8',
                                '-l', 'compact',
                                '-o', offset
                               ])

        if view.word(locations[0]).size() == len(prefix):
            proposals = to_proposals(cmd_output, True)
        else:
            proposals = to_proposals(cmd_output, False)
        print(proposals)

        # Make Unique
        seen = set()
        seen_add = seen.add
        return [ (p.display, p.insert) for p in proposals if not (p.display in seen or seen_add(p.display))]
        # return [(p.display, p.insert) for p in last_proposals]

    # def on_modified_async(self, view):
    #     global in_background
    #     global last_proposals
    #     if (in_background):
    #         return

    #     filename = get_file_name(view)
    #     print (filename)

    #     if (not filename.endswith('.c') and not filename.endswith('.h')):
    #         return

    #     pt = view.sel()[0].begin()
    #     print (pt)
    #     if ('comment' in view.scope_name(pt)):
    #         return

    #     in_background = True

    #     view.run_command("save")

    #     offset = offset_of_location(view, pt)

    #     cmd_output = run_eclim(['-command', 'c_complete',
    #                             '-p', 'elfs',
    #                             '-f', filename,
    #                             '-e', 'utf-8',
    #                             '-l', 'compact',
    #                             '-o', offset
    #                            ])

    #     proposals = to_proposals(cmd_output)
    #     print(proposals)

    #     last_proposals = proposals

    #     in_background = False
    #     view.run_command("auto_complete")


    def on_post_save_async(self, view):
        if self.is_scratch(view):
            return

        view = self.get_focused_view_id(view)

        if view is None:
            return

        filename = get_file_name(view)
        print (filename)

        if (not filename.endswith('.c') and not filename.endswith('.h')):
            return

        issues = run_eclim(['-command', 'c_src_update',
                               '-p', 'elfs',
                               '-f', '"' + filename + '"',
                               '-v'
                            ], True)

        linter_regions = [LinterRegion(issue['line'], issue['column'], issue['message']) for issue in issues];

        regions = [lr.region(view) for lr in linter_regions]
        view.add_regions('issues', regions, 'keyword', flags=sublime.DRAW_NO_FILL)

        linting[view.id()] = {}
        for lr in linter_regions:
            linting[view.id()][lr.line] = lr

        self.on_selection_modified_async(view)

    def get_focused_view_id(self, view):
        """
        Return the focused view which shares view's buffer.
        When updating the status, we want to make sure we get
        the selection of the focused view, since multiple views
        into the same buffer may be open.
        """
        active_view = view.window().active_view()

        for view in view.window().views():
            if view == active_view:
                return view

    def is_scratch(self, view):
        """
        Return whether a view is effectively scratch.
        There is a bug (or feature) in the current ST3 where the Find panel
        is not marked scratch but has no window.
        There is also a bug where settings files opened from within .sublime-package
        files are not marked scratch during the initial on_modified event, so we have
        to check that a view with a filename actually exists on disk if the file
        being opened is in the Sublime Text packages directory.
        """

        if view.is_scratch() or view.is_read_only() or view.window() is None or view.settings().get("repl") is not None:
            return True
        elif (
            view.file_name() and
            view.file_name().startswith(sublime.packages_path() + os.path.sep) and
            not os.path.exists(view.file_name())
        ):
            return True
        else:
            return False

    def on_close(self, view):
        """Called after view is closed."""

        if self.is_scratch(view):
            return

        vid = view.id()

        if vid in linting:
            del linting[vid];

    def on_selection_modified_async(self, view):
        if self.is_scratch(view):
            return

        view = self.get_focused_view_id(view)

        if view is None:
            return

        vid = view.id()

        # Get the line number of the first line of the first selection.
        try:
            lineno = view.rowcol(view.sel()[0].begin())[0]
        except IndexError:
            lineno = -1

        # print (lineno)

        if vid in linting:
            # print(linting)
            errors = linting[vid]

            if errors:
                if lineno in errors:
                    view.set_status('subclimelinter', '[[[%s]]]' % (errors[lineno].message))
                    return
        view.erase_status('subclimelinter')
