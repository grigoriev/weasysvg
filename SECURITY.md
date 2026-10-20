# Security policy

## Reporting a vulnerability

Report a vulnerability privately through GitHub:
https://github.com/grigoriev/weasysvg/security/advisories/new
(the **Security** tab, **Report a vulnerability**). Do not open a public issue for it.

We answer within a week. The fix goes into the next release, and its release notes name it.

## Supported versions

Only the latest release gets fixes.

## Scope

The package in `src/weasysvg/`, the test and bench tools, the Dockerfile, the scripts and the
workflows belong to this repository. weasysvg renders untrusted SVG inside WeasyPrint: a way to make it
read files, fetch URLs past the URL fetcher of the caller, or exhaust memory or time is in scope.

Vulnerabilities in upstream software (WeasyPrint, Pango, Python and the development tools) belong to
the upstream project. Tell us as well if this project is affected, so we can release a fix when the
upstream fix is out.
