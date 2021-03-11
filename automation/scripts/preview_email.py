from datetime import datetime

import flask

from ..utils import templates
from .. import models

app = flask.Flask(__name__)


@app.route("/new_member_email.html")
def new_member_email():
    member = models.MemberModel(
        name="Grace Hopper",
        email="user@example.com",
        id=1,
        created_at=datetime.now(),
    )
    return templates.render("new_member_email.html.jinja", member=member)


@app.route("/<path:filename>.html")
def preview(filename):
    return templates.render("%s.html.jinja" % filename)


if __name__ == "__main__":
    app.run(debug=True)
