import asyncio
import subprocess
import os
import tarfile
import zipfile


def get_version():
    """
    Extracts the version from the specified __about__.py file.
    """
    about = {}
    with open("./src/python_redlines/__about__.py") as f:
        exec(f.read(), about)
    return about["__version__"]


async def run_command(command):
    """
    Runs a shell command and prints its output.
    """
    process = await asyncio.create_subprocess_exec(
        *command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    async for line in process.stdout:
        print(line.decode().strip())

    await process.wait()


def _compress_tar(source_dir, target_file):
    with tarfile.open(target_file, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))


def _compress_zip(source_dir, target_file):
    with zipfile.ZipFile(target_file, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                zipf.write(
                    os.path.join(root, file),
                    os.path.relpath(
                        os.path.join(root, file), os.path.join(source_dir, "..")
                    ),
                )


async def compress_files(source_dir, target_file):
    """
    Compresses files in the specified directory into a tar.gz or zip file.
    """
    loop = asyncio.get_event_loop()
    if target_file.endswith(".tar.gz"):
        await loop.run_in_executor(None, _compress_tar, source_dir, target_file)
    elif target_file.endswith(".zip"):
        await loop.run_in_executor(None, _compress_zip, source_dir, target_file)


def cleanup_old_builds(dist_dir, current_version):
    """
    Deletes any build files ending in .zip or .tar.gz in the dist_dir with a different version tag.
    """
    for file in os.listdir(dist_dir):
        if not file.endswith(
            (f"{current_version}.zip", f"{current_version}.tar.gz", ".gitignore")
        ):
            file_path = os.path.join(dist_dir, file)
            os.remove(file_path)
            print(f"Deleted old build file: {file}")


async def main():
    version = get_version()
    print(f"Version: {version}")

    dist_dir = "./src/python_redlines/dist/"

    await run_command(["dotnet", "restore", "./csproj"])

    run_commands = [
        ["dotnet", "publish", "./csproj", "-c", "Release", "-r", "linux-x64", "--self-contained", "--no-restore"],
        ["dotnet", "publish", "./csproj", "-c", "Release", "-r", "linux-arm64", "--self-contained", "--no-restore"],
        ["dotnet", "publish", "./csproj", "-c", "Release", "-r", "win-x64", "--self-contained", "--no-restore"],
        ["dotnet", "publish", "./csproj", "-c", "Release", "-r", "win-arm64", "--self-contained", "--no-restore"],
        ["dotnet", "publish", "./csproj", "-c", "Release", "-r", "osx-x64", "--self-contained", "--no-restore"],
        ["dotnet", "publish", "./csproj", "-c", "Release", "-r", "osx-arm64", "--self-contained", "--no-restore"],
    ]

    await asyncio.gather(*[run_command(command) for command in run_commands])

    compression_inputs = [
        (
            "./csproj/bin/Release/net8.0/linux-x64",
            f"{dist_dir}/linux-x64-{version}.tar.gz",
        ),
        (
            "./csproj/bin/Release/net8.0/linux-arm64",
            f"{dist_dir}/linux-arm64-{version}.tar.gz",
        ),
        (
            "./csproj/bin/Release/net8.0/win-x64",
            f"{dist_dir}/win-x64-{version}.zip",
        ),
        (
            "./csproj/bin/Release/net8.0/win-arm64",
            f"{dist_dir}/win-arm64-{version}.zip",
        ),
        (
            "./csproj/bin/Release/net8.0/osx-x64",
            f"{dist_dir}/osx-x64-{version}.tar.gz",
        ),
        (
            "./csproj/bin/Release/net8.0/osx-arm64",
            f"{dist_dir}/osx-arm64-{version}.tar.gz",
        ),
    ]

    await asyncio.gather(
        *[
            compress_files(source_dir, target_file)
            for source_dir, target_file in compression_inputs
        ]
    )

    cleanup_old_builds(dist_dir, version)

    print("Build and compression complete.")


if __name__ == "__main__":
    asyncio.run(main())
