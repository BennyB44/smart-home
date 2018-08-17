"""Define a mode."""

# pylint: disable=attribute-defined-outside-init,import-error

from typing import Union

import appdaemon.plugins.hass.hassapi as hass  # type: ignore


class Mode(hass.Hass):
    """Define a mode."""

    @property
    def state(self) -> str:
        """Return the current state of the mode switch."""
        return self.get_state(self.switch)

    @state.setter
    def state(self, value: str) -> None:
        """Alter the state of the mode switch."""
        if value not in ['on', 'off']:
            self.error('Mode value undefined: {0}'.format(value))
            return

        if value == 'on':
            func = self.turn_on
        else:
            func = self.turn_off

        func(self.switch)

    def initialize(self) -> None:
        """Initialize."""
        self._enabled_toggles_to_disable = []  # type: ignore
        self._enabled_toggles_to_enable = []  # type: ignore
        self.switch = 'input_boolean.mode_{0}'.format(self.name)

        self.listen_state(self.switch_toggled_cb, entity=self.switch)

    def register_enabled_toggle(
            self, enabled_toggle_name: str, value: str) -> None:
        """Record how a enable toggle should respond when in this mode."""
        location = getattr(self, '_enabled_toggles_to_{0}'.format(value))
        if enabled_toggle_name in location:
            self.log(
                'Switch behavior already exists: {0}'.format(
                    enabled_toggle_name),
                level='WARNING')
            return

        location.append(enabled_toggle_name)

    def switch_toggled_cb(  # pylint: disable=too-many-arguments
            self, entity: Union[str, dict], attribute: str, old: str, new: str,
            kwargs: dict) -> None:
        """Make alterations when a mode enabled_toggle is toggled."""
        self.fire_event('MODE_CHANGE', mode=self.name, state=new)

        if new == 'on':
            func1 = self.turn_off
            func2 = self.turn_on
        else:
            func1 = self.turn_on
            func2 = self.turn_off

        for enabled_toggle in self._enabled_toggles_to_disable:
            func1(enabled_toggle)
        for enabled_toggle in self._enabled_toggles_to_enable:
            func2(enabled_toggle)
