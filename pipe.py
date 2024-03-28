from typing import Optional


async def pipe(
    input_str: str, session_id: str = "", *args, **kwargs
) -> Optional[str]:
    """Pipe from the input of this block to the output.
    First argument: str
    Second argument: str the input string from the previous block
    Session_id: str The name of the current running isinstance
    Keyword/default arguments dependent on the caller
    A reminder on python arguments
    First arguments: These are positional without default must be included
    Next arguments: have defaults and can be keyword arguments as well
    Variable positional arguments in an array
    Variable keyword arguments in a dictionary
    https://stackoverflow.com/questions/39623889/is-there-any-way-to-print-kwargs-in-python
    https://builtin.com/software-engineering-perspectives/arguments-in-python
    https://stackoverflow.com/questions/15074821/python-passing-parameters-by-name-along-with-kwargs
    """
    output_str = (
        f"{__file__}: {input_str=} {session_id=} {args=} {kwargs=}"
        f"{locals()}"
    )
