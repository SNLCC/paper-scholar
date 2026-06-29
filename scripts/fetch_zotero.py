#!/usr/bin/env python3
"""fetch_zotero.py — ..."""

# Handle terminal encoding gracefully: if stdout is not UTF-8,
# use the terminal's native encoding with 'replace' to avoid crashes.
# This ensures Chinese text displays correctly on Windows terminals (GBK).
import sys
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(errors='replace')
    except (AttributeError, ValueError):
        pass

"""
fetch_zotero.py — Retrieve papers, annotations, and PDFs from Zotero.

Three access modes:

  local  (default)   Zotero local API (http://localhost:23119/api/)
                     Requires Zotero desktop app running. No API key needed.

  web                Zotero Web API (https://api.zotero.org)
                     Requires an API key from https://www.zotero.org/settings/keys
                     Works without Zotero running.

  webdav             Nutstore/WebDAV storage (e.g. https://dav.jianguoyun.com/dav/)
                     Fetches PDF files directly from cloud storage.
                     Requires WebDAV credentials.

Usage:
    # Local API (Zotero must be running)
    python fetch_zotero.py local collections
    python fetch_zotero.py local items [--collection <key>]
    python fetch_zotero.py local item <key> [--annotations] [--pdf-path]

    # Web API
    python fetch_zotero.py web --api-key <key> [--user-id <id>] collections
    python fetch_zotero.py web --api-key <key> [--user-id <id>] items
    python fetch_zotero.py web --api-key <key> [--user-id <id>] item <key> [--annotations]

    # WebDAV (Nutstore)
    python fetch_zotero.py webdav --user <email> --password <app-pwd> ls [<remote-path>]
    python fetch_zotero.py webdav --user <email> --password <app-pwd> get <remote-path> <local-file>
"""

import argparse
import base64
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urljoin

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ZOTERO_LOCAL_API = "http://localhost:23119/api/"
ZOTERO_WEB_API = "https://api.zotero.org/"
NUTSTORE_WEBDAV = "https://dav.jianguoyun.com/dav/"


# ===================================================================
#  Shared helpers
# ===================================================================

def _fmt_item(data: dict) -> dict:
    """Return a human-readable summary from an item's data dict."""
    creators = data.get("creators", [])
    author_str = "; ".join(
        f"{c.get('firstName', '')} {c.get('lastName', '')}".strip()
        for c in creators if c.get("creatorType") == "author"
    )
    return {
        "key": data.get("key"),
        "title": data.get("title", "(no title)"),
        "authors": author_str or "(unknown)",
        "date": data.get("date", ""),
        "itemType": data.get("itemType", ""),
        "doi": data.get("DOI", ""),
    }


def _fmt_annotations(children: list[dict]) -> list[dict]:
    """Extract meaningful annotation fields from children."""
    result = []
    for c in children:
        d = c.get("data", {})
        if d.get("itemType") != "annotation":
            continue
        entry = {
            "page": d.get("annotationPageLabel"),
            "color": d.get("annotationColor"),
            "text": d.get("annotationText", ""),
            "comment": d.get("annotationComment", ""),
        }
        if entry["text"] or entry["comment"]:
            result.append(entry)
    return result


def _print_items(items: list[dict]):
    for item in items:
        d = item if "data" in item else {"data": item}
        s = _fmt_item(d.get("data", d))
        print(f"[{s['key']}] {s['title']}")
        print(f"      Author(s): {s['authors']}  |  {s['date']}  |  DOI: {s['doi']}")
        print()


def _print_item_detail(item: dict, annotations: list[dict] | None = None):
    d = item if "data" in item else {"data": item}
    s = _fmt_item(d.get("data", d))
    print(f"Title:   {s['title']}")
    print(f"Authors: {s['authors']}")
    print(f"Date:    {s['date']}")
    print(f"Type:    {s['itemType']}")
    print(f"DOI:     {s['doi']}")
    print()

    if annotations:
        print(f"Annotations ({len(annotations)}):")
        for a in annotations:
            color = a["color"] or "yellow"
            page = f"p.{a['page']}" if a["page"] else "?"
            print(f"  [{color}] {page}: {a['text']}")
            if a["comment"]:
                print(f"         Comment: {a['comment']}")
        print()


# ===================================================================
#  Mode 1 — Local API
# ===================================================================

class ZoteroLocal:
    """Zotero local API — requires the desktop app to be running."""

    def __init__(self):
        self.base = ZOTERO_LOCAL_API

    def _user_prefix(self) -> str:
        """Zotero local API uses user 0 for the local database."""
        return "users/0"

    def _get(self, path: str) -> list | dict:
        url = urljoin(self.base, path.lstrip("/"))
        req = urllib.request.Request(url, headers={"Zotero-API-Version": "3"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code} from {url}: {e.reason}", file=sys.stderr)
            if e.code == 404:
                print("Check that the item/collection key is correct.", file=sys.stderr)
            sys.exit(1)
        except urllib.error.URLError as e:
            print(f"Error: cannot reach Zotero at {url}", file=sys.stderr)
            print("Make sure Zotero is running.", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: non-JSON response from {url}", file=sys.stderr)
            sys.exit(1)

    def collections(self) -> list[dict]:
        data = self._get(f"{self._user_prefix()}/collections")
        return data if isinstance(data, list) else []

    def items(self, collection_key: str | None = None, limit: int = 100) -> list[dict]:
        if collection_key:
            path = f"{self._user_prefix()}/collections/{collection_key}/items/top?limit={limit}"
        else:
            path = f"{self._user_prefix()}/items/top?limit={limit}"
        data = self._get(path)
        return data if isinstance(data, list) else []

    def item_children(self, item_key: str) -> list[dict]:
        data = self._get(f"{self._user_prefix()}/items/{item_key}/children")
        return data if isinstance(data, list) else []

    def annotations(self, item_key: str) -> list[dict]:
        return _fmt_annotations(self.item_children(item_key))

    def pdf_attachment(self, item_key: str) -> dict | None:
        for c in self.item_children(item_key):
            d = c.get("data", {})
            if d.get("itemType") == "attachment" and d.get("contentType") == "application/pdf":
                return {"path": d.get("path", ""), "linkMode": d.get("linkMode"),
                        "contentType": "application/pdf"}
        return None


# ===================================================================
#  Mode 2 — Web API
# ===================================================================

class ZoteroWeb:
    """Zotero Web API — requires an API key, works without the desktop app."""

    def __init__(self, api_key: str, user_id: str | None = None):
        self.base = ZOTERO_WEB_API
        self.api_key = api_key
        self._user_id = user_id

    def _user_prefix(self) -> str:
        uid = self._user_id or self._resolve_user_id()
        return f"users/{uid}"

    def _resolve_user_id(self) -> str:
        """Fetch the user ID from the API key's owner."""
        data = self._get("keys/current")
        if isinstance(data, dict):
            uid = data.get("userID")
            if uid:
                return str(uid)
        print("Error: could not resolve user ID. Provide --user-id explicitly.", file=sys.stderr)
        sys.exit(1)

    def _get(self, path: str) -> list | dict:
        url = urljoin(self.base, path.lstrip("/"))
        req = urllib.request.Request(url, headers={
            "Zotero-API-Version": "3",
            "Authorization": f"Bearer {self.api_key}",
        })
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code} from {url}: {e.reason}", file=sys.stderr)
            if e.code == 403:
                print("Check that your API key is valid.", file=sys.stderr)
            sys.exit(1)
        except urllib.error.URLError as e:
            print(f"Error connecting to Zotero Web API: {e}", file=sys.stderr)
            sys.exit(1)

    def collections(self) -> list[dict]:
        data = self._get(f"{self._user_prefix()}/collections")
        return data if isinstance(data, list) else []

    def items(self, collection_key: str | None = None, limit: int = 100) -> list[dict]:
        if collection_key:
            path = f"{self._user_prefix()}/collections/{collection_key}/items/top?limit={limit}"
        else:
            path = f"{self._user_prefix()}/items/top?limit={limit}"
        data = self._get(path)
        return data if isinstance(data, list) else []

    def item_children(self, item_key: str) -> list[dict]:
        data = self._get(f"{self._user_prefix()}/items/{item_key}/children")
        return data if isinstance(data, list) else []

    def annotations(self, item_key: str) -> list[dict]:
        return _fmt_annotations(self.item_children(item_key))

    def pdf_attachment(self, item_key: str) -> dict | None:
        for c in self.item_children(item_key):
            d = c.get("data", {})
            if d.get("itemType") == "attachment" and d.get("contentType") == "application/pdf":
                # Web API may include a download link
                return {
                    "path": d.get("path", ""),
                    "linkMode": d.get("linkMode"),
                    "contentType": "application/pdf",
                    "download_url": d.get("url") or d.get("filename", ""),
                    "filename": d.get("filename", "paper.pdf"),
                }
        return None


# ===================================================================
#  Mode 3 — WebDAV (Nutstore 坚果云)
# ===================================================================

class NutstoreWebDAV:
    """Access Zotero attachments stored on Nutstone via WebDAV.

    Nutstone WebDAV endpoint: https://dav.jianguoyun.com/dav/
    Authentication: email + application password (not account password).
    Zotero stores files under: /dav/Zotero/<zotero-user-id>/storage/...
    """

    def __init__(self, user: str, password: str, base_url: str = NUTSTORE_WEBDAV):
        self.base = base_url.rstrip("/") + "/"
        auth_bytes = f"{user}:{password}".encode("utf-8")
        self.auth_header = "Basic " + base64.b64encode(auth_bytes).decode("ascii")

    def _request(self, method: str, path: str) -> tuple[bytes, dict]:
        url = urljoin(self.base, path.lstrip("/"))
        req = urllib.request.Request(url, method=method, headers={
            "Authorization": self.auth_header,
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read(), dict(resp.headers)
        except urllib.error.HTTPError as e:
            print(f"WebDAV HTTP {e.code} for {method} {url}: {e.reason}", file=sys.stderr)
            if e.code in (401, 403):
                print("Check your email and application password.", file=sys.stderr)
                print("(Use an app password from 坚果云账户 → 安全选项 → 应用密码)", file=sys.stderr)
            sys.exit(1)
        except urllib.error.URLError as e:
            print(f"WebDAV connection error: {e}", file=sys.stderr)
            sys.exit(1)

    def _propfind_xml(self, path: str) -> str:
        """WebDAV PROPFIND to list a directory."""
        url = urljoin(self.base, path.lstrip("/"))
        body = b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><d:displayname/><d:getcontentlength/><d:getcontenttype/><d:getlastmodified/><d:resourcetype/></d:prop></d:propfind>'
        req = urllib.request.Request(url, data=body, method="PROPFIND", headers={
            "Authorization": self.auth_header,
            "Depth": "1",
            "Content-Type": "application/xml",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            print(f"WebDAV PROPFIND HTTP {e.code} for {url}", file=sys.stderr)
            sys.exit(1)

    def list_dir(self, remote_path: str = "") -> list[dict]:
        """List files and folders at remote_path."""
        import xml.etree.ElementTree as ET
        xml_text = self._propfind_xml(remote_path)
        items = []
        root = ET.fromstring(xml_text)
        # WebDAV XML namespace
        ns = {"D": "DAV:"}
        for resp_elem in root.findall(".//D:response", ns):
            href = resp_elem.findtext("D:href", "", ns)
            if href == urljoin(self.base, remote_path.lstrip("/")):
                continue  # skip the directory itself
            name = resp_elem.findtext(".//D:displayname", "", ns)
            size = resp_elem.findtext(".//D:getcontentlength", "0", ns)
            mtime = resp_elem.findtext(".//D:getlastmodified", "", ns)
            content_type = resp_elem.findtext(".//D:getcontenttype", "", ns)
            # Determine if directory: check resourcetype first, then content-type,
            # then trailing slash in href, and only as last resort check size.
            # Nutstore may report non-zero sizes for directories, so size=="0" is unreliable.
            resource_type_elem = resp_elem.find(".//D:resourcetype", ns)
            is_collection = False
            if resource_type_elem is not None:
                is_collection = resource_type_elem.find("D:collection", ns) is not None
            is_dir = (
                is_collection or
                (content_type == "httpd/unix-directory" if content_type else False) or
                (href.rstrip("/") != href) or  # href ends with /
                (not content_type and size == "0")  # last resort
            )
            items.append({
                "href": href,
                "name": name or Path(href).name,
                "size": int(size) if size.isdigit() else 0,
                "modified": mtime,
                "is_dir": is_dir,
            })
        return items

    def download(self, remote_path: str, local_path: str):
        """Download a file from WebDAV to local disk."""
        data, headers = self._request("GET", remote_path)
        dest = Path(local_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        size = len(data)
        print(f"Downloaded {remote_path} → {local_path} ({size:,} bytes)", file=sys.stderr)
        return str(dest)


# ===================================================================
#  CLI commands — local
# ===================================================================

def cmd_local(args):
    z = ZoteroLocal()
    if args.command2 == "collections":
        cols = z.collections()
        if not cols:
            print("No collections found.")
            return
        print(f"{'Key':<12} {'Name':<40} {'Items'}")
        print("-" * 70)
        for c in cols:
            d = c.get("data", {})
            print(f"{d.get('key', '?'):<12} {d.get('name', '?'):<40} {d.get('numItems', '?')}")

    elif args.command2 == "items":
        items = z.items(args.collection)
        _print_items(items)

    elif args.command2 == "item":
        item_data = z._get(f"{z._user_prefix()}/items/{args.item_key}")
        item = item_data[0] if isinstance(item_data, list) and item_data else item_data
        anns = z.annotations(args.item_key) if args.annotations else None
        _print_item_detail(item, anns)
        if args.pdf_path:
            att = z.pdf_attachment(args.item_key)
            if att:
                print(f"PDF path: {att['path']}")
                print(f"Link mode: {att.get('linkMode', '?')}")
            else:
                print("No PDF attachment found.")


# ===================================================================
#  CLI commands — web
# ===================================================================

def cmd_web(args):
    z = ZoteroWeb(api_key=args.api_key, user_id=args.user_id)
    if args.command2 == "collections":
        cols = z.collections()
        if not cols:
            print("No collections found.")
            return
        print(f"{'Key':<12} {'Name':<40} {'Items'}")
        print("-" * 70)
        for c in cols:
            d = c.get("data", {})
            print(f"{d.get('key', '?'):<12} {d.get('name', '?'):<40} {d.get('numItems', '?')}")

    elif args.command2 == "items":
        items = z.items(args.collection)
        _print_items(items)

    elif args.command2 == "item":
        item_data = z._get(f"{z._user_prefix()}/items/{args.item_key}")
        item = item_data[0] if isinstance(item_data, list) and item_data else item_data
        anns = z.annotations(args.item_key) if args.annotations else None
        _print_item_detail(item, anns)


# ===================================================================
#  CLI commands — webdav
# ===================================================================

def cmd_webdav(args):
    wd = NutstoreWebDAV(user=args.user, password=args.password)
    if args.command2 == "ls":
        remote = args.remote_path or ""
        items = wd.list_dir(remote)
        if not items:
            print("(empty)")
            return
        print(f"{'Type':<6} {'Size':>10} {'Name'}")
        print("-" * 70)
        for item in items:
            typ = "📁" if item["is_dir"] else "📄"
            size_str = f"{item['size']:,}" if not item["is_dir"] else ""
            print(f"{typ:<6} {size_str:>10} {item['name']}")
    elif args.command2 == "get":
        dest = wd.download(args.remote_path, args.local_file)
        print(dest)


# ===================================================================
#  Main
# ===================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Fetch papers, annotations and PDFs from Zotero"
    )
    sub = parser.add_subparsers(dest="mode", help="Access mode")

    # --- local ---
    p_local = sub.add_parser("local", help="Zotero local API (app must be running)")
    p_local_sub = p_local.add_subparsers(dest="command2")
    p_local_sub.add_parser("collections", help="List collections")
    p_items = p_local_sub.add_parser("items", help="List items")
    p_items.add_argument("--collection", "-c", help="Filter by collection key")
    p_item = p_local_sub.add_parser("item", help="Show item details")
    p_item.add_argument("item_key", help="Item key")
    p_item.add_argument("--annotations", "-a", action="store_true", help="Show annotations")
    p_item.add_argument("--pdf-path", "-p", action="store_true", help="Show PDF attachment path")

    # --- web ---
    p_web = sub.add_parser("web", help="Zotero Web API (requires API key)")
    p_web.add_argument("--api-key", required=True, help="Zotero API key")
    p_web.add_argument("--user-id", help="Zotero user ID (auto-detected if omitted)")
    p_web_sub = p_web.add_subparsers(dest="command2")
    p_web_sub.add_parser("collections", help="List collections")
    p_witems = p_web_sub.add_parser("items", help="List items")
    p_witems.add_argument("--collection", "-c", help="Filter by collection key")
    p_witem = p_web_sub.add_parser("item", help="Show item details")
    p_witem.add_argument("item_key", help="Item key")
    p_witem.add_argument("--annotations", "-a", action="store_true", help="Show annotations")

    # --- webdav ---
    p_wd = sub.add_parser("webdav", help="WebDAV (Nutstone 坚果云)")
    p_wd.add_argument("--user", required=True, help="WebDAV username (email)")
    p_wd.add_argument("--password", required=True, help="WebDAV password (app password)")
    p_wd_sub = p_wd.add_subparsers(dest="command2")
    p_ls = p_wd_sub.add_parser("ls", help="List remote directory")
    p_ls.add_argument("remote_path", nargs="?", default="", help="Remote path")
    p_get = p_wd_sub.add_parser("get", help="Download remote file")
    p_get.add_argument("remote_path", help="Remote file path")
    p_get.add_argument("local_file", help="Local destination path")

    args = parser.parse_args()

    if args.mode == "local":
        cmd_local(args)
    elif args.mode == "web":
        cmd_web(args)
    elif args.mode == "webdav":
        cmd_webdav(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
