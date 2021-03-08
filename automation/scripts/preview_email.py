import flask

from ..utils import templates

app = flask.Flask(__name__)


@app.route("/<path:filename>.html")
def preview(filename):
    return templates.render("%s.html.jinja" % filename)


if __name__ == "__main__":
    app.run(debug=True)
