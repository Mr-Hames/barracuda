# Security policy

Barracuda opens files that other people made: PDFs, Office documents and ZIP archives. That makes careful handling of hostile files part of the job, and reports are welcome.

## What it does to stay safe

- Files are only read on your computer. Nothing is uploaded or sent anywhere, and the scripts make no network calls.
- ZIP archives are unpacked into a temporary folder that is deleted afterwards. Paths that try to escape that folder (`../`) are skipped.
- Unpacking stops at 1 GB in total and 2,000 files per archive, so a "zip bomb" can't fill your disk. Archives inside archives count toward the same limit and are opened two levels deep at most.
- Password-protected or damaged files are reported as unreadable instead of crashing the check.
- Excel files are parsed with `defusedxml` installed, which protects against XML entity attacks.

## Supported versions

Only the latest release gets fixes.

## Reporting a vulnerability

Please don't open a public issue for a security problem. Use GitHub's private reporting instead: open the **Security** tab of this repository and click **Report a vulnerability**. You'll get an answer within a week. If the report is confirmed, the fix goes out in a new release and you're credited unless you'd rather not be.
