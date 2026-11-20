"""Render the project summary as plain text."""


def render(state: dict) -> str:
    out = [f"paper: {state['title'] or '(untitled)'}  [{state['lang']}]"]
    brief = state["brief"]
    out.append(f"brief: {brief['status']}  message: {brief['message'] or '(not written)'}")
    if brief["findings"]:
        listed = ", ".join(f"{f['id']} {f['status'] or '(no status)'}" for f in brief["findings"])
        out.append(f"  findings: {listed}")
    out.append(f"  open items in BRIEF.md: {brief['open_items']}")
    out.extend(f"    - {item}" for item in brief["open_item_texts"][:3])

    for key, label in (("project", "STYLE.md"), ("shared", "shared")):
        style = state["style"][key]
        if not style["path"]:
            continue
        name = label if key == "project" else f"shared {style['path']}"
        if not style["exists"]:
            out.append(f"style: {name} (missing)")
            continue
        extra = f", {style['pending']} waiting to be shared" if style["pending"] else ""
        out.append(
            f"style: {name}: {style['rules']} rules, {style['candidates']} candidates{extra}"
        )

    out.append("sources:" if state["sources"] else "sources: (none; add [[sources]] to paper.toml)")
    for src in state["sources"]:
        if not src["exists"]:
            out.append(f"  - {src['name']}: {src['path']} (missing)")
            continue
        kind = "runops project" if src["runops"] else "directory"
        log = f", LOG.md {src['log_updated']}" if src["log_updated"] else ""
        out.append(f"  - {src['name']}: {src['path']} ({kind}{log})")
        out += [f"      {topic}" for topic in src["analysis"]]

    manuscript = state["manuscript"]
    build = state["build"]
    built = "not built"
    if build["pdf"]:
        built = f"{build['pdf']} {build['built']}" + (" (stale)" if build["stale"] else "")
    out.append(f"manuscript: {manuscript['main']}, {manuscript['paragraphs']} paragraphs; {built}")

    out.append("figures:" if state["figures"] else "figures: (none)")
    for fig in state["figures"]:
        out.append(
            f"  - {fig['name']}: {fig['message'] or '(no message in figure.md)'}\n"
            f"      {fig['status']}, {fig['rounds']} review rounds, "
            f"output {fig['output']}"
        )

    predictions = state["predictions"]
    if predictions["marks"]:
        where = ", ".join(f"{name} {n}" for name, n in predictions["files"].items())
        out.append(f"predictions: {predictions['marks']} \\pred marks ({where})")
    else:
        out.append("predictions: no \\pred marks")

    comments = state["comments"]
    out.append(f"comments: {len(comments)} open" if comments else "comments: none open")
    for c in comments:
        out.append(f"  - {c['file']}:{c['line']}: {c['text']}")
        if c["target"]:
            out.append(f"      on: {c['target']}")

    out += [f"next: {hint}" for hint in state["next"]]
    return "\n".join(out)
