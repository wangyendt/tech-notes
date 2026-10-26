#!/usr/bin/env python3
"""Build the public site without editing the canonical external book.

Only the declared book subtree and static assets are copied. No source repository
code, hooks, notebooks or build commands are executed.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.parse
import urllib.request
import unicodedata
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import yaml

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache"
GENERATED = CACHE / "generated"
DOCS = GENERATED / "docs"
CONFIG = ROOT / ".site-config.yml"
LINK = re.compile(r"(!?\[[^\]]*\]\()([^)]+)(\))")
SOURCE_NAME = re.compile(r"(?:^|/)README\.md(?=$|#)")
# These checks protect this case study's required anonymization, not all possible secrets.
class PrivateMarkers:
    """Keep identifying deny markers out of the public source, including this guard."""
    def search(self, text: str) -> str | None:
        normalized = "".join(unicodedata.normalize("NFKC", text).casefold().split())
        bank = json.loads((ROOT / "anonymization.json").read_text())["sha256_by_normalized_length"]
        for width, hashes in bank.items():
            width, hashes = int(width), set(hashes)
            for index in range(len(normalized) - width + 1):
                candidate = normalized[index:index + width].encode()
                if hashlib.sha256(candidate).hexdigest() in hashes:
                    return "PRIVATE_MARKER"
        return None


FORBIDDEN = PrivateMarkers()


def run(*args: str, cwd: Path | None = None) -> str:
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def download(url: str, limit: int = 20_000_000) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "tech-notes-static-builder"})
    with urllib.request.urlopen(request, timeout=45) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("download exceeded fixed size limit")
    return data


def rewrite_links(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        target = match[2]
        if target.startswith(("https:", "http:", "mailto:", "#")):
            return match[0]
        target = re.sub(r"(^|/)README\.md(?=$|#)", r"\1index.md", target)
        return match[1] + target + match[3]
    return LINK.sub(replace, text)


def page_title(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem


def book_navigation(book: Path, mount: str) -> list[dict[str, str]]:
    """Honor the source README's reading order; include new root chapters too."""
    ordered = ["README.md"]
    for match in LINK.finditer((book / "README.md").read_text(encoding="utf-8")):
        name = urllib.parse.unquote(match[2].split("#", 1)[0])
        if name.endswith(".md") and "/" not in name and name not in ordered:
            ordered.append(name)
    for path in sorted(book.glob("*.md")):
        if path.name not in ordered:
            ordered.append(path.name)
    result = []
    for name in ordered:
        path = book / name
        if not path.is_file() or path.is_symlink():
            raise ValueError("source table of contents points to a missing or unsafe chapter")
        destination = "index.md" if name == "README.md" else name
        result.append({"全书导读" if name == "README.md" else page_title(path): f"{mount}/{destination}"})
    return result


def copy_tree(source: Path, destination: Path, book_meta: dict | None = None) -> None:
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise ValueError("symlinks in publishable content are not allowed")
        if not path.is_file() or path.name == ".DS_Store" or "__pycache__" in path.parts:
            continue
        rel = path.relative_to(source)
        # Image-generation working notes are not part of the published book.
        if book_meta and rel.parts[0] == "assets" and path.suffix == ".md":
            continue
        if path.suffix.lower() not in {".md", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".css", ".js", ".py", ".txt", ".bib"}:
            raise ValueError(f"unreviewed publication file type: {path.name}")
        target = destination / rel
        if target.name == "README.md":
            target = target.with_name("index.md")
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".md":
            text = rewrite_links(path.read_text(encoding="utf-8"))
            if book_meta:
                url = book_meta["base_url"] + urllib.parse.quote(str(rel), safe="/")
                note = ('\n!!! info "源项目同步章节"\n'
                        f'    正文来自[源文件]({url})，提交 `{book_meta["commit"][:12]}`。'
                        '章节状态与原文一致；本站展示不代表新的推导审查。\n')
                lines = text.splitlines(keepends=True)
                first_h1 = next((i for i, line in enumerate(lines) if line.startswith("# ")), None)
                if first_h1 is None:
                    text = note + "\n" + text
                else:
                    lines.insert(first_h1 + 1, "\n" + note + "\n")
                    text = "".join(lines)
            target.write_text(text, encoding="utf-8")
        else:
            shutil.copyfile(path, target)


def checkout_book(spec: dict, explicit: Path | None, ref: str | None) -> tuple[Path, dict]:
    branch = ref or spec["ref"]
    if explicit:
        checkout = explicit.resolve()
        if run("git", "status", "--porcelain", "--", spec["path"], cwd=checkout):
            raise ValueError("the source book has uncommitted changes; commit it before a reproducible build")
    else:
        checkout = CACHE / "upstream-book"
        if not (checkout / ".git").exists():
            run("git", "clone", "--filter=blob:none", "--sparse", "--no-checkout", "--depth", "1",
                f'https://github.com/{spec["repository"]}.git', str(checkout))
        run("git", "-c", "core.hooksPath=/dev/null", "fetch", "--depth", "1", "origin", branch, cwd=checkout)
        run("git", "sparse-checkout", "set", "--", spec["path"], cwd=checkout)
        run("git", "-c", "core.hooksPath=/dev/null", "checkout", "--detach", "FETCH_HEAD", cwd=checkout)
    commit = run("git", "rev-parse", "HEAD", cwd=checkout)
    tree = run("git", "rev-parse", f'{commit}:{spec["path"]}', cwd=checkout)
    book = checkout / spec["path"]
    if not (book / "README.md").is_file():
        raise ValueError("source book README missing")
    meta = {"repository": spec["repository"], "ref": branch, "commit": commit, "tree": tree,
            "path": spec["path"], "mount": spec["mount"],
            "base_url": f'https://github.com/{spec["repository"]}/blob/{commit}/{spec["path"]}/'}
    return book, meta


def fingerprint(book_tree: str) -> str:
    digest = hashlib.sha256(book_tree.encode())
    paths = [ROOT / "books.json", ROOT / "mkdocs.yml", ROOT / "requirements.lock", ROOT / "vendor.lock.json", ROOT / "anonymization.json"]
    paths += list((ROOT / "content").rglob("*"))
    paths += list((ROOT / "scripts").glob("*.py"))
    for path in sorted(paths):
        if path.is_file() and not path.is_symlink() and "__pycache__" not in path.parts and path.name != ".DS_Store":
            digest.update(str(path.relative_to(ROOT)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def is_current(url: str, expected: str) -> bool:
    try:
        return json.loads(download(url.rstrip("/") + "/build-info.json", 100_000))["fingerprint"] == expected
    except Exception:
        return False  # Missing/unreachable site does not erase the last deployment.


def install_mathjax() -> None:
    spec = json.loads((ROOT / "vendor.lock.json").read_text())["mathjax"]
    archive = CACHE / f'mathjax-{spec["version"]}.tgz'
    if not archive.exists():
        archive.write_bytes(download(spec["url"]))
    raw = archive.read_bytes()
    integrity = "sha512-" + base64.b64encode(hashlib.sha512(raw).digest()).decode()
    if integrity != spec["integrity"]:
        raise ValueError("MathJax package checksum mismatch")
    destination = DOCS / "vendor/mathjax"
    total = 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as bundle:
        for member in bundle:
            parts = PurePosixPath(member.name).parts
            if not (member.name.startswith("package/es5/") or member.name == "package/LICENSE"):
                continue
            if ".." in parts or member.issym() or member.islnk():
                raise ValueError("unsafe dependency archive path")
            if not member.isfile():
                continue
            total += member.size
            if total > 100_000_000:
                raise ValueError("dependency asset size exceeded")
            target = destination.joinpath(*parts[1:])
            target.parent.mkdir(parents=True, exist_ok=True)
            stream = bundle.extractfile(member)
            if stream is None:
                raise ValueError("dependency asset missing")
            target.write_bytes(stream.read())


def validate_content() -> None:
    """Verify local links, anonymization and absence of obvious local/private artifacts."""
    for path in DOCS.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        if "/Users/" in text or re.search(r"-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY", text):
            raise ValueError("local path or private key found in publishable content")
        if "android-wearable-heart-rate" in path.parts and FORBIDDEN.search(text):
            raise ValueError("case-study anonymization check failed")
        for match in LINK.finditer(text):
            target = match[2].split(' "', 1)[0]
            parsed = urllib.parse.urlsplit(target)
            if parsed.scheme or target.startswith("#"):
                continue
            local = (path.parent / urllib.parse.unquote(parsed.path)).resolve()
            if not local.is_relative_to(DOCS.resolve()) or not local.exists():
                raise ValueError(f"broken or escaping local link in {path.relative_to(DOCS)}: {target}")
    case = DOCS / "systems/android-wearable-heart-rate"
    for path in case.rglob("*"):
        if path.suffix in {".svg", ".py", ".txt"} and FORBIDDEN.search(path.read_text(encoding="utf-8")):
            raise ValueError("case-study asset anonymization check failed")


def prepare(explicit: Path | None = None, ref: str | None = None, check_url: str | None = None, force: bool = False) -> dict:
    CACHE.mkdir(exist_ok=True)
    spec = json.loads((ROOT / "books.json").read_text())
    book, meta = checkout_book(spec, explicit, ref)
    info = {"fingerprint": fingerprint(meta["tree"]), "book": meta,
            "built_at": datetime.now(timezone.utc).isoformat(), "generator": "Zensical"}
    if check_url and not force and is_current(check_url, info["fingerprint"]):
        return {**info, "changed": False}
    if GENERATED.exists():
        shutil.rmtree(GENERATED)
    DOCS.mkdir(parents=True)
    copy_tree(ROOT / "content", DOCS)
    copy_tree(book, DOCS / spec["mount"], meta)
    provenance = DOCS / "sources/index.md"
    provenance.parent.mkdir(parents=True, exist_ok=True)
    source_url = meta["base_url"] + "README.md"
    canonical = provenance.read_text(encoding="utf-8")
    provenance.write_text(canonical + f'''

## 当前构建来源

| 项目 | 当前构建 |
|---|---|
| 源仓库 | [{meta["repository"]}](https://github.com/{meta["repository"]}) |
| 跟随分支 | `{meta["ref"]}` |
| 源提交 | [`{meta["commit"][:12]}`](https://github.com/{meta["repository"]}/commit/{meta["commit"]}) |
| 书籍目录树 | `{meta["tree"]}` |
| 源目录 | [{spec["path"]}]({source_url}) |
''', encoding="utf-8")
    config = yaml.safe_load((ROOT / "mkdocs.yml").read_text())
    def replace(value):
        if value == "__KALIBR_BOOK__":
            return book_navigation(book, spec["mount"])
        if isinstance(value, list):
            return [replace(v) for v in value]
        if isinstance(value, dict):
            return {k: replace(v) for k, v in value.items()}
        return value
    config = replace(config)
    config["docs_dir"] = str(DOCS.relative_to(ROOT))
    config["site_dir"] = "site"
    CONFIG.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    (DOCS / "build-info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validate_content()
    install_mathjax()
    return {**info, "changed": True}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book-checkout", type=Path, help="Use a clean local source checkout instead of fetching GitHub")
    parser.add_argument("--source-ref", help="Optional source ref for a remote build")
    parser.add_argument("--check-url", help="Skip if the published fingerprint is unchanged")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    result = prepare(args.book_checkout, args.source_ref, args.check_url, args.force)
    if args.github_output:
        with args.github_output.open("a") as out:
            out.write(f'changed={str(result["changed"]).lower()}\n')
            out.write(f'book_commit={result["book"]["commit"]}\n')
    if result["changed"] and not args.prepare_only:
        subprocess.run([sys.executable, "-m", "zensical", "build", "--strict", "--config-file", str(CONFIG)], check=True, cwd=ROOT)
    print(json.dumps({"changed": result["changed"], "book_commit": result["book"]["commit"], "fingerprint": result["fingerprint"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
