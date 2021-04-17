#!/usr/bin/env python3
import argparse
import logging
import os
import re
import subprocess
import sys

__version__ = "1.0.0b"

log = logging.getLogger(__name__)
streamer = logging.StreamHandler()
formatter = logging.Formatter(
    fmt="[{asctime}] [{levelname:^10}] {message}",
    datefmt="%Y/%m/%d %H:%M:%S",
    style="{",
)
streamer.setFormatter(formatter)
log.addHandler(streamer)

FONT_HELP_FMT = "{0}'s font to use on cover if needed. Recomended font: {1}."
FONT_SIZE_HELP_FMT = "{0}'s font size to use on cover if needed (Default: {1})."

DEFAULT_EXECUTABLE = "fimfic2epub.cmd" if sys.platform == "win32" else "fimfic2epub"
FIMFIC_STORY_URL_REGEX = r"https?://(?:www.)?fimfiction.net/story/(?P<ID>\d+)"


def get_api_response(story_id) -> dict:
    import requests

    url = f"https://www.fimfiction.net/api/story.php?story={story_id}"
    log.debug("Getting story matadata from: %s", url)

    data = requests.get(url).json()
    log.debug("Got the following API response: %s", data)

    return data["story"]


def logged_exit(return_code=0):
    log.debug("Finished with return code of %s.", return_code)
    exit(return_code)


COVER_SIZE = (1080, 1440)
COVER_BACKGROUND = (0, 0, 0)
COVER_FOREGROUND = (255, 255, 255)
SIDE_PADDING = 108
TITLE_POS = (SIDE_PADDING, 150)
AUTHOR_POS = (SIDE_PADDING, 1200)
LINE_SPACING = 1.2


def create_placeholder_cover(
    *,
    title,
    author,
    filename,
    title_font,
    title_font_size,
    author_font,
    author_font_size,
):
    from PIL import Image, ImageDraw, ImageFont

    log.debug("Loading fonts.")
    title_font = ImageFont.truetype(title_font, size=title_font_size)
    author_font = ImageFont.truetype(author_font, size=author_font_size)

    im = Image.new("RGB", COVER_SIZE, COVER_BACKGROUND)
    draw = ImageDraw.Draw(im, mode="RGB")

    log.debug("Drawing rectangles.")
    for pad in [12, 20]:
        draw.rectangle(
            [(pad, pad), (COVER_SIZE[0] - pad, COVER_SIZE[1] - pad)],
            fill=COVER_BACKGROUND,
            outline=COVER_FOREGROUND,
            width=2,
        )

    max_width = COVER_SIZE[0] - SIDE_PADDING * 2

    for (x, y), text, font in [
        (TITLE_POS, title, title_font),
        (AUTHOR_POS, author, author_font),
    ]:
        log.debug("Drawing text %s with the font %s.", repr(text), repr(font))
        # Centering algorithm from this gist:
        # https://gist.github.com/pojda/8bf989a0556845aaf4662cd34f21d269
        lines = []
        line = []
        words = text.split()
        for word in words:
            new_line = " ".join(line + [word])
            size = font.getsize(new_line)
            text_height = size[1] * LINE_SPACING
            if size[0] <= max_width:
                line.append(word)
            else:
                lines.append(line)
                line = [word]
        if line:
            lines.append(line)
        lines = [" ".join(line) for line in lines if line]

        height = y
        for line in lines:
            total_size = font.getsize(line)
            x_left = int(x + ((max_width - total_size[0]) / 2))
            draw.text((x_left, height), line, fill=COVER_FOREGROUND, font=font)

            height += text_height

    log.debug("Saving cover image to %s", repr(filename))
    im.save(filename)


def main():
    parser = argparse.ArgumentParser(
        description="Wrapper around fimfic2epub's CLI to handle stories "
        "without a cover.",
        add_help=False,
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="%(prog)s, version " + __version__,
        help="Print script's version and exit.",
    )
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this help message and exit.",
    )
    parser.add_argument("--debug", action="store_true", help="Show debugging output.")
    parser.add_argument(
        "--image-dir",
        default=os.getcwd(),
        metavar="DIR",
        help="Directory to store the cover image and serve it to "
        "0.0.0.0 if necessary. Defaults to current directory.",
    )
    parser.add_argument(
        "--title-font",
        required=True,
        metavar="FONT",
        help=FONT_HELP_FMT.format("Title", "Montserrat-Bold"),
    )
    parser.add_argument(
        "--title-font-size",
        type=int,
        default=100,
        metavar="SIZE",
        help=FONT_SIZE_HELP_FMT.format("Title", 100),
    )
    parser.add_argument(
        "--author-font",
        required=True,
        metavar="FONT",
        help=FONT_HELP_FMT.format("Author", "Montserrat-Regular"),
    )
    parser.add_argument(
        "--author-font-size",
        type=int,
        default=50,
        metavar="SIZE",
        help=FONT_SIZE_HELP_FMT.format("Author", 50),
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=5,
        help="Extra seconds to wait before executing fimfic2epub "
        "if the server is started to ensure that it is ready (Default: 5).",
    )
    parser.add_argument(
        "--fimfic2epub-executable",
        default=DEFAULT_EXECUTABLE,
        metavar="FILEPATH",
        help="Location of the fimfic2epub executable "
        f'(Default: "{DEFAULT_EXECUTABLE}").',
    )
    parser.add_argument(
        "--fimfic2epub-dir",
        metavar="DIR",
        help='Forwarded into fimfic2epub as "--dir DIR".',
    )
    parser.add_argument(
        "--fimfic2epub-extra-flags",
        metavar="ARGS",
        help="Flags to forward into fimfic2epub. "
        'Take care with "-C <url>", it is added automatically when the story '
        "doesn't have a cover. "
        "If you want to define the directory use --fimfic2epub-dir instead.",
    )
    parser.add_argument(
        "--fimfic2epub-filename",
        metavar="FILENAME",
        help="Filename of the epub that will be created, "
        "forwarded into fimfic2epub itself.",
    )
    parser.add_argument("story", help="Fimfiction story to download with fimfic2epub.")

    args = parser.parse_args()
    log.setLevel(logging.DEBUG if args.debug else logging.INFO)

    excutable = args.fimfic2epub_executable
    if not excutable == DEFAULT_EXECUTABLE:
        if not os.path.isfile(alt_excutable):
            log.error("%s doesn't exist.", repr(alt_excutable))
            logged_exit(1)

    story_id = (
        args.story
        if args.story.isnumeric()
        else re.match(FIMFIC_STORY_URL_REGEX, args.story).groupdict()["ID"]
    )
    cmd = [excutable, story_id]

    output_name = args.fimfic2epub_filename
    if output_name:
        log.debug("Appending %s to fimfic2epub's execution command.", repr(output_name))
        cmd.append(output_name)

    output_dir = args.fimfic2epub_dir
    if output_dir:
        log.debug(
            "Appending the flag --dir with value %s to fimfic2epub's "
            "execution command.",
            repr(output_dir),
        )
        for arg in reversed(["--dir", output_dir]):
            cmd.insert(1, arg)

    extra_flags = args.fimfic2epub_extra_flags
    if extra_flags:
        log.debug(
            "Inserting the flags %s to fimfic2epub's execution command.",
            repr(extra_flags),
        )
        import shlex

        for arg in reversed(shlex.split(extra_flags)):
            cmd.insert(1, arg)

    cover_filename = f"{story_id}.jpeg"
    cover_path = os.path.join(args.image_dir, cover_filename)
    cover_file_exists = os.path.isfile(cover_path)

    # Only making a request to the API when there isn't a generated cover.
    cover_exists = False
    if not cover_file_exists:
        api_response = get_api_response(story_id)
        cover_exists = bool(api_response.get("image", None))

    if not cover_exists:
        import time

        log.info(
            "Story of ID %s doesn't have a cover, fimfic2epub NEEDS one.", story_id
        )

        if not cover_file_exists:
            log.info("Creating cover.")
            create_placeholder_cover(
                title=api_response["title"],
                author=api_response["author"]["name"],
                filename=cover_path,
                title_font=args.title_font,
                title_font_size=args.title_font_size,
                author_font=args.author_font,
                author_font_size=args.author_font_size,
            )
        else:
            log.info("Skipping cover generation since it already exists.")

        server = f"http://0.0.0.0:8000/{cover_filename}"
        log.debug(
            "Adding -C flag pointing to %s in fimfic2epub's execution command.",
            repr(server),
        )
        for arg in reversed(["-C", server]):
            cmd.insert(1, arg)

        log.info("Serving the file in %s.", repr(server))
        server_proc = subprocess.Popen(
            [sys.executable, "-m", "http.server"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=args.image_dir,
        )

        log.debug("Waiting %s second(s).", args.wait)
        time.sleep(args.wait)

    log.info("Executing: %s", " ".join(map(lambda s: repr(s) if " " in s else s, cmd)))

    try:
        fimfic2epub_proc = subprocess.run(cmd)
        logged_exit(fimfic2epub_proc.returncode)
    finally:
        if not cover_exists:
            log.info("Closing server.")
            server_proc.terminate()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("Unhandled exception!")
        logged_exit(1)
