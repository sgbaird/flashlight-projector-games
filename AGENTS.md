# Flashlight Projector Games

Sterling's (`sgbaird`) projector activities: a camera watches the projected wall and children control figures with
flashlights. `README.md` covers the activity chooser and setup.

- Python with OpenCV, NumPy, pygame and PyYAML (`requirements.txt`).
- `flashlight_scripture_maze/activity.py` is the Scripture Maze entry point (pygame, screens, walker, dwell buttons). Screens: title, story card, story
  pages (the book's panels, with their cited verses as buttons), scripture, maze, ending, and the map that
  reaches all of them; each screen sets its buttons with `set_buttons`. `maze.py` (generation, paths, item
  placement) and `flashlight_scripture_maze/flashlight.py` (calibration geometry, multi-spot detection, camera thread) have no pygame, so they
  are unit-tested. `art.py` turns the downloaded pictures into cards and circular portraits; `pictures.py` draws the
  animals, goal pictures (ark, tent, city) and faint scenery with pygame shapes. `stories.py` lists
  the stories, their picture crops and songs. `fetch_art.py` downloads the pictures, the story pages (`panels` in
  `art/<slug>/story.json`, each with the verses it cites), scripture passages and songs' instrumental
  accompaniments. `scooby_doo_pac_man/activity.py` is the cooperative Pac-Man-style activity; its pure rules live
  in `engine.py`, character metadata and portrait fallbacks in `characters.py`, and ignored local media in
  `local_assets/`.
- Check changes with `python -m pytest` and
  `python -m py_compile flashlight_scripture_maze/*.py scooby_doo_pac_man/*.py`. The activities need a projector,
  camera and display, so a CI runner cannot run them; each `activity.py --mouse --window` runs without a camera.
  Say what was not run.
- Keep the projected picture dim: dark sky, muted walls (`WALL`), portraits dimmed (`art.portrait`). The
  detector finds a flashlight as a patch that is both much brighter than the learned background and bright
  in absolute terms and big enough (`DIFF`, `MIN_LEVEL`, `MIN_AREA` in `flashlight_scripture_maze/flashlight.py`). Anything bright and moving that the activity draws can
  be mistaken for the flashlight; never draw a marker at the detected spot (it would detect itself).
- Content must suit Sunday: scripture stories told as in *Old Testament Stories*, gentle sounds, nothing scary
  or violent (the lions are quiet; David's maze is about gathering stones, not the fight).
- Call Flashlight Scripture Maze an **activity**, never a game. “Scooby-Doo Pac-Man” is the requested game name,
  but “activity” is preferred for generic UI and documentation wording.
- Testing Scripture Maze with the camera (local sessions):
  `python flashlight_scripture_maze/activity.py --camera 1 --record <dir>` saves the camera
  video, the projected picture and a log. Blur faces locally (an offline model such as `deface`) before
  looking at any camera frame, and never commit the videos: the camera shows the room and family, and the
  screen video shows church pictures. The logs (`log.jsonl`) and a transcript without tool outputs may be
  committed for provenance under `docs/provenance/<date>/`.

## Church media: never commit it

The *Old Testament Stories* pictures and text and *Children's Songbook* music are © Intellectual Reserve, Inc.,
licensed for personal, noncommercial use. This repository is public, so:

- Never commit pictures, story text, audio or sheet music from churchofjesuschrist.org (or the *Friend*
  magazine). `flashlight_scripture_maze/art/` is git-ignored; `fetch_art.py` fills it on the player's computer.
- Links are fine: story pages, song pages (`https://www.churchofjesuschrist.org/media/music/songs/<slug>`), and
  the image IDs the content API returns. Before adding a song, check that its page title is the song's name; an
  unknown slug still returns HTTP 200 with the title "Music Library".
- Mazes are generated, never traced or copied from the *Friend*.
- A Codex session on GitHub cannot see `art/`, so the activity must work without it (drawn figures).

## Scooby-Doo and Pac-Man media: never commit it

- Keep character headshots, villain portraits, logos, sounds, and other branded media under the ignored
  `scooby_doo_pac_man/local_assets/` directory. Never commit a private URL manifest.
- The installer may copy files or download user-supplied direct URLs for private, noncommercial local use. Do not
  add copyrighted media or fixed proprietary asset URLs to the public repository.
- The activity must remain usable with its generated maze and drawn initial portraits when local assets are absent.

## @codex on GitHub

`@codex` (`.github/workflows/codex.yml`) in an issue (title or body) or an issue or PR conversation comment starts
a Codex session, for anyone with write access. Model and effort tags: `@codex+gpt-6-luna:high`, `@codex:low`; a bare
tag uses the plan's defaults. On an issue, a session that changes files opens a pull request from its branch. The pull
request description holds the full write-up and key images; the reply on the issue is one sentence linking it. (If
it cannot open one, the write-up goes in the reply with a compare link.) Efforts: `none`, `minimal`, `low`, `medium`,
`high`, `xhigh`, `max`, `ultra` (each model accepts a subset). The first tag with a `+model` or `:effort` wins,
wherever it is in the title or body. On an issue the session works on a new `codex/issue-<n>-<run>` branch; on a PR it
pushes to the PR's branch. Every `@codex` starts at once, so other sessions may be working on the same issue or PR:
check with `gh run list -w codex.yml --status in_progress` and the thread's "working on this" comments, and on a
shared PR branch `git pull --rebase` before each push rather than force-pushing. Cancel a run from the Actions tab.
While it runs, its "working on this" comment shows the plan, the latest interim message and the recent commands
(never their output), updated about once a minute, so anything a session writes in an interim message or a command
line is public on this repository.

## The shared Codex login (for Sterling and for sessions)

Every run uses one ChatGPT-managed login (`auth.json`), following
https://learn.chatgpt.com/docs/auth/ci-cd-auth for ephemeral runners. Same design as `sgbaird/balloon-pop-game`
and `ME-EN-250/me-en-250-private`, each with its own separate login.

- `.github/actions/codex-run` restores the newest encrypted copy from the Actions cache (key prefix `codex-auth-`),
  falling back to the `CODEX_AUTH_JSON` secret, and saves a new encrypted copy whenever Codex rewrote the file.
  `CODEX_AUTH_KEY` is the encryption passphrase. No token with secret-write access is involved.
- `codex-keepalive.yml` forces a refresh on Mondays and Thursdays. Codex itself refreshes only within 5 minutes of
  the 10-day access token's expiry (or on a 401), so ordinary runs never refresh and can run in parallel.
- This repository is public: GitHub turns off scheduled workflows after 60 days with no repository activity. If the
  keep-alive stops, re-enable it under Actions and reseed.
- Sessions: never read, print or copy anything under `$CODEX_HOME`.
- **Reseed** if a run fails with "Reseed CODEX_AUTH_JSON", or the keep-alive fails twice in a row. On Sterling's
  PC, in PowerShell: `$env:CODEX_HOME="$env:USERPROFILE\.codex-ci-maze"; npx -y @openai/codex@0.165.0 login`,
  then `gh secret set CODEX_AUTH_JSON -R sgbaird/flashlight-projector-games < $env:USERPROFILE\.codex-ci-maze\auth.json`,
  delete the cache entries (`gh cache delete --all -R sgbaird/flashlight-projector-games`), run the keep-alive by
  hand (`gh workflow run codex-keepalive.yml -R sgbaird/flashlight-projector-games`), and then delete the local
  `auth.json`. Never use that CODEX_HOME for local work, and never reuse another repository's CI login: the CI
  copy rotates its tokens, and two holders of one login log each other out.
- If `npx` fails with "Could not read package.json" under `npm-cache\_npx` (a broken npx cache, as on 2026-11-01),
  install the same version into a folder and run it from there:
  `npm install --prefix $env:TEMP\codex-cli @openai/codex@0.165.0`, then
  `& $env:TEMP\codex-cli
ode_modules\.bin\codex.cmd login` (with `CODEX_HOME` set as above). Delete the folder
  afterwards.
