"""Toolkit-agnostic package setup and extension-install screen model."""

from __future__ import annotations

from concurrent.futures import Future
from dataclasses import replace
from threading import Lock

from nwbforge.app.packages import InstallMode, InstallPreset, PackageInstallRequest, PackageInstallResult
from nwbforge.app.services import PackageManagementController
from nwbforge.ui.errors import DefaultUiErrorPresenter, UiErrorPresenter
from nwbforge.ui.models import PackageInstallerState, PackageInstallerStateListener


class PackageInstallerScreenModel:
    """Drive route selection, preview, and background install state for the UI."""

    def __init__(
        self,
        controller: PackageManagementController,
        *,
        error_presenter: UiErrorPresenter | None = None,
    ) -> None:
        self._controller = controller
        self._state = PackageInstallerState()
        self._listeners: list[PackageInstallerStateListener] = []
        self._lock = Lock()
        self._error_presenter = error_presenter or DefaultUiErrorPresenter()
        self._preset_routes = {
            preset: tuple(spec.route_name for spec in specs)
            for preset, specs in controller.list_preset_routes().items()
        }

    @property
    def state(self) -> PackageInstallerState:
        return self._state

    def subscribe(self, listener: PackageInstallerStateListener, *, emit_initial: bool = True) -> None:
        with self._lock:
            self._listeners.append(listener)
            state = self._state
        if emit_initial:
            listener(state)

    def load(self) -> PackageInstallerState:
        available_routes = self._controller.list_available_routes()
        saved_selection = self._controller.load_saved_selection()

        if saved_selection is not None:
            next_state = replace(
                self._state,
                available_routes=available_routes,
                install_mode=saved_selection.mode,
                install_preset=saved_selection.preset,
                selected_routes=saved_selection.routes,
                saved_selection=saved_selection,
                error_message=None,
                user_error=None,
            )
        else:
            default_routes = self._preset_routes[InstallPreset.COMMON]
            next_state = replace(
                self._state,
                available_routes=available_routes,
                install_mode=InstallMode.SELECTED,
                install_preset=InstallPreset.COMMON,
                selected_routes=default_routes,
                saved_selection=None,
                error_message=None,
                user_error=None,
            )

        self._set_state(next_state)
        return self.preview_install()

    def set_install_mode(self, install_mode: InstallMode | str) -> PackageInstallerState:
        install_mode = InstallMode(install_mode)
        if install_mode is InstallMode.MINIMAL:
            next_state = replace(
                self._state,
                install_mode=install_mode,
                install_preset=InstallPreset.MINIMAL,
                selected_routes=(),
                error_message=None,
                user_error=None,
            )
        elif install_mode is InstallMode.FULL:
            next_state = replace(
                self._state,
                install_mode=install_mode,
                install_preset=InstallPreset.FULL,
                selected_routes=self._preset_routes[InstallPreset.FULL],
                error_message=None,
                user_error=None,
            )
        else:
            preset = self._state.install_preset
            if preset in {InstallPreset.MINIMAL, InstallPreset.FULL}:
                preset = InstallPreset.COMMON
            selected_routes = (
                self._preset_routes[preset]
                if preset is not InstallPreset.CUSTOM
                else self._state.selected_routes
            )
            next_state = replace(
                self._state,
                install_mode=install_mode,
                install_preset=preset,
                selected_routes=selected_routes,
                error_message=None,
                user_error=None,
            )

        self._set_state(next_state)
        return self.preview_install()

    def select_preset(self, preset: InstallPreset | str) -> PackageInstallerState:
        preset = InstallPreset(preset)
        install_mode = InstallMode.SELECTED
        selected_routes = self._state.selected_routes
        if preset is not InstallPreset.CUSTOM:
            selected_routes = self._preset_routes[preset]

        self._set_state(
            replace(
                self._state,
                install_mode=install_mode,
                install_preset=preset,
                selected_routes=selected_routes,
                error_message=None,
                user_error=None,
            )
        )
        return self.preview_install()

    def set_custom_routes(self, routes: tuple[str, ...]) -> PackageInstallerState:
        available_route_names = {spec.route_name for spec in self._state.available_routes}
        selected_routes = tuple(dict.fromkeys(route for route in routes if route in available_route_names))
        self._set_state(
            replace(
                self._state,
                install_mode=InstallMode.SELECTED,
                install_preset=InstallPreset.CUSTOM,
                selected_routes=selected_routes,
                error_message=None,
                user_error=None,
            )
        )
        return self.preview_install()

    def preview_install(self) -> PackageInstallerState:
        request = self._build_request(persist_selection=False)
        preview = self._controller.preview_install(request)
        return self._set_state(
            replace(
                self._state,
                preview=preview,
                issues=preview.issues,
                resolved_extras=preview.plan.extras,
                is_installable=preview.is_installable,
                user_error=None,
            )
        )

    def start_install(self, *, persist_selection: bool = True) -> Future[PackageInstallResult]:
        self._set_state(
            replace(
                self._state,
                is_install_running=True,
                error_message=None,
                progress_event=None,
                user_error=None,
            )
        )
        future = self._controller.start_install(
            self._build_request(persist_selection=persist_selection),
            progress_callback=self._handle_progress,
        )
        future.add_done_callback(self._handle_install_complete)
        return future

    def shutdown(self, wait: bool = True) -> None:
        self._controller.shutdown(wait=wait)

    def _build_request(self, *, persist_selection: bool) -> PackageInstallRequest:
        preset = self._state.install_preset
        if self._state.install_mode is InstallMode.MINIMAL:
            preset = InstallPreset.MINIMAL
        elif self._state.install_mode is InstallMode.FULL:
            preset = InstallPreset.FULL

        routes = ()
        if self._state.install_mode is InstallMode.SELECTED and preset is InstallPreset.CUSTOM:
            routes = self._state.selected_routes

        return PackageInstallRequest(
            mode=self._state.install_mode,
            preset=preset,
            routes=routes,
            persist_selection=persist_selection,
        )

    def _handle_progress(self, event) -> None:
        self._set_state(
            replace(
                self._state,
                is_install_running=event.stage.value not in {"completed", "failed"},
                progress_event=event,
                error_message=None,
                user_error=None,
            )
        )

    def _handle_install_complete(self, future: Future[PackageInstallResult]) -> None:
        try:
            result = future.result()
        except Exception as exc:
            user_error = self._error_presenter.present(exc)
            self._set_state(
                replace(
                    self._state,
                    is_install_running=False,
                    error_message=user_error.message,
                    user_error=user_error,
                )
            )
            return

        self._set_state(
            replace(
                self._state,
                is_install_running=False,
                error_message=None,
                user_error=None,
                last_completed_routes=result.preview.plan.selection.routes,
                preview=result.preview,
                issues=result.preview.issues,
                resolved_extras=result.preview.plan.extras,
                is_installable=result.preview.is_installable,
            )
        )

    def _set_state(self, new_state: PackageInstallerState) -> PackageInstallerState:
        with self._lock:
            self._state = new_state
            listeners = tuple(self._listeners)
            state = self._state
        for listener in listeners:
            listener(state)
        return state
