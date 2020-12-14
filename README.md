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

## Environment

This section covers steps required for setting up the environment for the automation.

### Staging Airtable

1. Duplicate production base, including records
2. Rename base to "STAGING"
3. Add automation bot user to staging base (with editor permissions)
4. Get base ID: go to airtable.com/api, select the staging base, and copy the base ID into your `config.json`

## Migration Notes

- All tables must have a new field `_meta_last_seen_status` (single line text type)
- NOTE that as opposed to the vintage automation, all records with `{Status} = BLANK()` are ignored
- Volunteers table:
    - Add a new status choice: `New`
    - Update form to include status field with `New` as the only option
