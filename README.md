# nano-banana — Claude Code skill for image generation

An auto-triggering Claude Code skill that wraps Google Gemini's **Nano Banana 2**
(`gemini-3.1-flash-image-preview`). Plain-English prompts, real PNG files on
disk, every prompt remembered in a JSON sidecar.

## Install

In Claude Code, paste this:

> Install the nano-banana skill from `https://github.com/Adam-Berger-Dev/nano-banana-claude-code-skill` into my Claude Code skills directory.

Claude will clone the repo to `~/.claude/skills/nano-banana/` and you're done.

If you'd rather run it yourself:

```bash
git clone https://github.com/Adam-Berger-Dev/nano-banana-claude-code-skill \
    ~/.claude/skills/nano-banana
```

## Set your API key

The skill reads `GEMINI_API_KEY` from `~/.env`. Get a free key at
[aistudio.google.com/apikey](https://aistudio.google.com/apikey), then:

```bash
echo 'GEMINI_API_KEY=paste-yours-here' >> ~/.env
chmod 600 ~/.env
```

The free tier is generous — generate freely.

## Use it

Open Claude Code in any project and ask:

> *"Make me a wide hero image — abstract, warm, late-afternoon light, cream and
> burnt-orange tones, no text."*

The skill auto-triggers. Claude picks it, runs `generate.py`, prints the saved
file path. The PNG opens, a JSON sidecar lands beside it.

## What's in here

| File | Purpose |
|---|---|
| [`SKILL.md`](SKILL.md) | Frontmatter description Claude reads to decide *when* to use the skill, plus the prompting/usage guide it follows |
| [`scripts/generate.py`](scripts/generate.py) | Stdlib-only Python CLI — no `pip install`, no virtualenv |

## Direct usage (without Claude Code)

```bash
python3 ~/.claude/skills/nano-banana/scripts/generate.py \
    "a tabby cat napping in a sunbeam, photo, soft window light, 35mm" \
    --aspect 1:1 --resolution 1K --output ./test.png
```

If `./test.png` lands, you're good.

## Walkthrough

Full video walkthrough + step-by-step companion page:
**[adam-berger.com/resources/nano-banana-claude-code-skill](https://adam-berger.com/resources/nano-banana-claude-code-skill)**

## License

MIT — do whatever you want with this. Attribution appreciated but not required.
