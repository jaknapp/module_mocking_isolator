import ast
import glob
import importlib
import os
from contextlib import ExitStack
from enum import Enum
from typing import Any, Tuple
from unittest.mock import patch

from mock_isolator.mock_recording_encoder import (
    get_json_file_mock_interaction_recording_store,
)
from mock_isolator.recording_mock import BasicRecordingMocker, RecordingMock
from mock_isolator.types import MockIsolatorMode


def _get_patch_path(
    full_import_path: str,
    alias: str | None,
    imports_to_mock: list[str],
    filepath: str,
    is_import_from: bool,
) -> str:
    base_module_path = ".".join(filepath.replace("/", ".").split(".")[:-1])
    for mock_path in imports_to_mock:
        if full_import_path.startswith(mock_path):
            if alias:
                return f"{base_module_path}.{alias}"
            elif is_import_from:
                return f"{base_module_path}.{full_import_path.split('.')[-1]}"
            else:
                return f"{base_module_path}.{full_import_path}"
    return full_import_path


def _should_patch_import(full_import_path: str, imports_to_mock: list[str]) -> bool:
    for mock_path in imports_to_mock:
        if full_import_path.startswith(mock_path):
            return True
    return False


def _get_imports_to_patch_for_module_filepath(
    filepath: str,
    imports_to_mock: list[str],
) -> list[Tuple[str, str, str | None]]:
    """Return list of patch path, module path, and alias"""
    with open(filepath, "r") as file:
        node = ast.parse(file.read(), filename=filepath)
    imported_items: list[Tuple[str, str, str | None]] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Import):
            for alias in child.names:
                full_import_path = alias.name
                if _should_patch_import(full_import_path, imports_to_mock):
                    patch_path = _get_patch_path(
                        full_import_path,
                        alias.asname,
                        imports_to_mock,
                        filepath,
                        is_import_from=False,
                    )
                    imported_items.append((patch_path, alias.name, None))
        elif isinstance(child, ast.ImportFrom):
            module = child.module if child.module else ""
            for alias in child.names:
                full_import_path = f"{module}.{alias.name}"
                if _should_patch_import(full_import_path, imports_to_mock):
                    patch_path = _get_patch_path(
                        full_import_path,
                        alias.asname,
                        imports_to_mock,
                        filepath,
                        is_import_from=True,
                    )
                    imported_items.append((patch_path, module, alias.name))
    return imported_items


def _load_item(module_path: str, alias: str | None) -> Any:
    module_imported = importlib.import_module(module_path)
    if alias is None:
        return module_imported
    return getattr(module_imported, alias)


def isolate_module_with_mocks(
    exit_stack: ExitStack,
    module_filepath: str,
    modules_to_mock: list[str],
    mode: MockIsolatorMode,
    recording_filepath_prefix: str,
) -> None:
    """
    Stores/loads mock interaction recordings from the recording_filepath_prefix where
    each mocked module gets a separate file.
    """
    patch_paths = _get_imports_to_patch_for_module_filepath(
        filepath=module_filepath,
        imports_to_mock=modules_to_mock,
    )
    recording_filepaths = {
        patch_path: f"{recording_filepath_prefix}{patch_path}.json"
        for patch_path, module_path, _ in patch_paths
    }
    recording_store = get_json_file_mock_interaction_recording_store()
    if mode == MockIsolatorMode.REPLAY:
        [
            exit_stack.enter_context(
                cm=patch(
                    module_path,
                    new=recording_store.load_recorded_mock_interactions_from_file(
                        filepath=recording_filepath
                    ),
                )
            )
            for module_path, recording_filepath in recording_filepaths.items()
        ]
    elif mode == MockIsolatorMode.RECORD:
        patch_path_modules = {
            patch_path: _load_item(module_path, alias)
            for patch_path, module_path, alias in patch_paths
        }
        mocker = BasicRecordingMocker()
        module_path_mocks = [
            (
                module_path,
                exit_stack.enter_context(
                    cm=patch(
                        module_path,
                        new=RecordingMock(wrapped_item=real_object, mocker=mocker),
                    )
                ),
            )
            for module_path, real_object in patch_path_modules.items()
        ]

        def write_recorded_mocks_to_file():
            for file in glob.glob(pathname=f"{recording_filepath_prefix}*"):
                os.remove(path=file)
            for module_path, mock in module_path_mocks:
                recording_store.store_recorded_mock_interactions_to_file(
                    mock=mock,
                    filepath=f"{recording_filepath_prefix}{module_path}.json",
                )

        exit_stack.callback(write_recorded_mocks_to_file)


def isolate_dependencies_with_mocks(
    exit_stack: ExitStack,
    dependencies: list[Any],
    dependency_names: list[str],
    mode: MockIsolatorMode,
    recording_filepath_prefix: str,
) -> None:
    """
    Records/replays mock interactions from the recording_filepath_prefix where
    each mocked module gets a separate file.
    """
    recording_store = get_json_file_mock_interaction_recording_store()
    dependency_name_to_filepath = {
        dependency_name: f"{recording_filepath_prefix}{dependency_name}.json"
        for dependency_name in dependency_names
    }
    if mode == MockIsolatorMode.REPLAY:
        return {
            mock_name: recording_store.load_recorded_mock_interactions_from_file(
                filepath=dependency_name_to_filepath[mock_name]
            )
            for mock_name in dependency_names
        }
    elif mode == MockIsolatorMode.RECORD:
        mocker = BasicRecordingMocker()
        dependency_name_to_recording_mock = {
            dependency_name: RecordingMock(wrapped_item=dependency, mocker=mocker)
            for dependency_name, dependency in zip(dependency_names, dependencies)
        }

        def write_recorded_mocks_to_file():
            for file in glob.glob(pathname=f"{recording_filepath_prefix}*"):
                os.remove(path=file)
            for dependency_name, recording_mock in dependency_name_to_recording_mock.items():
                recording_store.store_recorded_mock_interactions_to_file(
                    mock=recording_mock,
                    filepath=dependency_name_to_filepath[dependency_name],
                )

        exit_stack.callback(write_recorded_mocks_to_file)
        return dependency_name_to_recording_mock
    
    