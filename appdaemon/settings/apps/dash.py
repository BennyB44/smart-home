"""Define automations for Amazon Dash Buttons."""
# pylint: disable=too-few-public-methods
from core import Base


class ButtonAction:
    """Define a base class for button actions."""

    def __init__(self, hass: Base, args: dict) -> None:
        """Configure."""
        self._args = args
        self._hass = hass

    def run(self) -> None:
        """Run the action."""
        raise NotImplementedError()


class ActivateScene(ButtonAction):
    """Define an action that turns on a scene."""

    def run(self) -> None:
        """Turn on the scene."""
        self._hass.turn_on('scene.{0}'.format(self._args['scene']))


class ArmSecuritySystem(ButtonAction):
    """Define an action that sets the security system in "Home" mode."""

    def run(self) -> None:
        """Set the security system."""
        self._hass.security_manager.set_alarm(
            self._hass.security_manager.AlarmStates[self._args['state']])


class BumpClimate(ButtonAction):
    """Define an action that bumps the climate 2° in the correct direction."""

    def run(self) -> None:
        """Bump."""
        degrees = self._args['degrees']

        if (self._hass.climate_manager.mode ==
                self._hass.climate_manager.Modes.cool):
            degrees *= -1

        self._hass.climate_manager.bump_indoor_temp(degrees)


class ToggleEntity(ButtonAction):
    """Toggle an entity."""

    def run(self) -> None:
        """Toggle."""
        if self._args.get('master'):
            if self._hass.get_state(self._args['master']) == 'on':
                method_name = 'turn_off'
            else:
                method_name = 'turn_on'
        else:
            method_name = 'toggle'

        method = getattr(self._hass, method_name)
        for entity_id in self._args['entities']:
            method(entity_id)


class DashButton(Base):
    """Define an automation for Amazon Dash Buttons."""

    OBJECT_MAP = {
        'Activate "Good Night"': (ActivateScene, {
            'scene': 'good_night'
        }),
        'Arm Security System "Home"': (ArmSecuritySystem, {
            'state': 'home'
        }),
        'Bump Climate 2°': (BumpClimate, {
            'degrees': 2
        }),
        'Toggle All Salt Lamps': (
            ToggleEntity, {
                'entities': [
                    'light.salt_lamp_office', 'light.salt_lamp_master_bedroom'
                ],
                'master': 'light.salt_lamp_master_bedroom'
            }),
        'Toggle Christmas Tree': (
            ToggleEntity, {
                'entities': ['switch.christmas_tree']
            }),
    }

    def configure(self) -> None:
        """Configure."""
        self.listen_event(
            self.button_pressed,
            'AMAZON_DASH_PRESS',
            button_label=self.properties['friendly_name'])

    def button_pressed(
            self, event_name: str, data: dict, kwargs: dict) -> None:
        """Respond when button is pressed."""
        action_name = self.get_state(self.entity_ids['action_list'])

        if action_name not in self.OBJECT_MAP:
            self.error('Unknown action: {0}'.format(action_name))
            return

        self._log.info('Running Dash action: %s', action_name)

        klass, args = self.OBJECT_MAP[action_name]
        button = klass(self, args)  # type: ignore
        button.run()
