#!/usr/bin/env python3
"""Keep a small, private, local shelf of web links."""

import argparse
import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


def store_path() -> Path:
    override = os.environ.get("LINK_SHELF_FILE")
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library/Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    return base / "link-shelf" / "bookmarks.json"


def terminal_safe(value: str) -> str:
    return "".join(
        char if char.isprintable() else char.encode("unicode_escape").decode("ascii")
        for char in value
    )


def load_items(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc
    if (
        not isinstance(data, dict)
        or type(data.get("version")) is not int
        or data["version"] != 1
        or not isinstance(data.get("bookmarks"), list)
    ):
        raise ValueError(f"unsupported or invalid bookmark file: {path}")
    required = ("id", "url", "title", "added", "tags")
    for item in data["bookmarks"]:
        if (
            not isinstance(item, dict)
            or any(not isinstance(item.get(key), str) for key in required[:4])
            or len(item.get("id", "")) != 32
            or any(char not in "0123456789abcdef" for char in item.get("id", ""))
            or not isinstance(item.get("tags"), list)
            or any(not isinstance(tag, str) for tag in item["tags"])
        ):
            raise ValueError(f"invalid bookmark record in {path}; file left untouched")
    return data["bookmarks"]


def save_items(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as stream:
            temp_path = Path(stream.name)
            json.dump({"version": 1, "bookmarks": items}, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def add_bookmark(args: argparse.Namespace, path: Path) -> int:
    parsed = urlsplit(args.url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("URL must be an absolute http:// or https:// address")
    parsed.port  # Validate the port syntax and range without making a network request.
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URLs containing embedded credentials are not stored")
    items = load_items(path)
    title = args.title or parsed.hostname + (parsed.path.rstrip("/") or "")
    items.append({
        "id": uuid.uuid4().hex,
        "url": args.url,
        "title": title,
        "added": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tags": sorted({tag.strip() for tag in args.tag if tag.strip()}),
    })
    save_items(path, items)
    print(f"Saved {terminal_safe(title)} ({items[-1]['id'][:8]}) to {terminal_safe(str(path))}")
    return 0


def print_matches(items: list[dict]) -> int:
    for item in items:
        tags = f" [{', '.join(terminal_safe(tag) for tag in item['tags'])}]" if item["tags"] else ""
        print(f"{item['id'][:8]}  {terminal_safe(item['added'][:10])}  {terminal_safe(item['title'])}{tags}")
        print(f"  {terminal_safe(item['url'])}")
    return 0


def list_bookmarks(args: argparse.Namespace, path: Path) -> int:
    items = load_items(path)
    if args.tag:
        wanted = args.tag.casefold()
        items = [item for item in items if wanted in {tag.casefold() for tag in item["tags"]}]
    if not items:
        print("No bookmarks found.")
        return 0
    return print_matches(items)


def find_bookmarks(args: argparse.Namespace, path: Path) -> int:
    query = args.query.casefold()
    items = load_items(path)
    matches = [
        item for item in items
        if query in " ".join((item["title"], item["url"], *item["tags"])).casefold()
    ]
    if not matches:
        print("No matches.")
        return 0
    return print_matches(matches)


def remove_bookmark(args: argparse.Namespace, path: Path) -> int:
    items = load_items(path)
    matches = [item for item in items if item["id"].startswith(args.id)]
    if len(matches) != 1:
        print("No matching bookmark." if not matches else "ID prefix is ambiguous.", file=sys.stderr)
        return 1
    item = matches[0]
    if not args.yes:
        if not sys.stdin.isatty():
            print("Use --yes to confirm removal in a non-interactive shell.", file=sys.stderr)
            return 2
        try:
            answer = input(f"Remove {terminal_safe(item['title'])} ({item['id'][:8]})? [y/N] ")
        except EOFError:
            answer = ""
        if answer.casefold() not in ("y", "yes"):
            print("Cancelled.")
            return 0
    items.remove(item)
    save_items(path, items)
    print(f"Removed {item['id'][:8]}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="A private, local shelf for web links.")
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add", help="save a link")
    add.add_argument("url")
    add.add_argument("--title")
    add.add_argument("--tag", action="append", default=[])
    show = commands.add_parser("list", help="show saved links")
    show.add_argument("--tag")
    find = commands.add_parser("find", help="search titles, URLs, and tags")
    find.add_argument("query")
    remove = commands.add_parser("remove", help="remove one link by its ID or unique prefix")
    remove.add_argument("id")
    remove.add_argument("--yes", action="store_true", help="confirm removal without prompting")
    args = parser.parse_args()

    path = store_path()
    try:
        if args.command == "add":
            return add_bookmark(args, path)
        if args.command == "list":
            return list_bookmarks(args, path)
        if args.command == "find":
            return find_bookmarks(args, path)
        return remove_bookmark(args, path)
    except (OSError, ValueError) as exc:
        print(f"link-shelf: {terminal_safe(str(exc))}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
