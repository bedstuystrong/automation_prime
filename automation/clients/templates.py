"""Utilities for rendering jinja HTML templates

Example:

    from automation.utils import templates

    member = <get member from airtable>
    email_content = templates.render(
        "new_member_email.html.jinja",
        member=member,
    )

NOTE when writing jinja templates try and make your variables correspond to
existing models. For example, if you want to access a member's name in a
template use `{{ member.name }}` instead of `{{ name }}`.
"""

import functools
from pathlib import Path

import jinja2
from jinja2.utils import select_autoescape

STATIC_PATH = Path(__file__).parent.parent / "static"


@functools.cache
def get_environment():
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(STATIC_PATH)),
        autoescape=select_autoescape(["HTML"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render(template_name, **kwargs):
    return get_environment().get_template(template_name).render(**kwargs)
