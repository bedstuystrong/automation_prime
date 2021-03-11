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
import re

import jinja2
from jinja2.utils import select_autoescape
from premailer import transform


STATIC_PATH = Path(__file__).parent.parent / "static"


def digits_only(value):
    return re.sub(r"[^0-9]", "", value, count=0)


@functools.cache
def get_environment():
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(STATIC_PATH)),
        autoescape=select_autoescape(["HTML"]),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=jinja2.ChainableUndefined,
    )
    env.filters["digits_only"] = digits_only
    return env


def render(template_name, inline_css=True, **kwargs):
    rendered = get_environment().get_template(template_name).render(**kwargs)
    if inline_css:
        return transform(rendered, keep_style_tags=True)
    else:
        return rendered
