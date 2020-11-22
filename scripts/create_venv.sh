DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
DIR="$(dirname "$DIR")"
VENV="$DIR/venv"

if [ -f $(realpath "$VENV") ]; then
    echo "Removing old venv..."
	rm -r "$VENV"
fi

echo "Making new venv..."
python3 -m venv "$VENV"

echo "Installing requirements..."
"$VENV"/bin/pip install -r requirements.txt

echo "Done!"
