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

## Developers: Contributing
- To run tests: `pytest automation/` from the root of your checkout

## Developers: Environment and Settings Management

Settings are defined in `.env` files in the `environments/` directory: most of the time, you'll deal with `dev.env` locally, then deploy with `staging.env` to test out a change, and finally deploy with `prod.env` to make your change go live.

Secrets, like API keys, are managed for you: they're stored in Google Secret Manager and fetched as needed. If you need access to these, ask an admin to be added.

Setting schemas are managed near the code that uses them. For example, each client (in `automation.clients`) has some related settings defined with a schema, which you can access by instantiating that settings object and accessing its fields.

You can select a different environment (the default is `dev`) by setting the environment variable `AUTOMATION_ENV`, for example, `AUTOMATION_ENV=staging python -m automation....`. You can override individual variables by adding those values to your environment before running something, typically a local development script. Check out the `.env` files for valid variables you can override.

When deploying, you'll need to set `AUTOMATION_ENV` to either `prod` or `staging` when running `automation.scripts.setup_gcloud`: this selects which environment you deploy to.

## Environment

This section covers steps required for setting up the environment for the automation.

### Staging Airtable

1. Duplicate production base, including records and excluding comments
2. Rename base to "STAGING"
3. Add automation bot user to staging base (with editor permissions)
4. Get base ID: go to airtable.com/api, select the staging base, and copy the base ID into your `config.json`

## Migration Notes

- All tables must have a new field `_meta_last_seen_status` (single line text type)
- NOTE that as opposed to the vintage automation, all records with `{Status} = BLANK()` are ignored
- Members table:
    - Add a new status choice: `New`
    - Update form to include status field with `New` as the only option
