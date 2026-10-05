"""MathMate package.

`root_agent` is imported lazily (via __getattr__) so that submodules like
`mathmate.tools` and `mathmate.state_schema` — which contain the actual
testable logic — can be imported and unit-tested without requiring
google-adk (and its network-dependent extras) to be installed.
"""

__all__ = ["root_agent"]


def __getattr__(name):
    if name == "root_agent":
        from .agent import root_agent

        return root_agent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
