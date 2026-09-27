import pypandoc
import pydoc
import pick
import sys


def description(description):
    """Decorator to make it possible to quickly attach a description to a function or class."""
    def wrapper(action):
        action.description = description
        return action
    return wrapper


def launch_reader(story):
    chapters = story.contents
    chapter_index = -1

    @description('Next Chapter')
    def next_chapter_action():
        nonlocal chapter_index
        chapter_index += 1

    @description('Start from the Beginning')
    def start_from_beginning_action():
        nonlocal chapter_index
        chapter_index = 0

    @description('Select Chapter')
    def select_chapter_action():
        nonlocal chapter_index
        _, chapter_index = pick.pick(
            [chapter.title for chapter in chapters],
            "Which chapter?",
            default_index=max(0, chapter_index)
        )

    @description('Quit')
    def quit_action():
        sys.exit(0)

    actions = [next_chapter_action, start_from_beginning_action, select_chapter_action, quit_action]

    while True:
        _, action_index = pick.pick([action.description for action in actions], "What to do?")
        actions[action_index]()
        pydoc.pager(pypandoc.convert_text(chapters[chapter_index].contents, 'rst', format='html'))
