# link-shelf

A small local command-line bookmark shelf. Add links, tag them, find them later, and remove them by ID. It never fetches URLs or contacts a service.

## Usage

```sh
python link_shelf.py add https://example.com/guide --title "A useful guide" --tag reading
python link_shelf.py list
python link_shelf.py list --tag reading
python link_shelf.py find useful
python link_shelf.py remove 1a2b3c4d
```

Removal asks for confirmation in an interactive shell. Pass `--yes` only when you intend to remove the matching bookmark, including in scripts. IDs are random and the first eight characters are shown in the list.

## Data and privacy

The JSON file stays on the local machine. Its path can be set with `LINK_SHELF_FILE`; otherwise it uses the platform's normal per-user data directory. Writes use a temporary file and atomic replacement, so an interrupted save does not leave a half-written bookmark file. If the file cannot be parsed, the program stops without replacing it. Stored links may contain private query parameters; back up the file accordingly. The tool rejects URL-embedded usernames and passwords.

## Linux builds

Prebuilt x86_64 Linux onefile and onedir archives are attached to the [v1.0.0 release](https://github.com/506058115-cmd/link-shelf/releases/tag/v1.0.0). The release includes build details and SHA-256 checksums.

## License

MIT. See [LICENSE](LICENSE).
