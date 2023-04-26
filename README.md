# Welcome to the WikiPathways Database SANDBOX
This repository is a sandbox version of the wikipathways database to develop new actions and procedures for pathway curation.

## General Usage
Users should never have to see this repo. If you think you're here by accident, maybe you are looking for the [WikiPathways Database](https://github.com/wikipathways/wikipathways-database).

## Development
Please use caution when commit directly to this repository. Various GitHub Action are triggered by new commits. Please review the workflows in the `.github/workflows` directory and ask other developers on Slack if uncertain before making changes.

### Update Protocol
The GitHub actions specifiy versions for various tools and resources. Developers are responsible for keeping these up-to-date. GitHub Actions will report pending deprecations on each run. Please take note of these and update the version numbers accordingly. These might include:
 * Node.js
 * Ubuntu _(consider using ubuntu-latest)_
 * Syntax for things like environment variables and secrets

 Marketplace actions also need to be updated. These might include:
 * actions/checkout
 * actions/setup-java
 * actions/setup-node
 * actions/setup-python
 * actions/cache
 * r-lib/actions/setup-r

 Finally, our own tools and resources will require updates. These might include:
 * meta-data-action jar
 * SyncAction jar
 * Caches of bridgedb files
