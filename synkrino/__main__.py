import shutil
import os
import sys
import argparse
from synkrino import baseline, compare, email

def main(args):
    crop = [args.y_start, args.y_end, args.x_start, args.x_end]

    if args.baseline:
        baseline(args.website, args.baseline_location, crop)
    elif args.compare:
        if not os.path.exists(args.baseline_location):
            baseline(args.website, args.baseline_location, crop)

        was_different, location, diff = compare(args.website, args.baseline_location, crop)
        if was_different:
            email(args.email, diff, args.from_email, args.from_email_password)
            shutil.move(location, args.baseline_location)
    else:
        sys.exit(1)

parser = argparse.ArgumentParser()
parser.add_argument("website", help="URL to take the screenshot of")
parser.add_argument("baseline_location", help="Location to store the baseline image, should be a png file")
parser.add_argument("--baseline", help="Store this screenshot as a baseline", action="store_true")
parser.add_argument("--compare", help="Compare this to the baseline", action="store_true")

parser.add_argument("--email", help="Email address to send the diff image to") 

parser.add_argument("--from-email", help="From email address")
parser.add_argument("--from-email-password", help="From email password")

parser.add_argument("--y-start", default=0, type=int)
parser.add_argument("--y-end", default=-1, type=int)
parser.add_argument("--x-start", default=0, type=int)
parser.add_argument("--x-end", default=-1, type=int)

args = parser.parse_args()

main(args)
