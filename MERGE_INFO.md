# Repository Merge Documentation

This document describes the repository merge structure for the Kai project.

## Merged Repositories

This repository now contains subdirectories for the following merged repositories:

### 1. bashull/
- **Source**: [Bashull/Bashull](https://github.com/Bashull/Bashull)
- **Purpose**: Config files and profile information
- **Status**: Directory structure created; source repository is currently empty

### 2. vscode-server/
- **Source**: Bashull/.openvscode-server (repository not currently available)
- **Purpose**: OpenVSCode Server configuration and files
- **Status**: Directory structure created; awaiting source content

## Merge Strategy

The merge was designed to preserve commit history using Git subtree merge strategy. Once content is available in the source repositories, full history can be preserved using:

```bash
# For bashull repository
git subtree add --prefix=bashull bashull-repo <branch>

# For vscode-server repository
git subtree add --prefix=vscode-server vscode-server-repo <branch>
```

## Directory Structure

```
Kai/
├── bashull/           # Bashull profile and config files
├── vscode-server/     # OpenVSCode Server files
├── src/               # Main application source
├── components/        # React components
└── ...                # Other project files
```

## Future Updates

To update merged subdirectories with changes from their source repositories:

```bash
# Update bashull
git subtree pull --prefix=bashull bashull-repo <branch>

# Update vscode-server
git subtree pull --prefix=vscode-server vscode-server-repo <branch>
```

## Notes

- The merge structure maintains separation of concerns while keeping all related code in one repository
- Each subdirectory maintains its own README.md with specific information
- Git remotes for source repositories are preserved for future updates
