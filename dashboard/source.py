"""Where the workbook comes from.

Order of preference:
1. A file uploaded in the sidebar (explicit, for this session only).
2. SharePoint through Microsoft Graph, when credentials are in st.secrets.
3. A local path, e.g. a SharePoint library synced with OneDrive.

Nothing here stores data in the repository; credentials live in
.streamlit/secrets.toml (never committed) or in the hosting platform's
secrets settings.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

GRAPH = "https://graph.microsoft.com/v1.0"
TIMEOUT = 30


@dataclass
class Loaded:
    content: bytes
    origin: str          # "upload" | "sharepoint" | "local"
    label: str           # shown in the masthead
    file_name: str
    modified: datetime | None = None


class SourceError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# SharePoint link parsing
# ---------------------------------------------------------------------------
@dataclass
class SharePointTarget:
    hostname: str
    site_path: str            # e.g. /teams/Quality
    item_guid: str | None     # list item unique id from ?sourcedoc={...}
    file_name: str | None
    drive_path: str | None    # path inside the document library, if given


def parse_sharepoint_url(url: str) -> SharePointTarget:
    """Understand the links people copy from SharePoint / Excel online.

    Handles '/:x:/r/teams/<site>/_layouts/15/Doc.aspx?sourcedoc={GUID}&file=Name.xlsx'
    and direct document links like '/teams/<site>/Shared Documents/Folder/Name.xlsx'.
    """
    u = urlparse(url.strip())
    if not u.hostname:
        raise SourceError("The SharePoint link has no host name.")
    path = unquote(u.path)
    path = re.sub(r"^/:[a-z]:/[a-z]/", "/", path)  # strip sharing prefix like /:x:/r/
    m = re.match(r"^(/(?:sites|teams)/[^/]+)(/.*)?$", path)
    if not m:
        raise SourceError("The SharePoint link doesn't contain a /sites/... or /teams/... path.")
    site_path, rest = m.group(1), (m.group(2) or "")
    q = parse_qs(u.query)
    guid = None
    if "sourcedoc" in q:
        guid = q["sourcedoc"][0].strip("{}").lower()
    file_name = q.get("file", [None])[0]
    drive_path = None
    if rest and "/_layouts/" not in rest and rest.lower().endswith((".xlsx", ".xlsm", ".xls")):
        parts = rest.strip("/").split("/")
        # first segment is the library ("Shared Documents"); Graph paths are relative to it
        drive_path = "/".join(parts[1:]) if len(parts) > 1 else parts[0]
        file_name = file_name or parts[-1]
    return SharePointTarget(u.hostname, site_path, guid, file_name, drive_path)


# ---------------------------------------------------------------------------
# Microsoft Graph download (app-only, client credentials)
# ---------------------------------------------------------------------------
def _token(tenant_id: str, client_id: str, client_secret: str) -> str:
    try:
        import msal  # imported lazily so the app runs without it when SharePoint isn't used
    except ImportError as exc:  # pragma: no cover
        raise SourceError("The 'msal' package is missing. Add it to requirements.txt.") from exc
    app = msal.ConfidentialClientApplication(
        client_id, authority=f"https://login.microsoftonline.com/{tenant_id}", client_credential=client_secret)
    res = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in res:
        raise SourceError(f"Sign-in to Microsoft failed: {res.get('error_description') or res.get('error')}")
    return res["access_token"]


def _get(session, url: str, **kw):
    r = session.get(url, timeout=TIMEOUT, **kw)
    if r.status_code == 403:
        raise SourceError("SharePoint refused access (403). The app registration needs read access to this site.")
    if r.status_code == 404:
        raise SourceError("SharePoint couldn't find the site or file (404). Check the link in the secrets.")
    r.raise_for_status()
    return r


def fetch_sharepoint(cfg: dict) -> Loaded:
    import requests

    for k in ("tenant_id", "client_id", "client_secret", "file_url"):
        if not cfg.get(k):
            raise SourceError(f"SharePoint secret '{k}' is missing.")
    target = parse_sharepoint_url(cfg["file_url"])
    if cfg.get("drive_path"):
        target.drive_path = cfg["drive_path"].strip("/")

    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {_token(cfg['tenant_id'], cfg['client_id'], cfg['client_secret'])}"
    site = _get(s, f"{GRAPH}/sites/{target.hostname}:{quote(target.site_path)}").json()
    site_id = site["id"]

    item = None
    drive_id = None
    if target.drive_path:
        drive = _get(s, f"{GRAPH}/sites/{site_id}/drive").json()
        drive_id = drive["id"]
        item = _get(s, f"{GRAPH}/drives/{drive_id}/root:/{quote(target.drive_path)}").json()
    else:
        name = target.file_name or ""
        query = re.sub(r"\.[^.]+$", "", name).replace("'", "''") or "xlsx"
        drives = _get(s, f"{GRAPH}/sites/{site_id}/drives").json().get("value", [])
        for drv in drives:
            res = _get(s, f"{GRAPH}/drives/{drv['id']}/root/search(q='{quote(query)}')",
                       params={"$select": "id,name,sharepointIds,lastModifiedDateTime,file"}).json()
            for it in res.get("value", []):
                if "file" not in it:
                    continue
                uid = (it.get("sharepointIds") or {}).get("listItemUniqueId", "").strip("{}").lower()
                if (target.item_guid and uid == target.item_guid) or (not target.item_guid and it.get("name") == name):
                    item, drive_id = it, drv["id"]
                    break
            if item:
                break
        if not item:
            raise SourceError(f"'{name or 'the workbook'}' wasn't found in the site's document libraries.")

    content = _get(s, f"{GRAPH}/drives/{drive_id}/items/{item['id']}/content").content
    modified = None
    if item.get("lastModifiedDateTime"):
        modified = datetime.fromisoformat(item["lastModifiedDateTime"].replace("Z", "+00:00"))
    return Loaded(content, "sharepoint", "SharePoint", item.get("name") or target.file_name or "workbook.xlsx", modified)


# ---------------------------------------------------------------------------
# Local / synced path
# ---------------------------------------------------------------------------
def local_path(secrets: dict | None) -> str | None:
    env = os.environ.get("TROLLEY_XLSX_PATH")
    if env:
        return env
    if secrets and isinstance(secrets.get("local"), dict):
        return secrets["local"].get("path")
    return None


def read_local(path: str) -> Loaded:
    p = Path(os.path.expandvars(os.path.expanduser(path)))
    if not p.exists():
        raise SourceError(f"The file '{p}' doesn't exist (yet). If it's a OneDrive folder, check it has synced.")
    mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
    return Loaded(p.read_bytes(), "local", "Synced folder", p.name, mtime)
