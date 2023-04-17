INITIAL_STATE = "INITIAL_STATE"
TERMINAL_STATE = "TERMINAL_STATE"
DEFAULT = "DEFAULT"


from typing import Dict, Tuple, Callable, Any, Optional


JsonParams = Dict[str, Any]

TransitionActionResult = Tuple[bool, Optional[str], JsonParams]

TransitionAction = Callable[[JsonParams], TransitionActionResult]

StateDefinition = Dict[str, Tuple[Optional[TransitionAction], str, str, bool]]

