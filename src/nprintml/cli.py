import argparse

# import argparse_formatter  # FIXME


def execute(argv=None, **parser_kwargs):
    parser = argparse.ArgumentParser(
        description='DESCRIPTION GOES HERE',

        # TODO: It's assumed that we'll want fancy formatting;
        # TODO: but, if that's not the case let's get rid of this:
        # formatter_class=argparse_formatter.ParagraphFormatter,

        **parser_kwargs,
    )
    args = parser.parse_args(argv)

    raise NotImplementedError(args)
