# automation_prime

TODO

## Developers: Getting Started

### Devcontainers

The (hopefully) easiest way to get working is with VS Code and devcontainers.

To start, install:

* Docker ([for Mac or Windows](https://www.docker.com/products/docker-desktop)), or using your Linux distribution's package manager
* [VS Code](https://code.visualstudio.com/)
* The [VS Code Remote Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension

Next, in VS Code, open the Command Palette (`Ctrl+Shift+P`) and run `Remote-Containers: Clone Repository in Container Volume...`. Clone `https://github.com/bedstuystrong/automation_prime`, or fork that repo first and clone your fork.

Once it clones the repo, it will build your development environment in a container for you, and you'll be ready to go.

You can open a terminal and test that your environment is set up correctly:

```
$ python -m automation.scripts.local -h
```

### Other Systems

Without devcontainers, you will need a recent version of Python 3. Run `./create_venv.sh` to create a virtualenv and install `automation_prime`'s dependencies, then activate that environment (`source venv/bin/activate`) and run `pip install -e .`.
