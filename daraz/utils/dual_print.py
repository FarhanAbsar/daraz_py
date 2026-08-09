

# output = None
def _get_output(output=None):
    # global output
    if output is None:
        output = widgets.Output()
    # global _output_displayed
    # if not _output_displayed:
    #     try:
    #         display(output)
    #     except Exception:
    #         pass
        # _output_displayed = True
    # display(output)
    return output

_output_displayed = False
try:
    import ipywidgets as widgets
    from IPython.display import display, HTML
    IN_JUPYTER = True

    output = _get_output()
except ImportError:
    IN_JUPYTER = False

def dual_print(*args, output=None):
    # global output
    if IN_JUPYTER:
        if output is None:
            output = _get_output()
        with output:
            print(*args)
    else:
    # if True:
        print(*args)