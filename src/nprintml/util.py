import argparse


class HelpAction(argparse.Action):
    """Pluggable "help" action.

    Based on the built-in "help" action, enabling the definition of
    additional "--help-*" flags.

    Help output must be printed by the given callable `help_action`.

    When the flag is set, `help_action` is invoked and then the process
    is exited.

    """
    def __init__(self,
                 option_strings,
                 *,
                 help_action,
                 dest=argparse.SUPPRESS,
                 default=argparse.SUPPRESS,
                 help=None):
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help)

        self.help_action = help_action

    def __call__(self, parser, namespace, values, option_string=None):
        self.help_action(parser, namespace, values, option_string)
        parser.exit()
