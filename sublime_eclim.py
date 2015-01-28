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

eclim_executable = "~/eclipse/eclim"

def show_error_msg(msg):
    sublime.error_message(msg)

def run_eclim(args_list):
    args_str = " ".join([str(s) for s in args_list])
    cmd = "%s %s" % (eclim_executable, args_str)
    print ("Running: %s" % (cmd))

    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = p.communicate()
    out = out.decode('utf-8')
    err = err.decode('utf-8')

    if err or "Connection refused" in out:
        show_error_msg(err)
        return None

    if (not out.startswith('{') and not out.startswith('[')):
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
        split = name.split(" ")
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
        self.view.run_command("save")

        filename = get_file_name(self.view)
        print (filename)

        pos = self.view.sel()[0]
        word = self.view.word(pos)
        offset = offset_of_location(self.view, word.a)

        location = run_eclim(['-command', 'c_search',
                              '-n', 'elfs',
                              '-f', filename,
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
        self.view.run_command("save")

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
        self.view.run_command("save")

        filename = get_file_name(self.view)
        print (filename)

        pos = self.view.sel()[0]
        word = self.view.word(pos)
        offset = offset_of_location(self.view, word.a)

        locations = run_eclim(['-command', 'c_search',
                               '-n', 'elfs',
                               '-f', filename,
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

def to_proposals(completions):
        proposals = [CompletionProposal(p['menu'], p['completion']) for p in completions]

        # newer versions of Eclim package the list of completions in a dict
        if isinstance(completions, dict):
            completions = completions['completions']
        for c in completions:
            if not "<br/>" in c['info']:  # no overloads
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
                        insert = c['completion'] + insert + ")"
                        props.append(CompletionProposal(variants[idx], insert))
                    else:
                        props.append(CompletionProposal(variants[idx], c['completion']))
                proposals.extend(props)
        return proposals

class SublimeEclimAutoComplete(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        # if (len(prefix) <= 2):
        #     return []

        view.run_command("save")

        filename = get_file_name(view)
        print (filename)

        if (not filename.endswith('.c') and not filename.endswith('.h')):
            return

        offset = offset_of_location(view, locations[0])


        cmd_output = run_eclim(['-command', 'c_complete',
                                '-p', 'elfs',
                                '-f', filename,
                                '-e', 'utf-8',
                                '-l', 'compact',
                                '-o', offset
                               ])

        proposals = to_proposals(cmd_output)
        print(proposals)

        # Make Unique
        seen = set()
        seen_add = seen.add
        return [ (p.display, p.insert) for p in proposals if not (p.insert in seen or seen_add(p.insert))]
        # return [(p.display, p.insert) for p in proposals]

    def on_post_save_async(self, view):
        filename = get_file_name(view)
        print (filename)

        if (not filename.endswith('.c') and not filename.endswith('.h')):
            return

        issues = run_eclim(['-command', 'c_src_update',
                               '-p', 'elfs',
                               '-f', filename,
                               '-v'
                            ])

        regions = [view.word(view.text_point(int(issue['line'])-1, int(issue['column']))) for issue in issues]
        print (regions)
        view.add_regions('issues', regions, 'keyword',
            flags=sublime.DRAW_NO_FILL)

