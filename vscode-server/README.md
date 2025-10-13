# VSCode Server Directory

This directory is reserved for content from the Bashull/.openvscode-server repository.

## Purpose
This subdirectory was created to house files and content from the Bashull/.openvscode-server repository.

## Status
The source repository (Bashull/.openvscode-server) does not currently exist or is empty. When the repository is created and populated with content, it can be merged here while preserving commit history using:

```bash
git subtree add --prefix=vscode-server vscode-server-repo <branch> --squash
```

Or to preserve full history:

```bash
git subtree add --prefix=vscode-server vscode-server-repo <branch>
```

## Notes
- This directory structure follows the requirement to merge the Bashull/.openvscode-server repository into a `vscode-server` subdirectory
- Commit history preservation will be maintained when content is available in the source repository
- OpenVSCode Server is typically used for browser-based development environments
