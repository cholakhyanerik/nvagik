# Security policy

## Supported versions

Nvagik is in early development (before 1.0). Security fixes are released only as a new version on top of the latest one. Older versions do not get fixes, so please update to the newest one.

| Version | Supported |
| --- | --- |
| Latest version (the newest `vX.Y.Z` tag; later also the current Microsoft Store version) | Yes |
| Any older version | No |

This policy will be reviewed for the 1.0 release.

## Reporting a vulnerability

Please **do not** report security problems in public issues, discussions or pull requests.

Report them privately through GitHub instead:

1. Open [Report a vulnerability](https://github.com/cholakhyanerik/nvagik/security/advisories/new) (the repository's **Security** tab, then **Report a vulnerability**). You need a GitHub account.
2. Describe the problem: the affected version, the steps to reproduce it (attach a sample project, audio file, MIDI file or plugin name if one is involved) and what an attacker could do with it. If the form does not accept a file, say so in the report: the maintainer can invite you to the advisory's temporary private fork to share it.

Only you, the maintainer and people the maintainer invites to help with the fix can see the report.

## What happens next

- You get a first answer within 7 days.
- If the problem is confirmed, it is fixed in a new release, as fast as its severity requires and in any case within 90 days. You are kept up to date in the report.
- After the fix is released, a security advisory is published. You are credited in it and in the [CHANGELOG](CHANGELOG.md) unless you prefer to stay anonymous.

## Scope

In scope:

- The Nvagik application and its source code, especially reading untrusted files (projects, audio, MIDI), plugin scanning and hosting, and saving files outside the project folder.
- Release builds, including the Microsoft Store package.
- The development hooks, scripts and CI workflows in this repository (for example, a way to commit private data past the guard hook).

Out of scope:

- Bugs in third-party VST3 plugins themselves. Please report them to the plugin's vendor. A VST3 plugin is native code that runs with your user rights, and Nvagik does not sandbox it, so install only plugins you trust. Still in scope: a plugin that crashes Nvagik during scanning, or Nvagik loading a plugin or DLL from a place you did not choose (for example, a project folder or the current directory).
- Vulnerabilities in dependencies such as Qt, PySide6 or NumPy. Please report them upstream, and tell us if Nvagik is affected. A release that bundles a dependency version with a known vulnerability, or Nvagik using a dependency unsafely, is in scope.

At the moment Nvagik makes no network requests and collects no data, so it has no servers or accounts to test. The landing page will be in scope once it exists.
