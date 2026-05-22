#!/usr/bin/env python3
import argparse
import subprocess
import os
import shutil
import datetime

LOG_FILE = ".merge_resolver.log"


def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def log_action(message):
    timestamp = datetime.datetime.now().isoformat()
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")


def get_unmerged_files():
    out, _, _ = run_cmd("git ls-files -u")
    if out:
        # Format of git ls-files -u:
        # 100644 blob-sha 1       file
        # We extract unique filenames
        files = set()
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                files.add(parts[1])
        return list(files)
    return []


def backup_state():
    print("Backing up state...")
    if os.path.exists(".git/MERGE_MSG"):
        shutil.copy2(".git/MERGE_MSG", ".git/MERGE_MSG.bak")
    # backup index
    shutil.copy2(".git/index", ".git/index.bak")
    log_action("Backup created for .git/MERGE_MSG and .git/index")


def rollback_state():
    print("Rolling back state...")
    if os.path.exists(".git/MERGE_MSG.bak"):
        shutil.copy2(".git/MERGE_MSG.bak", ".git/MERGE_MSG")
    if os.path.exists(".git/index.bak"):
        shutil.copy2(".git/index.bak", ".git/index")
    log_action("Rollback performed from backup")


def resolve_conflicts(strategy, dry_run):
    unmerged = get_unmerged_files()
    if not unmerged:
        print("No unmerged files found.")
        return

    for file in unmerged:
        action_msg = f"Resolving {file} using strategy '{strategy}'"
        print(action_msg)
        if dry_run:
            log_action(f"[DRY-RUN] {action_msg}")
            continue

        out, _, _ = run_cmd(f"git ls-files -u -- '{file}'")
        stages = []
        for line in out.splitlines():
            # Format: mode sha stage\tfile
            parts = line.split("\t")[0].split()
            if len(parts) >= 3:
                stages.append(parts[2])

        has_ours = "2" in stages
        has_theirs = "3" in stages

        if strategy == "ours":
            if has_ours:
                run_cmd(f"git checkout --ours -- '{file}'")
                run_cmd(f"git add '{file}'")
                log_action(f"Resolved {file}: checkout --ours")
            else:
                run_cmd(f"git rm '{file}'")
                log_action(f"Resolved {file}: git rm (deleted in ours)")
        else:
            if has_theirs:
                run_cmd(f"git checkout --theirs -- '{file}'")
                run_cmd(f"git add '{file}'")
                log_action(f"Resolved {file}: checkout --theirs")
            else:
                run_cmd(f"git rm '{file}'")
                log_action(f"Resolved {file}: git rm (deleted in theirs)")


def main():
    parser = argparse.ArgumentParser(description="Git Merge Resolver")
    parser.add_argument(
        "--strategy",
        choices=["ours", "theirs"],
        default="ours",
        help="Resolution strategy",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Backup .git/MERGE_MSG and index before resolution",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without doing it",
    )
    parser.add_argument(
        "--rollback", action="store_true", help="Restore from last backup"
    )

    args = parser.parse_args()

    if args.rollback:
        rollback_state()
        return

    if args.backup and not args.dry_run:
        backup_state()

    resolve_conflicts(args.strategy, args.dry_run)


if __name__ == "__main__":
    main()
