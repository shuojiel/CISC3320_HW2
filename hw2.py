import os
import signal


jobs = {}
next_job_id = 1


def reap_jobs():
    while True:
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)

            if pid == 0:
                break

            for job_id, job in jobs.items():
                if job["pid"] == pid:
                    if job["status"] == "Running":
                        job["status"] = "Done"
                    break

        except ChildProcessError:
            break


def main():
    global next_job_id

    while True:
        reap_jobs()

        try:
            command = input("myshell> ").strip()
        except EOFError:
            break

        if command == "":
            continue

        # exit
        if command == "exit":
            break

        # cd
        if command == "cd" or command.startswith("cd "):
            parts = command.split(maxsplit=1)

            if len(parts) == 1:
                directory = os.path.expanduser("~")
            else:
                directory = parts[1]

            try:
                os.chdir(directory)
            except FileNotFoundError:
                print(f"myshell: cd: {directory}: No such file or directory")
            except NotADirectoryError:
                print(f"myshell: cd: {directory}: Not a directory")
            except PermissionError:
                print(f"myshell: cd: {directory}: Permission denied")

            continue

        # jobs
        if command == "jobs":
            reap_jobs()

            for job_id, job in jobs.items():
                print(f"[{job_id}] {job['status']}\t{job['command']}")

            continue

        # fg
        if command.startswith("fg "):
            parts = command.split()

            if len(parts) != 2:
                print("Usage: fg <job number>")
                continue

            try:
                job_id = int(parts[1])
            except ValueError:
                print("Usage: fg <job number>")
                continue

            if job_id not in jobs:
                print(f"myshell: fg: job {job_id} not found")
                continue

            job = jobs[job_id]

            if job["status"] != "Running":
                print(f"myshell: fg: job {job_id} is not running")
                continue

            print(job["command"])

            try:
                os.waitpid(job["pid"], 0)
                job["status"] = "Done"
            except ChildProcessError:
                job["status"] = "Done"

            continue

        # kill
        if command.startswith("kill "):
            parts = command.split()

            if len(parts) != 2:
                print("Usage: kill <job number>")
                continue

            try:
                job_id = int(parts[1])
            except ValueError:
                print("Usage: kill <job number>")
                continue

            if job_id not in jobs:
                print(f"myshell: kill: job {job_id} not found")
                continue

            job = jobs[job_id]

            if job["status"] != "Running":
                print(f"myshell: kill: job {job_id} is not running")
                continue

            try:
                os.kill(job["pid"], signal.SIGTERM)
                os.waitpid(job["pid"], 0)

                job["status"] = "Terminated"

                print(f"[{job_id}] Terminated\t{job['command']}")

            except ProcessLookupError:
                job["status"] = "Done"
                print(f"myshell: kill: job {job_id} already finished")

            except ChildProcessError:
                job["status"] = "Done"

            continue

        # Check whether command should run in background
        background = False

        if command.endswith("&"):
            background = True
            command = command[:-1].strip()

        if command == "":
            continue

        args = command.split()

        # Create child process
        pid = os.fork()

        if pid == 0:
            # Child process
            try:
                os.execvp(args[0], args)

            except FileNotFoundError:
                print(
                    f"myshell: {args[0]}: command not found",
                    flush=True
                )
                os._exit(1)

            except Exception as error:
                print(
                    f"myshell: {args[0]}: {error}",
                    flush=True
                )
                os._exit(1)

        else:
            # Parent process
            if background:
                job_id = next_job_id
                next_job_id += 1

                jobs[job_id] = {
                    "pid": pid,
                    "command": command,
                    "status": "Running"
                }

                print(f"[{job_id}] {pid} {command}")

            else:
                os.waitpid(pid, 0)


if __name__ == "__main__":
    main()