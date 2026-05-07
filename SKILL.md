---
name: nano-banana
description: Generate or edit images using Google Gemini's Nano Banana 2 model (gemini-3.1-flash-image-preview) via a bundled stdlib-only Python CLI. Use this skill whenever the user asks to make, generate, create, draw, render, design, or edit any image, illustration, photo, mockup, visual, cover, poster, icon, graphic, or scene — including when they describe a visual without explicitly using the word "image". Also use it for any reference to Gemini image generation, Nano Banana, or AI image generation in general.
---

# Nano Banana — Gemini Image Generation

Generate or edit images with Google's `gemini-3.1-flash-image-preview` model (a.k.a. Nano Banana 2) via the stdlib-only CLI bundled at `scripts/generate.py`.

This skill is the **engine**. Other skills (e.g. `youtube-thumbnails`) layer purpose-specific defaults on top by calling the same script. Keep this skill general — don't bake use-case opinions in here.

A sibling skill **`openai-image`** wraps OpenAI's `gpt-image-2` with a CLI-compatible interface. Reach for it when **in-image text rendering** is critical (titles, posters with words) — gpt-image-2 is meaningfully better at legible text. For general work, faces, character references, and cheaper iteration, this skill (Nano Banana) is the right default.

## When to trigger

Any request to produce or modify a picture: thumbnails, illustrations, mockups, hero images, social posts, icons, posters, photo edits, character art, infographics, product shots. Also trigger when the user describes a visual scene without saying "image" — *"I want something showing a designer at her desk with neon lighting"* is an image request.

If a more specific skill applies (e.g. `youtube-thumbnails`), follow that skill for prompting and defaults, then call this skill's script to actually run the generation.

## How to call the script

```bash
python ~/.claude/skills/nano-banana/scripts/generate.py "<prompt>" \
    --aspect <ratio> \
    --resolution <size> \
    [--image <input.png> ...] \
    [--output <path.png>]
```

The script prints the saved PNG path on stdout. Default output: `./generated-images/<timestamp>-<slug>.png` plus a `.json` sidecar with the prompt and config.

For long or multi-line prompts, pipe via stdin:

```bash
python ~/.claude/skills/nano-banana/scripts/generate.py - <<'EOF'
your long, multi-line prompt
EOF
```

After running, **always show the user the saved path** so they can open the file. If the cwd has a more natural place to save (e.g. `slides/assets/` in a slide-deck project), pass `--output` to put it there.

## Crafting the prompt — the one rule

The model's #1 strength is language understanding. **Describe the scene as a paragraph, not a list of keywords.** A coherent narrative beats `cyberpunk, neon, futuristic, 4k, masterpiece` every time.

A strong prompt usually combines:

1. **Subject** — concrete detail. *"A gray tabby cat with a torn left ear"* beats *"a cat"*.
2. **Context / intent** — what is this image *for*? *"Logo for a high-end minimalist skincare brand"* gives the model a north star.
3. **Style / medium** — photo, oil painting, cel-shaded illustration, isometric 3D render, watercolor, vector flat illustration, etc.
4. **Composition** — close-up, wide shot, low-angle, over-the-shoulder, top-down, rule of thirds.
5. **Lighting** — golden hour, harsh studio strobe, soft window light, neon glow, moody chiaroscuro.
6. **Camera language** (for photographic styles) — 35mm portrait, macro, shallow depth of field, motion blur.
7. **Color palette** — explicit colors beat vague *"vibrant"*.
8. **What to omit** — phrase positively. Prefer *"empty deserted street"* over *"no cars"*.

When the user gives a vague request, **upgrade it** before generating: propose a one-paragraph concept, confirm with the user, then call the script. Don't silently invent details that change the meaning.

For extended templates, vocabulary, and lighting/lens cookbooks, see [`references/prompting.md`](references/prompting.md). Read it for high-stakes prompts (hero shots, deliverables) or when the user's request is too thin to act on.

## Aspect ratio and resolution

Supported aspect ratios: `1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9, 1:4, 4:1, 1:8, 8:1`.

Supported resolutions: `512, 1K, 2K, 4K` — **capital K is required**, the API rejects lowercase.

When the user hasn't specified, default like this:

| Use | Aspect | Resolution |
|---|---|---|
| Square social / icon | `1:1` | `1K` |
| Wide hero / 16:9 thumbnail | `16:9` | `2K` |
| Vertical phone / Story / Short cover | `9:16` | `1K` |
| Portrait poster / IG feed | `4:5` | `2K` |
| Cinemascope banner | `21:9` | `2K` |

Higher resolutions cost more tokens (512≈747, 1K≈1120, 2K≈1680, 4K≈2520). Default to `1K` unless the image is going to be displayed large or the user asks for "high detail" / "print" / "hero".

## Where to find reference images

By convention, the user keeps reference images (headshots, logos, product shots, mood boards, etc.) in **`./image-gen-resources/`** in the project's working directory. When the user mentions a specific filename — *"use my headshot"*, *"combine logo.png and product.jpg"*, *"the wireframe in my resources folder"* — look there first.

Resolution order for a referenced filename:
1. `./image-gen-resources/<name>` (case-insensitive match on filename + extension)
2. `./<name>` (project root)
3. The exact path the user provided, if it looks like a path

**Never auto-inject reference images.** Only pass `--image` when the user *explicitly* references one or more files. Do not browse `image-gen-resources/` and silently include things they didn't ask for — the folder is a staging area for *available* references, not a default-include list.

If the user references a file that doesn't exist, run `ls image-gen-resources/` and ask which file they actually meant.

## Editing an existing image

Pass `--image <path>` to apply edits. To do real inpainting, describe the change conversationally and pin everything that should stay:

> *"Change only the blue sofa to a vintage brown leather chesterfield. Keep the rest of the room — including the pillows and the window light — exactly the same."*

You can pass `--image` multiple times. The model accepts up to **10 object references** + **4 character references** in one call (14 total). The order matters less than that the prompt explicitly references each one (*"the cat in image 1, the kitchen in image 2"*).

### Preserving identity (faces, characters, products)

When the reference is a person or a recognizable object and you want the *same* person/object rendered into a new scene, the model needs explicit anchoring or it drifts. Encode these in the prompt:

- **Lock identity features.** *"Preserve the exact facial features, hair, skin tone, and clothing from the reference image."* Without this, the output looks "similar" but not quite right.
- **Big pose / expression changes degrade likeness.** Neutral → smiling preserves well; neutral → open-mouthed shouting distorts. Stay close to the reference's pose where you can.
- **Anything not visible in the reference will be invented.** A chest-up headshot cannot anchor what the arms do — generated arms often look anatomically off. Keep arm/hand prompts vague rather than specific, or crop tighter.
- **For higher fidelity, supply more references.** Up to 4 character reference images per call. A second photo showing the desired expression or pose dramatically improves results when the change is large.

## Iterating on a result

The Gemini docs explicitly recommend multi-turn iteration over re-rolling. The bundled CLI is one-shot, so to iterate:

1. Read the sidecar `.json` to recover the previous prompt.
2. Use the previous output PNG as `--image` and write a *change-only* prompt: *"Take this and make the lighting warmer. Keep the composition identical."*
3. Save to a new path (the timestamped filename avoids overwriting).

This preserves the parts you liked instead of rolling fresh dice.

## Critical quirks

- **No transparency.** The model can't render alpha. For PNG-on-white compositing assets, ask explicitly: *"isolated on a pure white background, no shadow."*
- **Text rendering is the weak spot.** For images with text (slide titles, posters), the docs recommend: write the text first, then ask for an image incorporating it. Keep it to 1-5 words. Specify font character (*"bold geometric sans-serif"*) and placement.
- **SynthID watermark.** Every image is invisibly watermarked by Google. No opt-out. Mention it if the user is doing client work where provenance matters.
- **Multiple variants in one call.** The model often returns one image even if you ask for several. To produce variants, call the script N times with the same prompt — each call uses a fresh seed.
- **Safety refusals.** Exit code `3` ("no image returned") usually means the model refused on policy grounds: real-person likenesses, copyrighted characters, violence, etc. Reframe and retry.
- **Languages.** Best results in: EN, AR-EG, DE, ES-MX, FR, HI, ID, IT, JA, KO, PT-BR, RU, UA, VI, ZH-CN.

For the full API surface and gotchas reference, see [`references/api-quirks.md`](references/api-quirks.md).

## API key resolution

The script searches in order:
1. `$GEMINI_API_KEY` environment variable
2. `./.env` in the current working directory
3. `~/.env` in the user's home directory

Get a key at https://aistudio.google.com/apikey. The free tier is generous for experimentation.
