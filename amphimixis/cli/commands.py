"""CLI command implementations for Amphimixis."""

import shutil
import tempfile
from os import path
import pickle

from amphimixis import Builder, Profiler, Shell, analyze, general, parse_config
from amphimixis.general import IUI, NullUI, Project, Build, constants, tools
from amphimixis.general.general import ProjectStats
from amphimixis.perf_analyzer import main as compare_perf


def run_analyze(project: general.Project, ui: IUI = NullUI()) -> bool:
    """Execute project analysis.

    :param Project project: Project instance to analyze
    :param IUI ui: User interface for progress display
    """

    project_name = path.basename(path.normpath(project.path))
    ui.update_message(project_name, "Analyzing project...")

    if not analyze(project):
        ui.mark_failed("Analysis failed. See amphimixis.log for details.")
        return False
    ui.mark_success("Analysis completed! See amphimixis.log for details.")
    return True


def run_build(
    project: general.Project, config_file_path: str, ui: IUI = NullUI()
) -> bool:
    """Execute project build.

    :param Project project: Project instance to build
    :param str config_file: Path to YAML configuration file
    :param IUI ui: User interface for progress display
    """

    if not project.builds and not parse_config(
        project, config_file_path=str(config_file_path), ui=ui
    ):
        return False

    there_are_built = False
    for build in project.builds:
        if Builder.build_for_linux(project, build, ui):
            there_are_built = True
            ui.mark_success("Build passed!")
        else:
            ui.mark_failed(build_id=build.build_name, error_message="Building failed")

    return there_are_built


def run_profile(
    project: general.Project,
    config_file_path: str,
    ui: IUI = NullUI(),
    events: list[str] | None = None,
) -> bool:
    """Execute project profiling.

    :param project: Project instance to profiler
    :param str config_file_path: Path to YAML configuration file
    :param IUI ui: User interface for progress display
    """

    if not project.builds and not parse_config(
        project, config_file_path=str(config_file_path), ui=ui
    ):
        return False

    setup_profiling_environment(project, ui)

    success = True

    for build in project.builds:
        if not build.successfully_built:
            continue
        profiler_ = Profiler(project, build, ui)
        successful_execs = profiler_.profile_all(events=events)
        profiler_.save_stats()
        profiler_.cleanup()
        # if empty return -> error
        # if build.executables is not empty, return not equal build.executables -> error
        # if build.executables is empty, return(found executables for profiling) not empty -> passed
        if not successful_execs or (
            build.executables and successful_execs != build.executables
        ):
            ui.mark_failed("Some executables failed to be profiled")
            success = False
        else:
            ui.mark_success("Profiling completed!")

    return success


def run_compare(
    filename1: str,
    filename2: str,
    target_events: None | list[str] = None,
    max_rows=20,
    ui: IUI = NullUI(),
) -> bool:
    """Compare two perf output files and print the top `max_rows`
    symbols with the most significant changes for specified events.

    :param str filename1: Path to first perf output file
    :param str filename2: Path to second perf output file
    :param list[str] target_events: List of event names to compare (or None for all)
    :param int max_rows: Maximum number of rows to display per event
    :param IUI ui: User interface for progress display
    """

    if not path.isfile(filename1):
        ui.mark_failed(f"File not found: {filename1}")
        return False
    if not path.isfile(filename2):
        ui.mark_failed(f"File not found: {filename2}")
        return False

    if (
        compare_perf(
            filename1, filename2, target_events=target_events, max_rows=max_rows
        )
        != 0
    ):
        ui.mark_failed("Comparison failed.")
        return False
    ui.mark_success("Comparison completed!")
    return True


def show_profiling_result(project: general.Project):
    """Show hint or warning after profiling, based on .scriptout files in current directory."""

    obj: ProjectStats = tools.load_project_stats(project)

    if not obj or not any(
        obj[build][exe].executable_run_success
        for build in obj.keys()
        for exe in obj[build]
    ):
        print("\n[!] No profiling data (.scriptout files) were generated.")
        print("\tPlease check amphimixis.log for details.")
        return

    if len(obj.keys()) == 1:
        print("\n[i] Only one profiling result was generated.")
        print("\tTo compare two results, run profiling again with a different build.")
        print("\tOnce you have two .scriptout files, compare them with:")
        print("\tamixis --compare <file1.scriptout> <file2.scriptout>")
        return

    def _find_matching_exe() -> tuple[str, str, str]:
        found_build1 = None
        found_build2 = None
        found_executable = None
        build_keys = list(obj.keys())
        for build1_index in range(len(build_keys) - 1):
            for build2_key in build_keys[build1_index + 1 :]:
                build1 = obj[build_keys[build1_index]]
                build2 = obj[build2_key]

                exe_keys = set(obj[build_keys[build1_index]]) | set(obj[build2_key])

                for exe in exe_keys:
                    if (
                        build1[exe].executable_run_success
                        and build2[exe].executable_run_success
                    ):
                        found_build1 = build_keys[build1_index]
                        found_build2 = build2_key
                        found_executable = exe
                        return found_build1, found_build2, found_executable
        return "", "", ""

    build1, build2, exe = _find_matching_exe()
    if not all([build1, build2, exe]):
        print(
            "\tThere is no profiling results for the same executable in different build"
        )
        print("\b Maybe you should check profiling errors")
        return

    file1 = tools.build_filename(build1, exe) + constants.PERF_SCRIPT_EXT
    file2 = tools.build_filename(build2, exe) + constants.PERF_SCRIPT_EXT

    print("\n[>] To compare two profiling results, use:")
    print(f"\tamixis --compare {file1} {file2}")


def setup_profiling_environment(project: general.Project, ui: general.IUI) -> bool:
    """
    Set up the profiling environment by copying the built binaries to the run machines.
    """
    success = True
    tmpdir = tempfile.mkdtemp("_amphimixis")
    for build in project.builds:
        if build.build_machine != build.run_machine:
            ui.update_message(build.build_name, "Copying built files to run machine")
            shell_build_machine = Shell(project, build.build_machine, ui=ui)
            shell_run_machine = Shell(project, build.run_machine, ui=ui)

            # copy builds
            build_path = path.join(
                shell_build_machine.get_project_workdir(), build.build_name
            )
            if not shell_build_machine.copy_to_host(build_path, tmpdir):
                ui.mark_failed("Can't download built files from build machine")
                success = False

            if not shell_run_machine.copy_to_remote(
                path.join(tmpdir, build.build_name),
                shell_run_machine.get_project_workdir(),
            ):
                ui.mark_failed("Can't transfer built files to run machine")
                success = False

            # copy source
            if not shell_run_machine.copy_to_remote(
                project.path, path.dirname(shell_run_machine.get_source_dir())
            ):
                ui.mark_failed("Can't transfer source code to run machine")
                success = False

    shutil.rmtree(tmpdir)
    return success


def open_alternate_term() -> None:
    """Uses Xterm control code to switch to an alternate terminal buffer"""
    print("\033[?1049h", end="")


def close_alternate_term() -> None:
    """Uses Xterm control code to return back to first terminal buffer"""
    print("\033[?1049l", end="")


def clean(*builds: Build) -> bool:
    """Clean builds directories"""
    project: Project
    try:
        project = tools.get_cache_project()
    except FileNotFoundError:
        print("Project file .project not found")
        return False
    success = True
    for b in builds:
        if not Builder.clean(project, b):
            success = False
    return success


def interactive_clean() -> bool:
    """Enumerate builds names and suggest choose which will be cleaned"""
    builds: dict[str, Build] = {}
    project: Project
    try:
        project = tools.get_cache_project()
        with open(Builder.BUILDS_LIST_FILE_NAME, "rb") as file:
            builds = pickle.load(file)
    except FileNotFoundError:
        pass

    success = True
    try:
        for i, build_name in enumerate(builds.keys()):
            print(f"{i + 1}.\t{build_name}")
        nums = [
            int(n) - 1 for n in input("Enter the builds numbers to clean: ").split()
        ]

        for i, build in enumerate(builds.values()):
            if i in nums:
                if Builder.clean(project, build):
                    print(f"{build.build_name} was successfully cleaned")
                else:
                    success = False
                    print(f"{build.build_name} failed to clean")
    except ValueError:
        print("Not a number")
    except KeyboardInterrupt:
        print("Cancelled")
    return success
