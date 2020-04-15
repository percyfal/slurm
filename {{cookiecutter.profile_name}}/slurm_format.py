from snakemake.utils import SequenceFormatter, AlwaysQuotedFormatter, QuotedFormatter
from snakemake.exceptions import WorkflowError

def format(_pattern, _quote_all=False, **kwargs):
    """Format a pattern in Snakemake style.
    This means that keywords embedded in braces are replaced by any variable
    values that are available in the current namespace.
    """
    fmt = SequenceFormatter(separator=" ")
    if _quote_all:
        fmt.element_formatter = AlwaysQuotedFormatter()
    else:
        fmt.element_formatter = QuotedFormatter()
    try:
        return fmt.format(_pattern, **kwargs)
    except KeyError as ex:
        raise NameError(
            "The name {} is unknown in this context. Please "
            "make sure that you defined that variable. "
            "Also note that braces not used for variable access "
            "have to be escaped by repeating them, "
            "i.e. {{{{print $1}}}}".format(str(ex))
        )

def format_values(dictionary, job_properties):
    formatted = dictionary.copy()
    print(job_properties)
    for key, value in list(formatted.items()):
        if isinstance(value, str):
            try:
                formatted[key] = format_wildformat(value, **job_properties)
            except NameError as e:
                msg = (
                    "Failed to format cluster config "
                    "entry for job {}.".format(job_properties.rule)
                )
            raise WorkflowError(msg, e)
    return formatted